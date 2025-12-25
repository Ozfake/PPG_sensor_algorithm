import math

def _mean(values):
    """
    Calculates the arithmetic mean of a list of values.
    """
    n = len(values)
    if n == 0:
        return 0.0
    return sum(values) / n

def _rms(values):
    """
    Root-mean-square (RMS) calculation.
    Used to determine the AC component amplitude.
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
    Compute SpO2 using linear approximation which is more robust for DIY sensors.
    """
    # 1) Basic Checks
    if raw_ir_buffer is None or raw_red_buffer is None:
        return None

    n = min(len(raw_ir_buffer), len(raw_red_buffer), len(ir_buffer), len(red_buffer))

    if n < min_samples:
        return None

    # Get the last n samples
    raw_ir = raw_ir_buffer[-n:]
    raw_red = raw_red_buffer[-n:]
    ir = ir_buffer[-n:]
    red = red_buffer[-n:]

    # 2) DC Component (Mean of raw data)
    dc_ir = _mean(raw_ir)
    dc_red = _mean(raw_red)

    if dc_ir == 0 or dc_red == 0:
        return None

    # 3) AC Component (RMS of filtered data)
    ac_ir = _rms(ir)
    ac_red = _rms(red)

    # Noise Check: AC signal cannot be larger than DC (indicates no finger or excessive movement)
    # We keep this check loose, but if AC is too large, the filter might be unstable.
    if ac_ir > dc_ir or ac_red > dc_red:
        return None 

    if ac_ir == 0 or ac_red == 0:
        return None

    # 4) Ratio-of-ratios (R)
    ratio_red = ac_red / dc_red
    ratio_ir = ac_ir / dc_ir
    
    # Prevention of division by zero error
    if ratio_ir == 0:
        return None

    R = ratio_red / ratio_ir
    
    # 5) SpO2 Formula
    # Old (Quadratic): spo2 = -45.060 * R*R + 30.354 * R + 94.845
    # New (Linear):    spo2 = 104 - 17 * R (Standard Maxim Integrated approach)
    # The linear formula is more consistent and doesn't crash to 0 even if R deviates.
    
    spo2_raw = 104 - 17 * R

    # Calibration Factor
    CAL_k = 1.44 
    
    spo2 = spo2_raw * CAL_k
    
    # 6) Limits (0–100)
    if spo2 < 0:
        spo2 = 0.0 # If still 0, R value is excessively large (>6)
    elif spo2 > 100:
        spo2 = 100.0

    return spo2