import math

class BandpassFilter:
    """
    Simple 1st order HP + 1st order LP band-pass filter.
    """

    def __init__(self, fs, fc_hp=0.7, fc_lp=4.0):
        """
        fs     : sampling frequency (Hz) 
        fc_hp  : high-pass cut-off (Hz)   
        fc_lp  : low-pass cut-off (Hz)    
        """
        self.fs = fs
        self.dt = 1.0 / fs

        # Calculate alpha coefficients for HP and LP
        self.hp_alpha = self._calc_alpha(fc_hp)
        self.lp_alpha = self._calc_alpha(fc_lp)

        # Past values (state)
        self.x_prev = 0.0      # önceki input
        self.hp_prev = 0.0     # önceki HP output
        self.lp_prev = 0.0     # önceki LP output

    def _calc_alpha(self, fc):
        """The alpha value of the 1st order filter for the given cut-off frequency."""
        rc = 1.0 / (2.0 * math.pi * fc)  # RC = 1 / (2πfc)
        alpha = self.dt / (rc + self.dt)
        return alpha

    def step(self, x):
        # --- 1) PASS 1 ---
        # High-pass
        hp1 = self.hp_prev + self.hp_alpha * (x - self.x_prev)
        # Update input memory
        self.x_prev = x
        # Low-pass
        lp1 = self.lp_prev + self.lp_alpha * (hp1 - self.lp_prev)

        # Şimdi pass-1 state'lerini pass-2 için hazırlıyoruz
        self.hp_prev = hp1
        self.lp_prev = lp1

        # --- 2) PASS 2 ---
        # High-pass tekrar
        hp2 = self.hp_prev + self.hp_alpha * (lp1 - self.x_prev)
        # Burada x_prev pass-1 input'u (yani raw x), pass-2 için güncelle:
        self.x_prev = lp1
        # Low-pass tekrar
        lp2 = self.lp_prev + self.lp_alpha * (hp2 - self.lp_prev)

        # Update final states
        self.hp_prev = hp2
        self.lp_prev = lp2

        return lp2
