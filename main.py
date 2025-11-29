# system
from machine import I2C, Pin
from utime import ticks_diff, ticks_us 
#wifi connection and data
import json
import network
import time
import socket
# external
from max30205 import MAX30205
from max30102 import MAX30102, MAX30105_PULSE_AMP_MEDIUM
from filter import BandpassFilter
#project_modules
from hrcalculator import compute_hr
from spo2calculator import compute_spo2


SSID = "SUPERONLINE_Wi-Fi_3252"
PASSWORD = "3HcTsZPUXYx5"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    
    print("Wi-Fi Connected.")

    return wlan

wlan = connect_wifi()
print("Pico connected, ifconfig =", wlan.ifconfig())


#TCP server and client connection
def start_server():
    print("Starting TCP server on port 8266...")
    addr = socket.getaddrinfo("0.0.0.0", 8266)[0][-1]
    s = socket.socket()
    s.bind(addr) # addr: server
                 # remote_addr: client 
    s.listen(1)
    
    print("Waiting for client...")
    client, remote_addr = s.accept()
    print("Client connected from:", remote_addr)

    return client

client_socket = start_server()
print("TCP client socket ready, now initializing sensors...")


bp_filter_ir = BandpassFilter(fs=100, fc_hp=0.5, fc_lp=8.0)
bp_filter_red = BandpassFilter(fs=100, fc_hp=0.5, fc_lp=8.0) 

compute_frequency = True # we may use it for control it by an input from user
f_HZ = 0 # frequency of data acquisition

t_start = ticks_us() # starting time for acquisition 
samples_n = 0 # number of samples received

BUFFER_SIZE = 50 
red_buffer = []
ir_buffer = []


my_SDA_pin = 26
my_SCL_pin = 27
my_i2c_freq = 100000

i2c = I2C(1, sda=Pin(my_SDA_pin), scl=Pin(my_SCL_pin), freq=my_i2c_freq)
print(i2c.scan())

sensor = MAX30102(i2c=i2c)
# setup the sensor
sensor.setup_sensor()
# Set the number of samples to be averaged by the chip 
sensor.set_fifo_average(8) # set FIFO average to 8 samples
# Set the ADC range
sensor.set_adc_range(16384) # set ADC range to 16384nA
#Set the sample rate
sensor.set_sample_rate(100) # set sample rate to 100 samples per second
# Set the LED pulse width
sensor.set_pulse_width(215) # set LED pulse width to 215us
# Set the led mode
sensor.set_led_mode(2) # set to SpO2 mode (Red + IR)
# set the led brightness
sensor.set_pulse_amplitude_red(MAX30105_PULSE_AMP_MEDIUM) # set Red LED brightness to medium
sensor.set_pulse_amplitude_it(MAX30105_PULSE_AMP_MEDIUM) # set IR LED brightness to medium
# set the led brightness of all the active leds
sensor.set_active_leds_amplitude(MAX30105_PULSE_AMP_MEDIUM) # set all active LED brightness to medium

temp_sensor = MAX30205(i2c=i2c)

while True:
    sensor.check() # check for new data
    
    if sensor.available():
        red_sample = sensor.pop_red_from_storage()
        red_sample_filtered = bp_filter_red.step(red_sample)
        red_buffer.append(red_sample_filtered)


        ir_sample = sensor.pop_ir_from_storage()
        ir_sample_filtered = bp_filter_ir.step(ir_sample)
        ir_buffer.append(ir_sample_filtered)
        
        # Compute the real frequency at which we receive data (with microsecond precision)
        if compute_frequency:
            if ticks_diff(ticks_us(), t_start) >= 999999:
                f_HZ = samples_n
                samples_n = 0
                print("acquisition frequency = ", f_HZ)
                t_start = ticks_us()
            else:
                samples_n = samples_n + 1

        if len(red_buffer) >= BUFFER_SIZE and len(ir_buffer) >= BUFFER_SIZE:

            hr_result = compute_hr(ir_buffer, f_HZ)

            if hr_result is None:
                print("HR could not be computed, skipping this window.")
                red_buffer = []
                ir_buffer = []
                continue

            hr_rate, peaks_index = hr_result

            spo2 = compute_spo2(ir_buffer, red_buffer, min_samples=40)

            temperature_c = temp_sensor.read_temperature_c()

            data_packet = {
                "red": red_buffer,
                "ir": ir_buffer,
                "acq_freq": f_HZ,
                "hr": {
                    "value": hr_rate,
                    "peaks_index": peaks_index
                }, 
                "spo2": spo2,
                "body_temp": temperature_c 
            }

            payload = json.dumps(data_packet) + "\n" # sending json file

            try:
                client_socket.send(payload.encode("utf-8"))
            except OSError:
                client_socket = start_server()
                continue 

            red_buffer = []
            ir_buffer = []
        
    time.sleep_ms(1)