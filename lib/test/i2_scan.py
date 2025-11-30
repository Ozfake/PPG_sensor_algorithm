from machine import SoftI2C, Pin

my_SDA_pin = 26
my_SCL_pin = 27
my_i2c_freq = 100000  # önce 100 kHz deneyelim

i2c = SoftI2C(
    sda=Pin(my_SDA_pin),
    scl=Pin(my_SCL_pin),
    freq=my_i2c_freq
)

print("I2C scan starting...")
devices = i2c.scan()
print("Found devices:", devices)
