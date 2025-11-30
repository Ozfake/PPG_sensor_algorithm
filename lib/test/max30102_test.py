from machine import SoftI2C, Pin
from max30102 import MAX30102, MAX30105_PULSE_AMP_MEDIUM

i2c = SoftI2C(sda=Pin(26), scl=Pin(27), freq=100000)

print("Scan:", i2c.scan())

print("Creating sensor...")
sensor = MAX30102(i2c=i2c)

print("Calling setup_sensor()...")
sensor.setup_sensor()

print("Sensor initialized OK.")
