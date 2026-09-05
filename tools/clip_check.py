"""
Check a Positron CSV export for ADC clipping and energy/peak linearity.

Answers the question "is the 1275 keV peak compressed because the largest
pulses hit the voltage-range rail?" using the X_energy_raw and X_peak_mv
columns written by the Home panel export.

Usage (from the repo root):
    py tools/clip_check.py export.csv                 # auto-locate the top peak
    py tools/clip_check.py export.csv --region 1175:1375        # keV (calibrated)
    py tools/clip_check.py export.csv --region A=900:1100 --region B=880:1080
    py tools/clip_check.py export.csv --save         # write PNGs next to the CSV
    py tools/clip_check.py a.csv b.csv               # compare runs (e.g. 100 vs 200 mV)

Per channel it reports, for accepted pulses (X_has_pulse TRUE):
  * the fraction whose peak reached the rail (peak_mv within 2 LSB of the
    voltage range recorded in the CSV header), overall and inside the
    selected photopeak region;
  * the region's energy centroid (raw mV*ns, and keV when calibrated), which
    is what the two-point calibration uses;
  * the effective width energy/peak (ns) below and inside the region: for an
    unclipped detector this is constant, clipping makes it grow.

and draws energy vs. peak amplitude with the rail marked, plus the peak
histogram of the region. The energy axis is keV when the channel was
calibrated at export time, raw mV*ns otherwise; --region values are in the
same units. Regions given with --region apply to every file.

Not shipped with the application; developer tooling only.
"""

import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np

CHANNELS = ["A", "B", "C", "D"]
COLORS = {"A": "tab:blue", "B": "tab:orange", "C": "tab:green", "D": "tab:red"}
ADC_LEVELS = 127          # 8-bit ADC: full scale = 127 LSB either side of zero
CLIP_MARGIN_LSB = 2.0     # peak within this many LSB of the rail counts as clipped
AUTO_REGION_HALF_WIDTH = 0.08  # +-8 % around the located photopeak


def load_csv(path: Path):
    """Return (range_mv, per-channel dict of arrays)."""
    range_mv = None
    header = None
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for line in f:
            if line.startswith("#"):
                m = re.search(r"Voltage Range:\s*([\d.]+)\s*mV", line)
                if m:
                    range_mv = float(m.group(1))
                continue
            if header is None:
                header = next(csv.reader([line]))
                continue
            rows.append(next(csv.reader([line])))
    if header is None or not rows:
        sys.exit(f"{path}: no data rows")
    if range_mv is None:
        print(f"{path}: no 'Voltage Range' header line; assuming 100 mV")
        range_mv = 100.0
    col = {name: i for i, name in enumerate(header)}
    for ch in CHANNELS:
        for suffix in ("has_pulse", "energy_kev", "energy_raw", "peak_mv"):
            if f"{ch}_{suffix}" not in col:
                sys.exit(f"{path}: missing column {ch}_{suffix} "
                         "(export from a build that writes energy_raw/peak_mv)")

    data = {}
    for ch in CHANNELS:
        accepted = np.array([r[col[f"{ch}_has_pulse"]] == "TRUE" for r in rows])
        raw = np.array([float(r[col[f"{ch}_energy_raw"]]) for r in rows])
        peak = np.array([float(r[col[f"{ch}_peak_mv"]]) for r in rows])
        kev_col = [r[col[f"{ch}_energy_kev"]] for r in rows]
        calibrated = all(v != "N/A" for v in kev_col)
        kev = np.array([float(v) for v in kev_col]) if calibrated else None
        data[ch] = dict(
            raw=raw[accepted], peak=peak[accepted],
            kev=kev[accepted] if calibrated else None,
            n_total=len(rows),
        )
    return range_mv, data


def auto_region(energy: np.ndarray):
    """
    Locate the highest-energy prominent peak (the 1275 keV photopeak in a
    Na-22 spectrum) and return (lo, hi) around it, or None.
    """
    if len(energy) < 200:
        return None
    hist, edges = np.histogram(energy, bins=200, range=(0, np.percentile(energy, 99.9)))
    centers = 0.5 * (edges[:-1] + edges[1:])
    kernel = np.ones(5) / 5.0
    smooth = np.convolve(hist, kernel, mode="same")
    floor = 0.05 * smooth.max()
    # Local maxima above the floor, ignoring the first bins (dark pulses, noise)
    peaks = [i for i in range(3, len(smooth) - 3)
             if smooth[i] >= floor
             and smooth[i] >= smooth[i - 3:i + 4].max()
             and smooth[i] > smooth[i - 3] and smooth[i] > smooth[i + 3]]
    if not peaks:
        return None
    center = centers[peaks[-1]]
    return center * (1 - AUTO_REGION_HALF_WIDTH), center * (1 + AUTO_REGION_HALF_WIDTH)


def parse_regions(specs):
    """--region lo:hi or --region A=lo:hi (repeatable) -> {channel: (lo, hi)}."""
    regions = {}
    for spec in specs or []:
        chans = CHANNELS
        if "=" in spec:
            ch, spec = spec.split("=", 1)
            chans = [ch.strip().upper()]
        lo, hi = (float(v) for v in spec.split(":"))
        for ch in chans:
            regions[ch] = (lo, hi)
    return regions


