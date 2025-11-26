# max30205.py
# Clean MicroPython Driver for MAX30205 Human Body Temperature Sensor
# Compatible with Raspberry Pi Pico / Pico W

from machine import I2C

class MAX30205:
    """
    Simple MicroPython driver for MAX30205 temperature sensor.
    Auto-handles I2C address and temperature conversion.
    """

    def __init__(self, i2c: I2C, address: int = 0x48):
        """
        i2c     : SoftI2C or I2C object
        address : default 0x48 for most MAX30205 breakout boards
        """
        self.i2c = i2c
        self.address = address

    def read_raw(self):
        """
        Reads 2 bytes from temperature register (0x00)
        Returns signed 16-bit raw value.
        """
        data = self.i2c.readfrom_mem(self.address, 0x00, 2)
        raw = (data[0] << 8) | data[1]

        # Convert from 16-bit two's complement
        if raw & 0x8000:
            raw -= (1 << 16)

        return raw

    def read_temperature_c(self) -> float:
        """
        Returns temperature in Celsius with 1/256 °C resolution.
        """
        raw = self.read_raw()
        temp_c = raw / 256.0
        return temp_c

    def shutdown(self):
        """
        Put sensor into low-power shutdown mode.
        """
        config = self._read_config()
        config |= (1 << 8)  # set SHDN bit
        self._write_config(config)

    def wake(self):
        """
        Wake sensor from shutdown mode.
        """
        config = self._read_config()
        config &= ~(1 << 8)  # clear SHDN bit
        self._write_config(config)

    def one_shot(self) -> float:
        """
        Performs a one-shot measurement (useful for power saving).
        Returns temperature in °C.
        """
        config = self._read_config()
        config |= (1 << 15)   # OS bit
        self._write_config(config)

        # After the bit is set, the measurement completes immediately
        return self.read_temperature_c()

    # --- internal helpers ---

    def _read_config(self) -> int:
        data = self.i2c.readfrom_mem(self.address, 0x01, 2)
        return (data[0] << 8) | data[1]

    def _write_config(self, value: int):
        high = (value >> 8) & 0xFF
        low  = value & 0xFF
        self.i2c.writeto_mem(self.address, 0x01, bytes([high, low]))
