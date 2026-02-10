import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from tqdm import tqdm
import os
from datetime import datetime

# === FIXED INPUT PATHS ===
predicted_txt = "./Predictions/lactate.tsv"
sample_csv = "./topspin/sample_lactate.csv"
base_name = os.path.splitext(os.path.basename(predicted_txt))[0]

# === OUTPUT FOLDERS ===
plot_folder = f"./QC_spectra/{base_name}"
report_folder = f"./QC_reports/{base_name}"
os.makedirs(plot_folder, exist_ok=True)
os.makedirs(report_folder, exist_ok=True)

# === OUTPUT FILE PATHS ===
output_cleaned_txt = f"./predictions/{base_name}_cleaned.txt"
output_plot = os.path.join(plot_folder, "sample_vs_predicted_QC_plot.png")
output_qc_report = os.path.join(report_folder, f"qc_report_{base_name}.txt")

# === Function to load and clean spectrum ===
def load_clean_tsv(path):
    df = pd.read_csv(path, sep="\t", header=None, names=["ppm", "intensity"], low_memory=False)
    df["ppm"] = pd.to_numeric(df["ppm"], errors="coerce")
    df["intensity"] = pd.to_numeric(df["intensity"], errors="coerce")
    return df[(df["ppm"] >= -2) & (df["ppm"] <= 14)].dropna()

# === Run QC with Progress Bar ===
with tqdm(total=11, desc="Running QC", ncols=100, unit="step") as pbar:

    pred_df = load_clean_tsv(predicted_txt)
    sample_df = pd.read_csv(sample_csv)
    pbar.update(1)

    pred_df["intensity"] /= pred_df["intensity"].max()
    sample_df["intensity"] /= sample_df["intensity"].max()
    pbar.update(1)

    peaks_pred, _ = find_peaks(pred_df["intensity"], height=0.1)
    peaks_sample, _ = find_peaks(sample_df["intensity"], height=0.1)
    ppm_peaks_pred = pred_df["ppm"].iloc[peaks_pred].values
    ppm_peaks_sample = sample_df["ppm"].iloc[peaks_sample].values
    tolerance = 0.2
    matched_peaks = [s for s in ppm_peaks_sample if np.any(np.abs(s - ppm_peaks_pred) < tolerance)]
    unmatched_peaks = [s for s in ppm_peaks_sample if s not in matched_peaks]
    pbar.update(1)

    signal_region = sample_df.query("0.5 <= ppm <= 4")["intensity"]
    noise_region = sample_df.query("9 <= ppm <= 10")["intensity"]
    noise_std = noise_region.std()
    snr = signal_region.max() / noise_std if noise_std > 0 else np.inf
    pbar.update(1)

    lw_df = sample_df.query("-0.1 <= ppm <= 0.1").sort_values("ppm")
    half_max = lw_df["intensity"].max() / 2
    crossings = lw_df[np.abs(lw_df["intensity"] - half_max) < 0.02]
    linewidth_ppm = crossings["ppm"].max() - crossings["ppm"].min() if not crossings.empty else np.nan
    pbar.update(1)

    baseline_region = sample_df.query("9 <= ppm <= 10")
    sine_flag = "PASS" if baseline_region["intensity"].std() < 0.02 else "FAIL — possible sine wiggle"
    pbar.update(1)

    water_region = sample_df.query("0.2 <= ppm <= 0.4")
    water_flag = "PASS" if water_region["intensity"].max() < 0.2 else "FAIL — high water signal"
    pbar.update(1)

    pred_df.to_csv(output_cleaned_txt, sep="\t", index=False, header=False)
    pbar.update(1)

    plt.figure(figsize=(10, 5))
    plt.plot(sample_df["ppm"], sample_df["intensity"], label="Sample", color="black")
    plt.plot(pred_df["ppm"], pred_df["intensity"], label="Predicted", color="blue", alpha=0.7)
    plt.xlabel("Chemical Shift (ppm)")
    plt.ylabel("Normalized Intensity")
    plt.title("Sample vs Predicted Spectrum")
    plt.legend()
    plt.gca().invert_xaxis()
    plt.tight_layout()
    plt.savefig(output_plot, dpi=300)
    plt.close()
    pbar.update(1)

    with open(output_qc_report, "w") as f:
        f.write(f"QC Report for {base_name} Spectrum\n")
        f.write("=" * 40 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Sample file: {os.path.basename(sample_csv)}\n")
        f.write(f"Predicted file: {os.path.basename(predicted_txt)}\n\n")
        f.write(f"Total sample peaks: {len(ppm_peaks_sample)}\n")
        f.write(f"Matched peaks: {len(matched_peaks)} of {len(ppm_peaks_pred)} predicted ({100 * len(matched_peaks) / len(ppm_peaks_pred):.1f}%)\n")
        f.write(f"Unmatched sample peaks: {len(unmatched_peaks)}\n")
        f.write(f"Estimated SNR (max signal / noise std): {snr:.2f}\n")
        f.write(f"Linewidth @ 0 ppm: {linewidth_ppm:.4f} ppm\n")
        f.write(f"Baseline check (9–10 ppm): {sine_flag}\n")
        f.write(f"Water suppression (0.2–0.4 ppm): {water_flag}\n")
    pbar.update(1)

    with open(output_qc_report, "r") as f:
        print("\n" + f.read())
    pbar.update(1)

print("✅ QC complete.")
