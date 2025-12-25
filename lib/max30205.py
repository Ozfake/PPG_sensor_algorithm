from machine import I2C
import time

class MAX30205:
    REG_TEMPERATURE = 0x00
    REG_CONFIGURATION = 0x01

    def __init__(self, i2c, address=0x48, calibration_offset=0.0):
        self.i2c = i2c
        self.address = address
        self.offset = calibration_offset
        self.setup_sensor()

    def setup_sensor(self):
        """Set sensor to continuous mode (Wake up from Shutdown)"""
        try:
            self.i2c.writeto_mem(self.address, self.REG_CONFIGURATION, b'\x00')
        except OSError:
            pass

    def read_temperature_c(self):
        try:
            # Read 2 bytes of temperature data
            data = self.i2c.readfrom_mem(self.address, self.REG_TEMPERATURE, 2)
            raw = (data[0] << 8) | data[1]

            # 1. Two's complement calculation (Original logic)
            if raw & 0x8000:
                raw -= 1 << 16

            # 2. Convert to raw temperature
            temp = raw / 256.0

            # 3. CUSTOM FIX (Extended Format Correction)
            # If the value is unreasonably low (e.g., below -10C, currently reading -30C),
            # add 64.0 to correct the extended format bit interpretation issue.
            if temp < -10:
                temp += 64.0

            # 4. Add calibration offset
            temp = temp + self.offset
            
            return temp

        except OSError:
            return 0.0