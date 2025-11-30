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


def compute_spo2(ir_buffer, red_buffer, raw_ir_buffer, raw_red_buffer, min_samples=40):
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
    if raw_ir_buffer is None or raw_red_buffer is None:
        return None

    n_ir = len(ir_buffer)
    n_red = len(red_buffer)
    n_raw_ir = len(raw_ir_buffer)
    n_raw_red = len(raw_red_buffer)

    
    # Güvenlik: iki buffer uzunluğu farklıysa küçük olanı baz al
    n = min(n_raw_ir, n_raw_red, n_ir, n_red)

    if n < min_samples:
        return None

    raw_ir = raw_ir_buffer[-n:]
    raw_red = raw_red_buffer[-n:]
    ir = ir_buffer[-n:]
    red = red_buffer[-n:]

    # 2) DC bileşen (ortalama)
    dc_ir = _mean(raw_ir)
    dc_red = _mean(raw_red)

    if dc_ir == 0 or dc_red == 0:
        return None

    # 3) AC bileşen (ortalama etrafındaki dalgalanma)
    ac_ir = _rms(ir)
    ac_red = _rms(red)

    if dc_ir == 0 or dc_red == 0 or ac_ir == 0 or ac_red == 0:
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

    # DEBUG
    print("DEBUG:",
      "dc_ir=", dc_ir,
      "dc_red=", dc_red,
      "ac_ir=", ac_ir,
      "ac_red=", ac_red,
      "R=", R,
      "spo2=", spo2)


    return spo2
