"""
Plot the anomalous-event waveform dumps written by the acquisition engine
when POSITRON_DUMP_ANOMALIES=1 (see AnomalyDumper in positron/scope/acquisition.py).

Usage (from the repo root):
    py tools/plot_anomalies.py                 # newest dump dir, interactive windows
    py tools/plot_anomalies.py <dir>           # a specific dump directory
    py tools/plot_anomalies.py --kind normal   # only the reference events
    py tools/plot_anomalies.py --save          # write PNGs next to the .npz files
    py tools/plot_anomalies.py --max 10

Each figure has one row per channel. The anomalous segment is drawn in colour
with the trigger at t = 0. The previous and next segments of the same batch are
drawn faintly to the left and right, laid end-to-end as if the scope captured
them back-to-back (the real gap between segments is not recorded). Lines mark
the trigger (-5 mV), the mean-of-pre-trigger baseline the analysis used, and
the CFD threshold when the channel had a pulse.

Not shipped with the application; developer tooling only.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

TRIGGER_MV = -5.0
CHANNELS = ["A", "B", "C", "D"]
COLORS = {"A": "tab:blue", "B": "tab:orange", "C": "tab:green", "D": "tab:red"}


def newest_dump_dir() -> Path:
    root = Path.home() / ".positron" / "debug"
    dirs = sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []
    if not dirs:
        sys.exit(f"No dump directories under {root}")
    return dirs[-1]


def scalar(d, key, default=None):
    if key not in d:
        return default
    v = d[key]
    return v.item() if isinstance(v, np.ndarray) and v.shape == () else v


def describe(d) -> str:
    lines = []
    for prefix, label in (("prev_", "prev"), ("", "THIS"), ("next_", "next")):
        if prefix + "event_id" not in d:
            continue
        parts = []
        for ch in CHANNELS:
            if f"{prefix}{ch}" not in d:
                continue
            hp = bool(scalar(d, f"{prefix}{ch}_has_pulse"))
            t = scalar(d, f"{prefix}{ch}_timing_ns")
            e = scalar(d, f"{prefix}{ch}_energy")
            pk = scalar(d, f"{prefix}{ch}_peak_mv")
            flag = "*" if hp else " "
            parts.append(f"{ch}{flag} t={t:8.2f}ns E={e:9.0f} pk={pk:6.1f}")
        lines.append(f"  {label:4s} ev {int(scalar(d, prefix + 'event_id')):7d}: " + " | ".join(parts))
    return "\n".join(lines)


def plot_file(path: Path, save: bool) -> None:
    d = np.load(path, allow_pickle=False)
    t = d["time_ns"] / 1000.0  # us
    window_us = (t[-1] - t[0]) + (t[1] - t[0])
    pre = int(scalar(d, "pre_trigger_samples"))
    frac = float(scalar(d, "cfd_fraction"))

    print(f"\n{path.name}  ({scalar(d, 'kind')}, {scalar(d, 'scope_variant')}, "
          f"{scalar(d, 'sample_interval_ns')} ns/sample, segment {scalar(d, 'segment_index')}"
          f"/{scalar(d, 'batch_size')})")
    print(describe(d))

    fig, axes = plt.subplots(4, 1, figsize=(13, 10), sharex=True)
    for ax, ch in zip(axes, CHANNELS):
        if ch not in d:
            ax.set_visible(False)
            continue
        wf = d[ch]
        if f"prev_{ch}" in d:
            ax.plot(t - window_us, d[f"prev_{ch}"], color=COLORS[ch], alpha=0.3, lw=0.8, label="prev segment")
        if f"next_{ch}" in d:
            ax.plot(t + window_us, d[f"next_{ch}"], color=COLORS[ch], alpha=0.3, lw=0.8, label="next segment")
        ax.plot(t, wf, color=COLORS[ch], lw=1.0, label="this segment")

        baseline = float(np.mean(wf[:pre]))
        ax.axhline(baseline, color="k", ls="--", lw=0.8, label=f"baseline {baseline:.2f} mV")
        ax.axhline(TRIGGER_MV, color="gray", ls=":", lw=0.8, label="trigger -5 mV")
        hp = bool(scalar(d, f"{ch}_has_pulse"))
        if hp:
            thr = baseline - frac * float(scalar(d, f"{ch}_peak_mv"))
            ax.axhline(thr, color="m", ls=":", lw=0.8, label=f"CFD thr {thr:.1f} mV")
            ax.axvline(float(scalar(d, f"{ch}_timing_ns")) / 1000.0, color="m", lw=0.8)
        for x in (t[0], t[0] + window_us, t[0] - window_us, t[0] + 2 * window_us):
            ax.axvline(x, color="0.6", lw=0.6)
        ax.axvline(0.0, color="k", lw=0.8)

        e = scalar(d, f"{ch}_energy")
        tt = scalar(d, f"{ch}_timing_ns")
        ax.set_ylabel(f"{ch} (mV)")
        ax.set_title(f"Ch {ch}: has_pulse={hp}  t={tt:.2f} ns  E={e:.0f} mV*ns  "
                     f"peak={scalar(d, f'{ch}_peak_mv'):.1f} mV", fontsize=9, loc="left")
        ax.legend(fontsize=7, loc="lower right", ncol=3)
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel("time relative to this segment trigger (us); neighbours laid end-to-end")
    fig.suptitle(f"{path.name}  event {int(scalar(d, 'event_id'))}", fontsize=11)
    fig.tight_layout()
    if save:
        out = path.with_suffix(".png")
        fig.savefig(out, dpi=110)
        plt.close(fig)
        print(f"  -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("directory", nargs="?", help="dump directory (default: newest)")
    ap.add_argument("--kind", choices=["anomaly", "normal", "all"], default="all")
    ap.add_argument("--max", type=int, default=20, help="max files to plot")
    ap.add_argument("--save", action="store_true", help="save PNGs instead of showing windows")
    args = ap.parse_args()

    directory = Path(args.directory) if args.directory else newest_dump_dir()
    pattern = "*.npz" if args.kind == "all" else f"{args.kind}_*.npz"
    files = sorted(directory.glob(pattern))
    print(f"{directory}: {len(files)} file(s) matching {pattern}")
    for path in files[: args.max]:
        plot_file(path, args.save)
    if not args.save and files:
        plt.show()


if __name__ == "__main__":
    main()
