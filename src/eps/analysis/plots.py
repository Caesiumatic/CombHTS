"""Matplotlib / scikit-learn figures for ``eps analyze`` (lazy, degrade-gracefully).

All third-party plotting/ML imports happen INSIDE the functions so that a missing
``matplotlib`` or ``scikit-learn`` only skips the affected figure (with a note) rather than
crashing the whole command. Figures touching diagnostic soft axes are labeled as such.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DIAGNOSTIC_LABEL = "SCREENING-GRADE -- uncalibrated band gap + proton-referenced dimerization; diagnostic"

# Real descriptor axes (safe to plot without a diagnostic soft-axis warning).
DISTRIBUTION_COLUMNS = ("window_margin_V", "solubility_score", "anion_stability_margin_V")
DISTRIBUTION_FALLBACK = {"solubility_score": "solvation_dG_kcal_mol"}
CHEMSPACE_FEATURES = (
    "solvent_eps_r",
    "window_margin_V",
    "solubility_score",
    "anion_stability_margin_V",
)


def matplotlib_available() -> bool:
    """Return True if matplotlib can be imported (Agg backend)."""

    return _pyplot() is not None


def _pyplot():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except Exception:  # noqa: BLE001 - any import/backend failure means "no plotting".
        return None


def plot_distributions(frame: pd.DataFrame, out: Path, notes: list[str]) -> list[Path]:
    """Histograms of the REAL descriptor axes only."""

    plt = _pyplot()
    if plt is None:
        return []
    paths: list[Path] = []
    for column in DISTRIBUTION_COLUMNS:
        source = column if column in frame.columns else DISTRIBUTION_FALLBACK.get(column)
        if source is None or source not in frame.columns:
            notes.append(f"distribution SKIPPED for {column}: column not in harvest.")
            continue
        values = pd.to_numeric(frame[source], errors="coerce").dropna()
        if values.empty:
            notes.append(f"distribution SKIPPED for {source}: no finite values.")
            continue
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(values, bins=min(30, max(5, len(values) // 2)), color="#3b6ea5", edgecolor="white")
        ax.set_xlabel(source)
        ax.set_ylabel("triad count")
        ax.set_title(f"Distribution of {source} (real descriptor axis)")
        fig.tight_layout()
        path = out / f"dist_{source}.png"
        fig.savefig(path, dpi=120)
        plt.close(fig)
        paths.append(path)
    return paths


def plot_pareto(frame: pd.DataFrame, out: Path, notes: list[str]) -> Path | None:
    """Scatter window_margin_V vs solubility_score, marked by the existing pareto_front flag."""

    plt = _pyplot()
    if plt is None:
        return None
    required = ("window_margin_V", "solubility_score", "pareto_front")
    if not all(column in frame.columns for column in required):
        notes.append(
            "Pareto PNG SKIPPED: harvest lacks window_margin_V/solubility_score/pareto_front."
        )
        return None

    x = pd.to_numeric(frame["window_margin_V"], errors="coerce")
    y = pd.to_numeric(frame["solubility_score"], errors="coerce")
    on_front = frame["pareto_front"].astype(bool)

    sizes = None
    if "band_gap_deviation_eV" in frame.columns:
        deviation = pd.to_numeric(frame["band_gap_deviation_eV"], errors="coerce").fillna(0.0)
        sizes = 20.0 + 80.0 * _minmax(-deviation)

    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.scatter(
        x[~on_front], y[~on_front],
        s=None if sizes is None else sizes[~on_front],
        c="#bbbbbb", alpha=0.6, label="dominated",
    )
    ax.scatter(
        x[on_front], y[on_front],
        s=None if sizes is None else sizes[on_front],
        c="#d1495b", edgecolor="black", label="pareto_front",
    )
    ax.set_xlabel("window_margin_V")
    ax.set_ylabel("solubility_score")
    ax.set_title(f"Pareto front (point size ~ -band_gap_deviation_eV)\n{DIAGNOSTIC_LABEL}")
    ax.legend(title=DIAGNOSTIC_LABEL, fontsize=8)
    fig.tight_layout()
    path = out / "pareto_window_vs_solubility.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def chemical_space_map(frame: pd.DataFrame, out: Path, notes: list[str]) -> list[Path]:
    """Per-triad Morgan-fingerprint + descriptor map, embedded to 2D and colored two ways."""

    plt = _pyplot()
    if plt is None:
        return []
    sklearn_mods = _import_sklearn()
    if sklearn_mods is None:
        notes.append(
            "Chemical-space map SKIPPED: scikit-learn is not importable "
            "(summary, distributions, Pareto, and shortlist were still produced)."
        )
        return []
    pca_cls, tsne_cls = sklearn_mods

    if "monomer_canonical_smiles" not in frame.columns:
        notes.append("Chemical-space map SKIPPED: no monomer_canonical_smiles column.")
        return []

    n = int(len(frame))
    if n < 2:
        notes.append("Chemical-space map SKIPPED: fewer than 2 triads.")
        return []

    fingerprints = _morgan_matrix(frame["monomer_canonical_smiles"].astype(str).tolist(), notes)
    if fingerprints is None:
        return []

    try:
        fp_components = min(50, n, fingerprints.shape[1])
        fp_reduced = pca_cls(n_components=fp_components, random_state=0).fit_transform(fingerprints)
        features = _normalized_features(frame)
        combined = np.hstack([fp_reduced, features]) if features.size else fp_reduced

        if n < 10:
            embedding = pca_cls(n_components=2, random_state=0).fit_transform(combined)
            method = "PCA(2) [small-n fallback]"
        else:
            perplexity = min(30, max(5, n // 4))
            embedding = tsne_cls(
                n_components=2,
                perplexity=perplexity,
                init="pca",
                learning_rate="auto",
                random_state=0,
            ).fit_transform(combined)
            method = f"t-SNE (perplexity={perplexity})"
    except Exception as exc:  # noqa: BLE001 - degenerate inputs must not crash the command.
        notes.append(f"Chemical-space map SKIPPED: embedding failed ({type(exc).__name__}: {exc}).")
        return []

    paths: list[Path] = []
    for color_column, filename in (
        ("monomer_class", "chemspace_by_monomer_class.png"),
        ("passes_all_tier1_filters", "chemspace_by_pass_filters.png"),
    ):
        if color_column not in frame.columns:
            notes.append(f"Chemical-space coloring SKIPPED: no {color_column} column.")
            continue
        path = _scatter_embedding(plt, embedding, frame[color_column], color_column, method, out, filename)
        paths.append(path)
    return paths


def _scatter_embedding(plt, embedding, color_series, color_column, method, out: Path, filename: str) -> Path:
    fig, ax = plt.subplots(figsize=(7, 5.5))
    categories = pd.Series(color_series).astype(str)
    cmap = plt.get_cmap("tab10")
    for index, (label, mask) in enumerate(categories.groupby(categories).groups.items()):
        idx = categories.index.get_indexer(mask)
        ax.scatter(
            embedding[idx, 0], embedding[idx, 1],
            label=str(label), color=cmap(index % 10), alpha=0.75, s=28, edgecolor="white",
        )
    ax.set_xlabel("dim 1")
    ax.set_ylabel("dim 2")
    ax.set_title(f"Chemical-space map ({method})\ncolored by {color_column}")
    ax.legend(title=color_column, fontsize=7, loc="best")
    fig.tight_layout()
    path = out / filename
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def _import_sklearn():
    try:
        from sklearn.decomposition import PCA
        from sklearn.manifold import TSNE

        return PCA, TSNE
    except Exception:  # noqa: BLE001 - missing sklearn means "skip the map".
        return None


def _morgan_matrix(smiles_list: list[str], notes: list[str]) -> np.ndarray | None:
    try:
        from rdkit import Chem
        from rdkit.Chem import rdFingerprintGenerator
    except Exception:  # noqa: BLE001
        notes.append("Chemical-space map SKIPPED: RDKit fingerprint generator unavailable.")
        return None

    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=1024)
    cache: dict[str, np.ndarray] = {}
    rows: list[np.ndarray] = []
    for smiles in smiles_list:
        if smiles not in cache:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                cache[smiles] = np.zeros(1024, dtype=float)
            else:
                fp = generator.GetFingerprint(mol)
                cache[smiles] = np.array(fp, dtype=float)
        rows.append(cache[smiles])
    return np.vstack(rows)


def _normalized_features(frame: pd.DataFrame) -> np.ndarray:
    columns = [c for c in CHEMSPACE_FEATURES if c in frame.columns]
    if not columns:
        return np.empty((len(frame), 0))
    normalized = [
        _minmax(pd.to_numeric(frame[column], errors="coerce").fillna(0.0)).to_numpy()
        for column in columns
    ]
    return np.column_stack(normalized)


def _minmax(series: pd.Series) -> pd.Series:
    low = float(series.min())
    high = float(series.max())
    if high == low:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - low) / (high - low)
