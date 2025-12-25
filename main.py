# system
from machine import I2C, Pin
from utime import ticks_diff, ticks_us 
import gc # For garbage collection
import json
import network
import time
import socket

# external
from lib.max30205 import MAX30205
from lib.max30102 import MAX30102, MAX30105_PULSE_AMP_MEDIUM
from lib.filter import BandpassFilter

# project_modules
from lib.hrcalculator import compute_hr
from lib.spo2calculator import compute_spo2

################################################################
# CONFIGURATION
################################################################
DEBUG = False 
SSID = "" # Fill
PASSWORD = ""# Fill

################################################################
# SETUP FUNCTIONS
################################################################

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    
    print("Wi-Fi Connected:", wlan.ifconfig())
    return wlan

def start_server():
    print("Starting TCP server on port 8266...")
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    
    # TCP_NODELAY
    try:
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except:
        try:
            s.setsockopt(6, 1, 1) 
        except:
            pass

    s.bind(('0.0.0.0', 8266)) 
    s.listen(1)
    
    print("Waiting for client...")
    client, remote_addr = s.accept()
    print("Client connected from:", remote_addr)
    
    # --- FIX: Timeout setting must be HERE ---
    # We reset the timeout for every new connection.
    client.settimeout(0.1) 
    
    return client

################################################################
# INITIALIZATION
################################################################

# 1. Connect Network
wlan = connect_wifi()
client_socket = start_server()
# (Moved settimeout into start_server, not needed here anymore but harmless to keep)
print("System ready, initializing sensors...")

# 2. I2C & Sensors (TURBO MODE)
my_SDA_pin = 26
my_SCL_pin = 27
my_i2c_freq = 1000000 # 1 MHz

i2c = I2C(1, sda=Pin(my_SDA_pin), scl=Pin(my_SCL_pin), freq=my_i2c_freq)

# MAX30102 Setup
sensor = MAX30102(i2c=i2c)
sensor.setup_sensor()
sensor.set_fifo_average(2) 
sensor.set_adc_range(16384) 
sensor.set_sample_rate(100) 
sensor.set_pulse_width(215) 
sensor.set_led_mode(2) 
sensor.set_pulse_amplitude_red(MAX30105_PULSE_AMP_MEDIUM) 
sensor.set_pulse_amplitude_it(MAX30105_PULSE_AMP_MEDIUM) 
sensor.set_active_leds_amplitude(MAX30105_PULSE_AMP_MEDIUM)

# MAX30205 Setup
try:
    temp_sensor = MAX30205(i2c=i2c, calibration_offset = 4.45)
except Exception as e:
    temp_sensor = None

################################################################
# GLOBAL VARIABLES & BUFFERS
################################################################

BUFFER_SIZE = 100 
red_buffer = []
ir_buffer = []
raw_red_buffer = []
raw_ir_buffer = []

# Timing & Frequency
compute_frequency = True
f_HZ = 0 
t_start = ticks_us() 
samples_n = 0 

# Filters
bp_filter_ir = None 
bp_filter_red = None
filters_ready = False 

# State Variables
last_temp = 0.0
last_hr = None
hr_count = 0 
last_spo2 = None
window_id = 0 
sample_id = 0 

# Data Batching Variable
batch_buffer = ""

################################################################
# MAIN LOOP
################################################################

