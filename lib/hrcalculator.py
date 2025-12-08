import math

def compute_hr(ir_buffer, acq_freq):
    """
    Compute heart rate (HR) in bpm from a filtered IR PPG buffer.

    Parameters
    ----------
    ir_buffer : list[float]
        Recent window of filtered IR samples (e.g. length ~50–200).
    acq_freq : float
        Real acquisition frequency (Hz), e.g. 45.0, 50.0, 60.0 etc.

    Returns
    -------
    result : tuple or None
        (hr_bpm, peaks_index) if a plausible HR could be estimated,
        or None if the signal is not reliable enough.
    """

    # -----------------------------
    # Basic safety checks
    # -----------------------------
    if acq_freq is None or acq_freq <= 0:
        return None
    if ir_buffer is None:
        return None

    n = len(ir_buffer)
    if n < 10:
        # too few samples
        return None

    # -----------------------------
    # Center signal (DC removal)
    # -----------------------------
    mean_val = sum(ir_buffer) / n
    centered = [x - mean_val for x in ir_buffer]

    # Global amplitude / quality check
    max_c = max(centered)
    min_c = min(centered)
    peak_to_peak = max_c - min_c
    max_abs = max(abs(x) for x in centered)

    # Sinyal neredeyse düz veya çok küçük genlikliyse
    # (parmak yok / düzgün PPG yok) → HR hesaplama.
    AMP_MIN = 1.0  # gerekirse 1.0–3.0 arası ince ayar yapılabilir
    if peak_to_peak < AMP_MIN or max_abs == 0.0:
        return None

    # -----------------------------
    # HR & RR design constants
    # -----------------------------
    # Bu projede hedeflediğimiz fizyolojik HR aralığı
    HR_MIN_BPM = 45.0
    HR_MAX_BPM = 140.0

    # Aynı aralığa karşılık gelen RR sınırları (saniye)
    RR_MIN = 60.0 / HR_MAX_BPM   # en kısa RR (~0.43 s)
    RR_MAX = 60.0 / HR_MIN_BPM   # en uzun RR (~1.33 s)

    # Refrakter süre: minimum RR'nin biraz altında
    min_rr_seconds = RR_MIN * 0.8
    min_samples_between_peaks = int(acq_freq * min_rr_seconds)
    if min_samples_between_peaks < 1:
        min_samples_between_peaks = 1

    # -----------------------------
    # Dynamic peak threshold
    # -----------------------------
    # Peak’lerin max genliğin belli bir oranının üstünde olmasını istiyoruz.
    threshold = 0.3 * max_abs  # (0.3–0.7) ayarlanabilir

    # -----------------------------
    # Local-window "winner" ayarı
    # -----------------------------
    # Her aday peak için etrafında ±50 ms pencere açıp
    # bu pencerenin en yüksek noktasını gerçek peak seçiyoruz.
    win_samples = int(0.05 * acq_freq)  # ±50 ms
    if win_samples < 1:
        win_samples = 1

    # -----------------------------
    # Peak detection (local max + window winner + refractory)
    # -----------------------------
    peaks = []
    last_peak_idx = -min_samples_between_peaks  # ilk peak'e serbestlik

    # 1..n-2 arası tarama (komşulara bakmak için)
    for i in range(1, n - 1):
        sample = centered[i]

        # Threshold altında ise geç
        if sample < threshold:
            continue

        # Basit lokal maksimum testi
        if not (sample >= centered[i - 1] and sample >= centered[i + 1]):
            continue

        # Bu noktayı aday peak kabul edip local window winner alalım
        left = max(0, i - win_samples)
        right = min(n - 1, i + win_samples)

        # Pencere içindeki global maksimum index'i
        local_max_idx = left
        local_max_val = centered[left]
        for k in range(left + 1, right + 1):
            if centered[k] > local_max_val:
                local_max_val = centered[k]
                local_max_idx = k

        # Refrakter süreyi seçilen gerçek peak index'ine göre kontrol et
        if (local_max_idx - last_peak_idx) < min_samples_between_peaks:
            continue

        # Bu peak'i kabul et
        peaks.append(local_max_idx)
        last_peak_idx = local_max_idx

    # HR hesaplamak için en az 2 peak lazım
    if len(peaks) < 2:
        return None

    # -----------------------------
    # RR intervals (in seconds)
    # -----------------------------
    rr_intervals = []
    for k in range(1, len(peaks)):
        dt_seconds = (peaks[k] - peaks[k - 1]) / acq_freq
        rr_intervals.append(dt_seconds)

    # -----------------------------
    # RR filtreleme (absürd interval'ları at)
    # -----------------------------
    cleaned_rr = []
    for rr in rr_intervals:
        if RR_MIN <= rr <= RR_MAX:
            cleaned_rr.append(rr)

    if len(cleaned_rr) == 0:
        # Hepsi saçma aralık çıktı
        return None

    # -----------------------------
    # RR → HR (median ile sağlam tahmin)
    # -----------------------------
    cleaned_rr.sort()
    mid = len(cleaned_rr) // 2
    if len(cleaned_rr) % 2 == 1:
        median_rr = cleaned_rr[mid]
    else:
        median_rr = 0.5 * (cleaned_rr[mid - 1] + cleaned_rr[mid])

    if median_rr <= 0:
        return None

    hr_bpm = 60.0 / median_rr

    # Son güvenlik: HR hedef aralıkta mı?
    if not (HR_MIN_BPM <= hr_bpm <= HR_MAX_BPM):
        return None

    return hr_bpm, peaks
