import math

class BandpassFilter:
    """
    Standard 1st Order High-Pass + 1st Order Low-Pass Filter.
    Optimized for PPG signals.
    """

    def __init__(self, fs, fc_hp=0.5, fc_lp=5.0):
        """
        fs    : Sampling frequency (Hz) - e.g., 50Hz or 100Hz
        fc_hp : High-pass cutoff frequency (to remove DC component, e.g., 0.5Hz)
        fc_lp : Low-pass cutoff frequency (to remove noise, e.g., 5.0Hz)
        """
        self.fs = fs
        self.dt = 1.0 / fs

        # --- ALPHA CALCULATIONS ---
        
        # 1. Low Pass Alpha (Traditional RC circuit logic)
        # alpha_lp = dt / (RC + dt)
        rc_lp = 1.0 / (2.0 * math.pi * fc_lp)
        self.alpha_lp = self.dt / (rc_lp + self.dt)

        # 2. High Pass Alpha (Traditional structure)
        # alpha_hp = RC / (RC + dt)
        rc_hp = 1.0 / (2.0 * math.pi * fc_hp)
        self.alpha_hp = rc_hp / (rc_hp + self.dt)

        # --- STATE (MEMORY) VARIABLES ---
        self.y_lp_prev = 0.0 # Previous Low-Pass output
        self.y_hp_prev = 0.0 # Previous High-Pass output
        self.x_prev    = 0.0 # Previous raw input (Required for High-Pass)

    def step(self, x):
        """
        Called for every new sample (x).
        First, High-Pass is applied, then the result is passed to Low-Pass.
        """
        
        # --- STEP 1: High-Pass Filter (DC Blocking) ---
        # Formula: y[i] = alpha * (y[i-1] + x[i] - x[i-1])
        # This process pulls the signal mean to 0 (centers the pulse wave).
        y_hp = self.alpha_hp * (self.y_hp_prev + x - self.x_prev)

        # --- STEP 2: Low-Pass Filter (Smoothing) ---
        # We use the output of the High-Pass (y_hp) as input.
        # Formula: y[i] = y[i-1] + alpha * (x[i] - y[i-1])
        y_lp = self.y_lp_prev + self.alpha_lp * (y_hp - self.y_lp_prev)

        # --- STEP 3: Update Memory ---
        self.x_prev    = x
        self.y_hp_prev = y_hp
        self.y_lp_prev = y_lp

        # Return the filtered (Bandpass) data as the result
        return y_lp

    def reset(self):
        """Resets filter memory (used if necessary)"""
        self.y_lp_prev = 0.0
        self.y_hp_prev = 0.0
        self.x_prev    = 0.0