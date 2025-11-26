import math

class BandpassFilter:
    """
    Basit 1. dereceden HP + 1. dereceden LP band-pass filtre.
    """

    def __init__(self, fs, fc_hp=0.5, fc_lp=8.0):
        """
        fs     : örnekleme frekansı (Hz) 
        fc_hp  : high-pass cut-off (Hz)   
        fc_lp  : low-pass cut-off (Hz)    
        """
        self.fs = fs
        self.dt = 1.0 / fs

        # HP ve LP için alpha katsayılarını hesapla
        self.hp_alpha = self._calc_alpha(fc_hp)
        self.lp_alpha = self._calc_alpha(fc_lp)

        # Geçmiş değerler (state)
        self.x_prev = 0.0      # önceki input
        self.hp_prev = 0.0     # önceki HP output
        self.lp_prev = 0.0     # önceki LP output

    def _calc_alpha(self, fc):
        """Verilen cut-off frekansı için 1. dereceden filtre alpha değeri."""
        rc = 1.0 / (2.0 * math.pi * fc)  # RC = 1 / (2πfc)
        alpha = self.dt / (rc + self.dt)
        return alpha

    def step(self, x):
        """
        Tek bir örnek işler.
        x : mevcut ham örnek (mesela IR okuman)
        return : band-pass süzülmüş örnek
        """

        # 1) High-pass (yüksek geçiren) - "drift"i temizler
        # y_hp[n] = y_hp[n-1] + alpha_hp * (x[n] - x[n-1])
        hp = self.hp_prev + self.hp_alpha * (x - self.x_prev)

        # state güncelle
        self.hp_prev = hp
        self.x_prev = x

        # 2) Low-pass (alçak geçiren) - yüksek frekans gürültüsünü kırpar
        # y_lp[n] = y_lp[n-1] + alpha_lp * (hp[n] - y_lp[n-1])
        lp = self.lp_prev + self.lp_alpha * (hp - self.lp_prev)

        # state güncelle
        self.lp_prev = lp

        # Sonuç: band-pass süzülmüş örnek
        return lp
