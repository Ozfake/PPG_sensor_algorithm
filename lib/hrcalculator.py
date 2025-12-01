import math

def compute_hr(ir_buffer, acq_freq):
    """
    Compute heart rate (HR) in bpm from a filtered IR PPG buffer.

    ir_buffer : list of floats/ints
        Recent window of filtered IR samples (e.g. length ~50–200).
    acq_freq : float
        Real acquisition frequency (Hz), e.g. 95.0, 100.0 etc.

    Returns
    -------
    hr_bpm : float or None
        Estimated heart rate in bpm, or None if not enough info.
    """

    # Basic safety checks 
    if acq_freq <= 0:
        return None
    if ir_buffer is None or len(ir_buffer) < 10:
        # Too few samples
        return None

    # DC removal (center the signal around zero) 
    n = len(ir_buffer)
    mean_val = sum(ir_buffer) / n
    centered = [x - mean_val for x in ir_buffer]

    # Check signal amplitude (avoid noise-only windows) 
    max_abs = max(abs(x) for x in centered)
    if max_abs < 1e-3:
        # Almost flat signal -> no pulsatile information
        return None

    # Dynamic peak threshold 
        # We only accept peaks that are a certain fraction of max amplitude
    threshold = 0.3 * max_abs  # (0.3–0.7)

    # Peak detection with refractory period
        # Max physiological HR ~ 200 bpm → min RR ~ 0.3 s
    min_rr_seconds = 0.3
    min_sample_between_peaks = int(acq_freq * min_rr_seconds)
    if min_sample_between_peaks < 1:
        min_sample_between_peaks = 1

    peaks = []
    last_peak_idx = -min_sample_between_peaks  # allow first peak anywhere

    # Simple local-maximum-based peak detection
    # We skip first and last sample to safely look at i-1 and i+1
    for i in range(1, n - 1):
        sample = centered[i]

        # Above threshold?
        if sample < threshold:
            continue

        # Local maximum?
        if not (sample >= centered[i - 1] and sample >= centered[i + 1]):
            continue

        # Respect refractory period?
        if (i - last_peak_idx) < min_sample_between_peaks:
            continue

        # Accept this as a peak
        peaks.append(i)
        last_peak_idx = i

    # Need at least 2 peaks to compute RR intervals
    if len(peaks) < 2:
        return None

    # Compute RR intervals (in seconds)
    rr_intervals = []
    for k in range(1, len(peaks)):
        # index difference / sampling rate = time difference in seconds
        dt_seconds = (peaks[k] - peaks[k - 1]) / acq_freq
        rr_intervals.append(dt_seconds)

    # Reject absurdly small/large intervals (noise / motion artifacts)
    cleaned_rr = []
    for rr in rr_intervals:
        # Accept only intervals in a plausible range, e.g. 0.3–2.0 s
        if 0.4 <= rr <= 2.0:
            cleaned_rr.append(rr)

    if len(cleaned_rr) == 0:
        return None

    # Average RR → HR in bpm 
    cleaned_rr.sort()
    mid = len(cleaned_rr) // 2
    if len(cleaned_rr) % 2 == 1:
        median_rr = cleaned_rr[mid]
    else:
        median_rr = 0.5 * (cleaned_rr[mid-1] + cleaned_rr[mid])

    hr_bpm = 60.0 / median_rr

    if not (50.0 <= hr_bpm <= 130.0):
        return None

    return hr_bpm, peaks
