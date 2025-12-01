from machine import I2C

class MAX30205:
    def __init__(self, i2c, address=0x48):
        self.i2c = i2c
        self.address = address

    def read_temperature_c(self):
        # temp register 0x00: 2 byte
        data = self.i2c.readfrom_mem(self.address, 0x00, 2)
        raw = (data[0] << 8) | data[1]

        # two's complement
        if raw & 0x8000:
            raw -= 1 << 16

        temp = raw / 256.0

        # Eğer çok düşük çıktıysa → sensör extended formatta
        if temp < -10:
            temp += 64.0

        return temp