def analyse(path: Path, range_mv: float, data, regions, save: bool, show: bool):
    import matplotlib.pyplot as plt

    lsb = range_mv / ADC_LEVELS
    clip_level = range_mv - CLIP_MARGIN_LSB * lsb
    print(f"\n=== {path.name}: range {range_mv:.0f} mV, LSB {lsb:.2f} mV, "
          f"clipped if peak >= {clip_level:.1f} mV ===")

    fig, axes = plt.subplots(2, 4, figsize=(16, 7))
    fig.suptitle(f"{path.name} - {range_mv:.0f} mV range")

    for j, ch in enumerate(CHANNELS):
        d = data[ch]
        peak, raw, kev = d["peak"], d["raw"], d["kev"]
        n = len(peak)
        ax_sc, ax_h = axes[0, j], axes[1, j]
        if n == 0:
            print(f"{ch}: no accepted pulses")
            ax_sc.set_title(f"{ch}: no pulses")
            continue

        energy = kev if kev is not None else raw
        unit = "keV" if kev is not None else "mV*ns"
        clipped = peak >= clip_level
        print(f"{ch}: {n} accepted pulses, max peak {peak.max():.1f} mV, "
              f"clipped {clipped.sum()} ({100 * clipped.mean():.2f} %)")

        region = regions.get(ch) or auto_region(energy)
        if region is None:
            print(f"   no photopeak region (give --region)")
        else:
            lo, hi = region
            sel = (energy >= lo) & (energy <= hi)
            m = sel.sum()
            src = "given" if ch in regions else "auto"
            if m == 0:
                print(f"   region {lo:.1f}-{hi:.1f} {unit} ({src}): empty")
            else:
                cen_raw = raw[sel].mean()
                cen_txt = f"centroid {cen_raw:.1f} mV*ns"
                if kev is not None:
                    cen_txt += f" = {kev[sel].mean():.1f} keV"
                width_in = np.median(raw[sel] / peak[sel])
                below = (energy < lo) & (energy > 0.4 * lo)
                width_below = np.median(raw[below] / peak[below]) if below.sum() >= 10 else float("nan")
                print(f"   region {lo:.1f}-{hi:.1f} {unit} ({src}): {m} pulses, "
                      f"clipped {sel[clipped].sum()} ({100 * clipped[sel].mean():.1f} %), "
                      f"{cen_txt}")
                print(f"   effective width energy/peak: {width_in:.0f} ns in region, "
                      f"{width_below:.0f} ns for 0.4-1.0 x region")

        # Energy vs peak scatter (subsample for speed)
        idx = np.random.default_rng(0).permutation(n)[:20000]
        ax_sc.scatter(peak[idx], energy[idx], s=2, alpha=0.3, color=COLORS[ch])
        ax_sc.axvline(range_mv, color="k", ls="--", lw=1, label=f"rail {range_mv:.0f} mV")
        ax_sc.axvline(clip_level, color="r", ls=":", lw=1, label="clip level")
        if region is not None:
            ax_sc.axhspan(region[0], region[1], color="gray", alpha=0.15, label="region")
        ax_sc.set_xlabel("peak amplitude (mV)")
        ax_sc.set_ylabel(f"energy ({unit})")
        ax_sc.set_title(f"{ch}: {100 * clipped.mean():.1f} % clipped")
        ax_sc.set_xlim(0, range_mv * 1.05)
        ax_sc.legend(fontsize=7, loc="upper left")

        # Peak histogram, all pulses and region
        bins = np.linspace(0, range_mv * 1.05, 106)
        ax_h.hist(peak, bins=bins, color="lightgray", label="all accepted")
        if region is not None and sel.any():
            ax_h.hist(peak[sel], bins=bins, color=COLORS[ch], alpha=0.8, label="region")
        ax_h.axvline(range_mv, color="k", ls="--", lw=1)
        ax_h.axvline(clip_level, color="r", ls=":", lw=1)
        ax_h.set_xlabel("peak amplitude (mV)")
        ax_h.set_ylabel("pulses")
        ax_h.set_yscale("log")
        ax_h.legend(fontsize=7)

    fig.tight_layout()
    if save:
        out = path.with_suffix(".clip_check.png")
        fig.savefig(out, dpi=120)
        print(f"saved {out}")
    if not show:
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+", type=Path)
    ap.add_argument("--region", action="append", metavar="[CH=]LO:HI",
                    help="photopeak region in the energy column's units (keV if calibrated, else mV*ns)")
    ap.add_argument("--save", action="store_true", help="write <csv>.clip_check.png")
    ap.add_argument("--no-show", action="store_true", help="do not open figure windows")
    args = ap.parse_args()

    regions = parse_regions(args.region)
    import matplotlib
    if args.no_show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for path in args.csv:
        range_mv, data = load_csv(path)
        analyse(path, range_mv, data, regions, args.save, not args.no_show)
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
