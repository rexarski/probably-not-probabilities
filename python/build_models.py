"""Train two miscalibrated classifiers on Spotify hit-song data and emit JSON for the web app.

Outputs (written to ../web/static/data/):
  - holdout.json       : per-row scores from over/under-confident models + true labels
  - reliability.json   : binned reliability curves for well-calibrated, over, under
  - metrics.json       : ECE, Brier, accuracy, precision/recall by threshold
  - calibrated.json    : Platt + isotonic calibrated scores for the over-confident model
  - sample_rows.json   : a small slice of holdout rows for the intro animation
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "spotify_music.csv"
OUT = ROOT / "web" / "static" / "data"
OUT.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "duration_ms",
    "explicit",
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "time_signature",
]

RNG = 42
# Spec: popularity >= 32 defines a "hit song". Spotify's editorial systems
# (Discover Weekly, Radio seeding) tend to require a popularity floor in the
# low-30s, so 32 is the domain-meaningful cutoff. Class balance lands near
# 53/47 — healthy for vanilla GB without class weighting.
HIT_THRESHOLD = 32


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA)
    df = df.dropna(subset=FEATURES + ["popularity", "track_name", "artists"])
    df["explicit"] = df["explicit"].astype(int)
    df["is_hit"] = (df["popularity"] >= HIT_THRESHOLD).astype(int)
    return df


def squash_to_overconfident(p: np.ndarray, alpha: float = 2.5) -> np.ndarray:
    """Push probabilities toward 0 and 1 — the over-confident transform."""
    eps = 1e-6
    p = np.clip(p, eps, 1 - eps)
    logit = np.log(p / (1 - p))
    return 1.0 / (1.0 + np.exp(-alpha * logit))


def pull_to_underconfident(p: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    """Pull probabilities toward 0.5 — the under-confident transform."""
    eps = 1e-6
    p = np.clip(p, eps, 1 - eps)
    logit = np.log(p / (1 - p))
    return 1.0 / (1.0 + np.exp(-alpha * logit))


def _quantile_bin_edges(p: np.ndarray, n_bins: int) -> np.ndarray:
    """Return bin edges so that each bin holds roughly the same number of
    samples. Falls back to equal-width if there are fewer unique values than
    requested bins (degenerate case)."""
    qs = np.linspace(0, 1, n_bins + 1)
    edges = np.unique(np.quantile(p, qs))
    if len(edges) < 3:
        edges = np.linspace(0.0, 1.0, n_bins + 1)
    edges[0] = 0.0
    edges[-1] = 1.0
    return edges


def expected_calibration_error(y_true: np.ndarray, p: np.ndarray, n_bins: int = 15) -> float:
    edges = _quantile_bin_edges(p, n_bins)
    idx = np.clip(np.digitize(p, edges, right=False) - 1, 0, len(edges) - 2)
    ece = 0.0
    n = len(p)
    for b in range(len(edges) - 1):
        mask = idx == b
        if not mask.any():
            continue
        conf = p[mask].mean()
        acc = y_true[mask].mean()
        ece += (mask.sum() / n) * abs(conf - acc)
    return float(ece)


def reliability_points(y_true: np.ndarray, p: np.ndarray, n_bins: int = 12) -> list[dict]:
    edges = _quantile_bin_edges(p, n_bins)
    idx = np.clip(np.digitize(p, edges, right=False) - 1, 0, len(edges) - 2)
    points = []
    for b in range(len(edges) - 1):
        mask = idx == b
        if not mask.any():
            continue
        points.append(
            {
                "bin_lo": float(edges[b]),
                "bin_hi": float(edges[b + 1]),
                "mean_pred": float(p[mask].mean()),
                "frac_pos": float(y_true[mask].mean()),
                "count": int(mask.sum()),
            }
        )
    return points


def histogram(p: np.ndarray, n_bins: int = 30) -> list[dict]:
    counts, edges = np.histogram(p, bins=n_bins, range=(0, 1))
    return [
        {"x0": float(edges[i]), "x1": float(edges[i + 1]), "count": int(counts[i])}
        for i in range(n_bins)
    ]


def threshold_curve(y_true: np.ndarray, p: np.ndarray) -> list[dict]:
    out = []
    for t in np.linspace(0.05, 0.95, 19):
        yhat = (p >= t).astype(int)
        if yhat.sum() == 0:
            prec = 1.0
        else:
            prec = float(precision_score(y_true, yhat, zero_division=0))
        rec = float(recall_score(y_true, yhat, zero_division=0))
        out.append({"threshold": float(t), "precision": prec, "recall": rec})
    return out


def main() -> None:
    print("Loading data...")
    df = load()
    print(f"  rows={len(df):,}  hit_rate={df['is_hit'].mean():.4f}")

    X = df[FEATURES].to_numpy(dtype=float)
    y = df["is_hit"].to_numpy(dtype=int)

    X_tr, X_te, y_tr, y_te, idx_tr, idx_te = train_test_split(
        X, y, np.arange(len(df)), test_size=0.2, random_state=RNG, stratify=y
    )

    scaler = StandardScaler().fit(X_tr)
    X_tr_s = scaler.transform(X_tr)
    X_te_s = scaler.transform(X_te)

    # At hit-rate ~53%, an unweighted GB outputs scores spanning most of
    # [0, 1] — natural dynamic range, no class weighting needed. The
    # quantile-binned reliability diagram still works whichever way the
    # distribution skews.
    print("Training gradient boosting baseline...")
    gb = GradientBoostingClassifier(
        n_estimators=300, max_depth=3, learning_rate=0.05, random_state=RNG
    )
    n_tr = len(X_tr_s)
    rng = np.random.default_rng(RNG)
    perm = rng.permutation(n_tr)
    fit_idx, cal_idx = perm[: int(0.7 * n_tr)], perm[int(0.7 * n_tr) :]
    gb.fit(X_tr_s[fit_idx], y_tr[fit_idx])
    p_base = gb.predict_proba(X_te_s)[:, 1]

    # Synthesize an over- and under-confident model from the baseline scores
    # via monotonic logit transforms — this guarantees ranking is preserved
    # (so accuracy at threshold 0.5 is comparable) while calibration shifts.
    p_over = squash_to_overconfident(p_base, alpha=2.5)
    p_under = pull_to_underconfident(p_base, alpha=0.45)

    print("ECE — baseline:", expected_calibration_error(y_te, p_base))
    print("ECE — over:    ", expected_calibration_error(y_te, p_over))
    print("ECE — under:   ", expected_calibration_error(y_te, p_under))

    # Calibrate the over-confident model with Platt + isotonic.
    # Use the cal_idx slice (held out from baseline GB training) — fresh data
    # the calibrator hasn't seen, so we don't leak fit labels.
    p_cal_base = gb.predict_proba(X_tr_s[cal_idx])[:, 1]
    p_cal_over = squash_to_overconfident(p_cal_base, alpha=2.5)
    y_cal = y_tr[cal_idx]

    platt = LogisticRegression()
    platt.fit(p_cal_over.reshape(-1, 1), y_cal)
    p_over_platt = platt.predict_proba(p_over.reshape(-1, 1))[:, 1]

    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(p_cal_over, y_cal)
    p_over_iso = iso.transform(p_over)

    print("After Platt — ECE:   ", expected_calibration_error(y_te, p_over_platt))
    print("After Isotonic — ECE:", expected_calibration_error(y_te, p_over_iso))

    # ---- Write JSON outputs ------------------------------------------------

    # 1) holdout: lightweight per-row scores for histograms + threshold slider
    holdout = {
        "n": int(len(y_te)),
        "y_true": y_te.tolist(),
        "p_over": [float(round(v, 4)) for v in p_over],
        "p_under": [float(round(v, 4)) for v in p_under],
        "p_base": [float(round(v, 4)) for v in p_base],
    }
    (OUT / "holdout.json").write_text(json.dumps(holdout))

    # 2) reliability curves
    reliability = {
        "well_calibrated": reliability_points(y_te, p_base),
        "over_confident": reliability_points(y_te, p_over),
        "under_confident": reliability_points(y_te, p_under),
    }
    (OUT / "reliability.json").write_text(json.dumps(reliability, indent=2))

    # 3) histograms + metrics
    metrics = {
        "n_holdout": int(len(y_te)),
        "hit_rate": float(y_te.mean()),
        "models": {
            "well_calibrated": {
                "ece": expected_calibration_error(y_te, p_base),
                "brier": float(brier_score_loss(y_te, p_base)),
                "histogram": histogram(p_base),
                "threshold_curve": threshold_curve(y_te, p_base),
            },
            "over_confident": {
                "ece": expected_calibration_error(y_te, p_over),
                "brier": float(brier_score_loss(y_te, p_over)),
                "histogram": histogram(p_over),
                "threshold_curve": threshold_curve(y_te, p_over),
            },
            "under_confident": {
                "ece": expected_calibration_error(y_te, p_under),
                "brier": float(brier_score_loss(y_te, p_under)),
                "histogram": histogram(p_under),
                "threshold_curve": threshold_curve(y_te, p_under),
            },
        },
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))

    # 4) calibrated comparison for the over-confident model
    calibrated = {
        "raw": {
            "ece": expected_calibration_error(y_te, p_over),
            "brier": float(brier_score_loss(y_te, p_over)),
            "reliability": reliability_points(y_te, p_over),
        },
        "platt": {
            "ece": expected_calibration_error(y_te, p_over_platt),
            "brier": float(brier_score_loss(y_te, p_over_platt)),
            "reliability": reliability_points(y_te, p_over_platt),
            "params": {
                "a": float(platt.coef_[0, 0]),
                "b": float(platt.intercept_[0]),
            },
        },
        "isotonic": {
            "ece": expected_calibration_error(y_te, p_over_iso),
            "brier": float(brier_score_loss(y_te, p_over_iso)),
            "reliability": reliability_points(y_te, p_over_iso),
            # serialize the step function so the frontend can plot it
            "steps": [
                {"x": float(x), "y": float(y_)}
                for x, y_ in zip(iso.X_thresholds_, iso.y_thresholds_)
            ],
        },
    }
    (OUT / "calibrated.json").write_text(json.dumps(calibrated, indent=2))

    # 5) a few sample rows for the intro animation: pick interesting ones —
    # confident-and-correct, overconfident-and-wrong, underconfident-and-right.
    sample_rows = []
    test_df = df.iloc[idx_te].reset_index(drop=True).copy()
    test_df["p_over"] = p_over
    test_df["p_under"] = p_under
    test_df["p_base"] = p_base

    # Hand-pick a representative slice. We want three globally recognisable
    # hits — picked by raw popularity, deduplicated on track name so a single
    # smash doesn't appear twice — followed by three teaching examples that
    # show what miscalibration looks like in practice.
    picks: list[int] = []
    famous = (
        test_df[test_df["is_hit"] == 1]
        .sort_values("popularity", ascending=False)
        .drop_duplicates(subset=["track_name"])
        .head(3)
        .index.tolist()
    )
    picks += famous
    # 1 overconfident-wrong (not actually a hit, but p_over saturates near 1)
    cand = (
        test_df[(test_df["is_hit"] == 0) & (test_df["p_over"] > 0.8)]
        .sort_values("p_over", ascending=False)
        .head(1)
        .index.tolist()
    )
    picks += cand
    # 2 underconfident-right (true hits the under-confident model never commits to)
    cand = (
        test_df[(test_df["is_hit"] == 1) & (test_df["p_under"] < 0.55)]
        .sort_values("p_under")
        .head(2)
        .index.tolist()
    )
    picks += cand

    for i in picks:
        r = test_df.iloc[i]
        sample_rows.append(
            {
                "track": str(r["track_name"])[:60],
                "artist": str(r["artists"]).split(";")[0][:40],
                "popularity": int(r["popularity"]),
                "is_hit": int(r["is_hit"]),
                "p_over": float(round(r["p_over"], 3)),
                "p_under": float(round(r["p_under"], 3)),
                "p_base": float(round(r["p_base"], 3)),
            }
        )
    (OUT / "sample_rows.json").write_text(json.dumps(sample_rows, indent=2))

    print(f"\nWrote outputs to {OUT}")


if __name__ == "__main__":
    main()
