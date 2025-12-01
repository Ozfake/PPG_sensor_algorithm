import math

class BandpassFilter:
    """
    Simple 1st order HP + 1st order LP band-pass filter.
    """

    def __init__(self, fs, fc_hp=0.5, fc_lp=8.0):
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
        # 1) High-pass
        # y_hp[n] = y_hp[n-1] + alpha_hp * (x[n] - x[n-1])
        hp = self.hp_prev + self.hp_alpha * (x - self.x_prev)

        # Update state
        self.hp_prev = hp
        self.x_prev = x

        # 2) Low-pass
        # y_lp[n] = y_lp[n-1] + alpha_lp * (hp[n] - y_lp[n-1])
        lp = self.lp_prev + self.lp_alpha * (hp - self.lp_prev)

        # Update state
        self.lp_prev = lp

        # Result: band-pass filtered sample
        return lp
