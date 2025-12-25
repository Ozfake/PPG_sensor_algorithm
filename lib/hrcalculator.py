import math

def _refine_peak_index(data, idx):
    """
    Estimates the exact location (fractional index) of the peak 
    using parabolic interpolation.
    """
    # Boundary check
    if idx <= 0 or idx >= len(data) - 1:
        return float(idx)
        
    alpha = data[idx - 1]
    beta = data[idx]
    gamma = data[idx + 1]
    
    # Avoid processing if denominator is zero (flat line)
    denominator = (alpha - 2 * beta + gamma)
    if denominator == 0:
        return float(idx)
        
    p = 0.5 * (alpha - gamma) / denominator
    return idx + p

def compute_hr(ir_buffer, acq_freq):
    """
    Advanced HR calculation with Parabolic Interpolation.
    """

    # 1. Safety Checks
    if acq_freq is None or acq_freq <= 0: return None
    if ir_buffer is None: return None
    n = len(ir_buffer)
    if n < 10: return None

    # 2. DC Removal (Subtract Mean)
    mean_val = sum(ir_buffer) / n
    centered = [x - mean_val for x in ir_buffer]

    # 3. Amplitude Analysis
    max_c = max(centered)
    min_c = min(centered)
    max_abs = max(abs(x) for x in centered)

    # Return if no finger detected or signal is too weak
    AMP_MIN = 1.0 
    if (max_c - min_c) < AMP_MIN or max_abs == 0.0:
        return None

    # --- IMPROVEMENT 1: Adaptive Threshold Clamping ---
    # If max_abs suddenly spikes to 10000, the threshold becomes 3000, 
    # causing us to miss normal beats (e.g., 500).
    # Therefore, we keep max_abs at a "reasonable" level (Saturation).
    # This value (2000) may vary based on ADC settings but is generally safe.
    clamped_max = min(max_abs, 2000.0) 
    threshold = 0.3 * clamped_max

    # 4. Parameters
    HR_MIN_BPM = 40.0
    HR_MAX_BPM = 150.0
    
    # Refractory period (Minimum distance between two peaks)
    # For 150 BPM, at least ~0.4s (400ms) must pass.
    min_rr_seconds = 0.35 
    min_samples_between_peaks = int(acq_freq * min_rr_seconds)
    if min_samples_between_peaks < 1: min_samples_between_peaks = 1
    
    # Peak search window (±50ms)
    win_samples = int(0.05 * acq_freq)
    if win_samples < 1: win_samples = 1

    # 5. Peak Detection
    peaks_indices = []
    last_peak_idx = -min_samples_between_peaks

    for i in range(1, n - 1):
        sample = centered[i]

        if sample < threshold: continue

        # Is it a local maximum?
        if not (sample >= centered[i - 1] and sample >= centered[i + 1]):
            continue

        # Is it the "Winner" within the window?
        left = max(0, i - win_samples)
        right = min(n - 1, i + win_samples)
        
        is_winner = True
        for k in range(left, right + 1):
            if centered[k] > sample:
                is_winner = False
                break
        
        if not is_winner: continue

        # Refractory period check
        if (i - last_peak_idx) < min_samples_between_peaks:
            # If the new peak is larger than the previous one, update the previous one.
            # This prevents confusing the T-wave with the P-wave (dicrotic notch issues).
            if len(peaks_indices) > 0 and sample > centered[peaks_indices[-1]]:
                peaks_indices[-1] = i # Update
                last_peak_idx = i
            continue

        peaks_indices.append(i)
        last_peak_idx = i

    if len(peaks_indices) < 2:
        return None

    # --- IMPROVEMENT 2: Precise RR with Parabolic Interpolation ---
    refined_rr_intervals = []
    
    # Refine the first peak
    prev_refined_idx = _refine_peak_index(centered, peaks_indices[0])

    for k in range(1, len(peaks_indices)):
        curr_idx = peaks_indices[k]
        curr_refined_idx = _refine_peak_index(centered, curr_idx)
        
        # Calculate precise difference (float difference)
        sample_diff = curr_refined_idx - prev_refined_idx
        dt_seconds = sample_diff / acq_freq
        
        refined_rr_intervals.append(dt_seconds)
        prev_refined_idx = curr_refined_idx

    # 6. Filtering and Median
    valid_rr = []
    rr_min_limit = 60.0 / HR_MAX_BPM
    rr_max_limit = 60.0 / HR_MIN_BPM
    
    for rr in refined_rr_intervals:
        if rr_min_limit <= rr <= rr_max_limit:
            valid_rr.append(rr)

    if not valid_rr:
        return None

    valid_rr.sort()
    mid = len(valid_rr) // 2
    if len(valid_rr) % 2 == 1:
        median_rr = valid_rr[mid]
    else:
        median_rr = 0.5 * (valid_rr[mid - 1] + valid_rr[mid])

    if median_rr <= 0: return None

    hr_bpm = 60.0 / median_rr

    return hr_bpm, peaks_indices