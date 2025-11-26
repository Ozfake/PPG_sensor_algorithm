import math

def _mean(values):
    n = len(values)
    if n == 0:
        return 0.0
    return sum(values) / n


def _rms(values):
    """
    Root-mean-square (RMS) of values.
    AC bileşenin büyüklüğünü temsil etmek için kullanıyoruz.
    """
    n = len(values)
    if n == 0:
        return 0.0
    s = 0.0
    for v in values:
        s += v * v
    return (s / n) ** 0.5


def compute_spo2(ir_buffer, red_buffer, min_samples=40):
    """
    Compute SpO2 from IR and RED buffers using a simple ratio-of-ratios method.

    Parameters
    ----------
    ir_buffer : list of int/float
        Filtered IR samples.
    red_buffer : list of int/float
        Filtered RED samples.
    min_samples : int
        Minimum number of samples required to compute a stable SpO2.

    Returns
    -------
    float or None
        Estimated SpO2 value in %, or None if not enough data / invalid.
    """

    # 1) Temel kontroller
    if ir_buffer is None or red_buffer is None:
        return None

    n_ir = len(ir_buffer)
    n_red = len(red_buffer)

    if n_ir < min_samples or n_red < min_samples:
        # Yeterli örnek yok -> hesaplama yok
        return None

    # Güvenlik: iki buffer uzunluğu farklıysa küçük olanı baz al
    n = min(n_ir, n_red)
    ir = ir_buffer[-n:] # son n örnek
    red = red_buffer[-n:]

    # 2) DC bileşen (ortalama)
    dc_ir = _mean(ir)
    dc_red = _mean(red)

    if dc_ir == 0 or dc_red == 0:
        return None

    # 3) AC bileşen (ortalama etrafındaki dalgalanma)
    ir_ac = [v - dc_ir for v in ir]
    red_ac = [v - dc_red for v in red]

    ac_ir = _rms(ir_ac)
    ac_red = _rms(red_ac)

    if ac_ir == 0 or ac_red == 0:
        return None

    # 4) Ratio-of-ratios R = (AC_red/DC_red) / (AC_ir/DC_ir)
    ratio_red = ac_red / dc_red
    ratio_ir = ac_ir / dc_ir

    R = ratio_red / ratio_ir

    # 5) Empirik polinom: SpO2 = -45.060 * R^2 + 30.354 * R + 94.845
    spo2 = -45.060 * (R * R) + 30.354 * R + 94.845

    # 6) Limitler (0–100)
    if spo2 < 0:
        spo2 = 0.0
    elif spo2 > 100:
        spo2 = 100.0

    return spo2