while True:
    sensor.check() 
    
    while sensor.available():
        red_sample = sensor.pop_red_from_storage()
        ir_sample = sensor.pop_ir_from_storage()

        # Filtering
        if filters_ready and bp_filter_red and bp_filter_ir:
            red_sample_filtered = bp_filter_red.step(red_sample * -1)
            ir_sample_filtered  = bp_filter_ir.step(ir_sample * -1)
        else:
            red_sample_filtered = red_sample 
            ir_sample_filtered  = ir_sample
        
        # Buffer Filling
        raw_red_buffer.append(red_sample)
        red_buffer.append(red_sample_filtered)
        raw_ir_buffer.append(ir_sample)
        ir_buffer.append(ir_sample_filtered)

        sample_id += 1
        
        # --- FREQUENCY CALCULATION ---
        if compute_frequency:
            if ticks_diff(ticks_us(), t_start) >= 1000000: 
                temp_f_HZ = samples_n
                samples_n = 0
                t_start = ticks_us()

                if DEBUG: print("Freq:", temp_f_HZ)

                if 35 <= temp_f_HZ <= 70:
                    f_HZ = temp_f_HZ
                
                # Initialize filters
                if not filters_ready and f_HZ > 0:
                    bp_filter_ir = BandpassFilter(fs=f_HZ, fc_hp=0.5, fc_lp=8.0)
                    bp_filter_red = BandpassFilter(fs=f_HZ, fc_hp=0.5, fc_lp=8.0)
                    filters_ready = True
                    if DEBUG: print("Filters INITIALIZED. Fs:", f_HZ)
            else:
                samples_n += 1

        # --- DATA BATCHING ---
        current_line = "S, {},{:.1f},{:.1f}\n".format(
            sample_id,
            red_sample_filtered,
            ir_sample_filtered,
        )
        
        batch_buffer += current_line

        # Send every 15 samples (Traffic Control)
        if sample_id % 15 == 0: 
            try:
                client_socket.send(batch_buffer.encode("utf-8"))
                batch_buffer = "" 
            except OSError as e:
                # Timeout error (110)
                if len(e.args) > 0 and e.args[0] == 110: 
                    pass 
                else:
                    if DEBUG: print("Lost connection stream...")
                    client_socket.close()
                    client_socket = start_server() # Timeout is now set automatically here
                    batch_buffer = ""

        # --- CALCULATION (WINDOW FULL) ---
        if len(red_buffer) >= BUFFER_SIZE and len(ir_buffer) >= BUFFER_SIZE:
            window_id += 1

            # 1. Heart Rate (HR)
            hr_result = compute_hr(ir_buffer, f_HZ)

            if hr_result is None:
                hr_count += 1
                if hr_count >= 3:
                    hr_rate = None
                else:
                    hr_rate = last_hr
                peaks_index = []
            else:
                hr_rate, peaks_index = hr_result
                
                if last_hr is not None and hr_rate == last_hr:
                    hr_count += 1
                    if hr_count >= 3: 
                        hr_rate = None
                        peaks_index = []
                    else:
                        last_hr = hr_rate
                else:
                    last_hr = hr_rate
                    hr_count = 0

            # 2. SpO2
            spo2 = compute_spo2(ir_buffer, red_buffer, raw_ir_buffer, raw_red_buffer, min_samples=40)
            if spo2 is None:
                spo2 = last_spo2
            else:
                last_spo2 = spo2

            # 3. Temperature
            if temp_sensor:
                try:
                    temperature_c = temp_sensor.read_temperature_c()
                    last_temp = temperature_c
                except OSError:
                    temperature_c = last_temp
            else:
                temperature_c = 0.0

            # 4. Send JSON
            result_packet = {
                "type": "result",
                "window_id": window_id,
                "window_end_sample_id": sample_id,
                "window_start_sample_id": sample_id - BUFFER_SIZE + 1,
                "acq_freq": f_HZ,
                "hr": {"value": hr_rate, "peaks_index": peaks_index}, 
                "spo2": spo2,
                "body_temp": temperature_c 
            }

            try:
                payload_result = json.dumps(result_packet) + "\n"
                client_socket.send(payload_result.encode("utf-8"))
                
                # GC: Cleanup every 10 windows
                if window_id % 10 == 0:
                    gc.collect() 
                
            except OSError:
                if DEBUG: print("Lost connection JSON...")
                client_socket.close()
                client_socket = start_server()
                
            # Clear Buffers
            red_buffer = []
            ir_buffer = []
            raw_ir_buffer = []
            raw_red_buffer = []