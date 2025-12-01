# system

from machine import I2C, Pin
from utime import ticks_diff, ticks_us 
#wifi connection and data
import json
import network
import time
import socket
# external
from lib.max30205 import MAX30205
from lib.max30102 import MAX30102, MAX30105_PULSE_AMP_MEDIUM
from lib.filter import BandpassFilter
#project_modules
from lib.hrcalculator import compute_hr
from lib.spo2calculator import compute_spo2, _mean


################

#Wi-Fi connection setup
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

################

#Filters
bp_filter_ir = BandpassFilter(fs=100, fc_hp=0.5, fc_lp=8.0)
bp_filter_red = BandpassFilter(fs=100, fc_hp=0.5, fc_lp=8.0) 

#Buffers
BUFFER_SIZE = 100 
red_buffer = []
ir_buffer = []
raw_red_buffer = []
raw_ir_buffer = []

#Parameters for acquisition frequency
compute_frequency = True # we may use it for control it by an input from user
f_HZ = 0 # frequency of data acquisition
t_start = ticks_us() # starting time for acquisition 
samples_n = 0 # number of samples received

#I2C setup
my_SDA_pin = 26
my_SCL_pin = 27
my_i2c_freq = 100000

i2c = I2C(1, sda=Pin(my_SDA_pin), scl=Pin(my_SCL_pin), freq=my_i2c_freq)
print(i2c.scan())

################

## SENSOR SETUP
# setup the max30102
sensor = MAX30102(i2c=i2c)
sensor.setup_sensor()
# Set the number of samples to be averaged by the chip 
sensor.set_fifo_average(2) # set FIFO average to 8 samples
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

#setup the max30205
temp_sensor = MAX30205(i2c=i2c)

################
#Variables for conditions
last_temp = None #Holds last temperature
last_hr = None #Holds last heart rate
hr_count = 0 #Counts the number of times the peaks is not found 
last_spo2 = None #Holds last spo2


while True:
    sensor.check() # check for new data
    
    while sensor.available():
        red_sample = sensor.pop_red_from_storage()
        raw_red_buffer.append(red_sample)
        red_sample_filtered = bp_filter_red.step(red_sample)
        red_buffer.append(red_sample_filtered)


        ir_sample = sensor.pop_ir_from_storage()
        raw_ir_buffer.append(ir_sample)
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

        #First data packet for sending each frame of data
        sample_packet = {
            "type": "sample",
            "red": red_sample_filtered,
            "ir": ir_sample_filtered,
        }

        #Data conversion
        payload_sample = json.dumps(sample_packet) + "\n" # sending json file

        try:
            client_socket.send(payload_sample.encode("utf-8"))
        except OSError:
            client_socket = start_server()


        if len(red_buffer) >= BUFFER_SIZE and len(ir_buffer) >= BUFFER_SIZE:
            
            #Hr Calculation
            hr_result = compute_hr(ir_buffer,f_HZ)

            if hr_result is None:
                # If there is no peak
                print("HR could not be computed")
                hr_count += 1

                if hr_count >= 3:
                    # It counts
                    hr_rate = None
                else:
                    # last_hr can be used for couple of times (optional)
                    hr_rate = last_hr

                peaks_index = []

            else:
                hr_rate, peaks_index = hr_result
    
                if last_hr is not None and hr_rate == last_hr:
                    # The same HR that does not change repeatedly → suspicious
                    hr_count += 1
                    if hr_count >= 3:
                        hr_rate = None
                        peaks_index = []
                        print("HR frozen for 3 cycles, resetting...")
                    else:
                        last_hr = hr_rate
                else:
                    # Normal state: Hr came
                    last_hr = hr_rate
                    hr_count = 0

            #SpO2 Calculation
            spo2 = compute_spo2(ir_buffer, red_buffer, raw_ir_buffer, raw_red_buffer, min_samples=40)
            if spo2 is None:
                spo2 = last_spo2
            else:
                last_spo2 = spo2

            #Temperature Sensing
            try:
                temperature_c = temp_sensor.read_temperature_c()
                last_temp = temperature_c
            except OSError as e:
                print("Temp sensor read error:", e)
                temperature_c = last_temp
                
            #Second data packet for sending calculation results
            result_packet = {
                "type": "result",
                "acq_freq": f_HZ,
                "hr": {
                    "value": hr_rate,
                    "peaks_index": peaks_index
                }, 
                "spo2": spo2,
                "body_temp": temperature_c 
            }

            payload_result = json.dumps(result_packet) + "\n" # sending json file

            try:
                client_socket.send(payload_result.encode("utf-8"))
            except OSError:
                client_socket = start_server()
                 
            #Cleaning the buffers
            red_buffer = []
            ir_buffer = []
            raw_ir_buffer = []
            raw_red_buffer = []
        