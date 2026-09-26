"""UMAP -> HDBSCAN clustering, plus human-readable cluster summaries.

UMAP is not decoration: on the raw 384-d vectors HDBSCAN degenerates on this
data (one giant blob or >90% noise), because density estimation is unreliable
in high dimensions. Reducing to 5 dimensions first gives usable clusters.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import config as cfg


def reduce_dimensions(embeddings: np.ndarray) -> np.ndarray:
    """UMAP to a few dimensions, preserving the local neighbourhoods HDBSCAN needs."""
    import umap

    print(f"  [cluster] UMAP -> {cfg.UMAP_COMPONENTS}d "
          f"(n_neighbors={cfg.UMAP_N_NEIGHBORS}, metric=cosine)")
    reducer = umap.UMAP(
        n_components=cfg.UMAP_COMPONENTS,
        n_neighbors=cfg.UMAP_N_NEIGHBORS,
        min_dist=cfg.UMAP_MIN_DIST,
        metric="cosine",
        random_state=cfg.RANDOM_SEED,   # reproducible runs for the write-up
    )
    return reducer.fit_transform(embeddings)


def distance_matrix(reduced: np.ndarray) -> np.ndarray:
    """Euclidean distances in UMAP space.

    Cosine belongs on the raw sentence-transformer vectors, where direction
    carries the meaning. UMAP output has no meaningful origin, so cosine there
    would compare angles about an arbitrary point.
    """
    from sklearn.metrics import pairwise_distances
    return pairwise_distances(reduced, metric="euclidean").astype(np.float64)


def run_hdbscan(dist: np.ndarray, min_cluster_size: int, min_samples: int) -> np.ndarray:
    """Cluster from a precomputed distance matrix. Returns labels (-1 == noise)."""
    from sklearn.cluster import HDBSCAN

    return HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="precomputed",
        # copy=True matters: with copy=False HDBSCAN overwrites the distance
        # matrix in place, which would corrupt every later run in the sweep.
        copy=True,
        cluster_selection_method=cfg.CLUSTER_SELECTION_METHOD,
        cluster_selection_epsilon=cfg.CLUSTER_SELECTION_EPSILON,
    ).fit_predict(dist)


def sweep_min_cluster_size(reduced: np.ndarray) -> pd.DataFrame:
    """Grid over min_cluster_size x min_samples so parameters are chosen from evidence.

    min_samples is swept too because it controls how conservative HDBSCAN is:
    left at its default (== min_cluster_size) it marks most of this dataset as
    noise, while lower values recover far more structure.
    """
    dist = distance_matrix(reduced)
    rows = []
    for mcs in cfg.SWEEP_MIN_CLUSTER_SIZES:
        for ms in cfg.SWEEP_MIN_SAMPLES:
            labels = run_hdbscan(dist, mcs, ms)
            clustered = labels[labels >= 0]
            sizes = np.bincount(clustered) if clustered.size else np.array([])
            sizes = sizes[sizes > 0]
            rows.append({
                "min_cluster_size": mcs,
                "min_samples": ms,
                "n_clusters": int(len(sizes)),
                "n_noise": int((labels == -1).sum()),
                "pct_noise": round(100.0 * (labels == -1).sum() / len(labels), 1),
                "largest_cluster": int(sizes.max()) if sizes.size else 0,
                "median_cluster": int(np.median(sizes)) if sizes.size else 0,
                "smallest_cluster": int(sizes.min()) if sizes.size else 0,
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Cluster summaries
# --------------------------------------------------------------------------
# Body-derived TF-IDF terms describe the work; titles describe how it is
# marketed. Weight accordingly.
TERM_WEIGHT = 1.0
TITLE_WEIGHT = 0.25


def _seed_pattern(terms):
    """Word-boundary matcher for a seed list.

    Plain substring matching silently misfires: "ros" matches inside "cross
    functional", scoring a programme-management cluster as robotics. Boundaries
    are required, but \\b does not work after a symbol, so terms ending in a
    non-word character (c++) get a lookahead instead.
    """
    parts = []
    for t in sorted(terms, key=len, reverse=True):
        esc = re.escape(t)
        prefix = r"\b" if t[:1].isalnum() else ""
        suffix = r"\b" if t[-1:].isalnum() else r"(?![\w+#])"
        parts.append(prefix + esc + suffix)
    return re.compile("|".join(parts), re.I)


_TECH_RE = _seed_pattern(cfg.TECHNICAL_SEED_TERMS)
_CORP_RE = _seed_pattern(cfg.CORPORATE_SEED_TERMS)


def _lean_score(text: str) -> tuple[int, int]:
    """Count DISTINCT seed terms present, so one repeated word cannot dominate."""
    tech = len({m.group(0).lower() for m in _TECH_RE.finditer(text)})
    corp = len({m.group(0).lower() for m in _CORP_RE.finditer(text)})
    return tech, corp


def _technical_lean(terms: list[str], titles: list[str]) -> tuple[float, str]:
    """Cheap heuristic so clusters can be triaged before anyone hand-labels them.

    Not a relevance classifier -- just a hint about which clusters to read first,
    and enough to check the trap cases automatically.

    TF-IDF terms are weighted far above titles. Titles alone are actively
    misleading: a pure technical-program-management cluster is full of words
    like "Lidar", "Autonomy" and "Vehicle OS" in its *titles* while its body
    vocabulary is entirely programme management, and weighting the two equally
    labelled that cluster "technical".
    """
    term_tech, term_corp = _lean_score(" ".join(terms).lower())
    title_tech, title_corp = _lean_score(" ".join(titles).lower())

    tech = TERM_WEIGHT * term_tech + TITLE_WEIGHT * title_tech
    corp = TERM_WEIGHT * term_corp + TITLE_WEIGHT * title_corp
    total = tech + corp
    score = 0.5 if total == 0 else tech / total
    if score >= 0.65:
        lean = "technical"
    elif score <= 0.35:
        lean = "corporate"
    else:
        lean = "mixed"
    return round(score, 3), lean


def summarize_clusters(df: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    """Top TF-IDF terms of `cluster_text` + example titles per cluster, for hand-labelling."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    df = df.copy()
    df["cluster_id"] = labels

    vec = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.5,          # terms in >half the corpus carry no discriminative signal
        stop_words="english",
        sublinear_tf=True,
        max_features=40000,
    )
    matrix = vec.fit_transform(df["cluster_text"])
    vocab = np.array(vec.get_feature_names_out())

    rows = []
    for cid in sorted(set(labels)):
        mask = (labels == cid)
        sub = df[mask]
        # Mean TF-IDF within the cluster surfaces the cluster's own vocabulary.
        mean_tfidf = np.asarray(matrix[mask].mean(axis=0)).ravel()
        top_idx = np.argsort(mean_tfidf)[::-1][:cfg.TOP_TFIDF_TERMS]
        terms = [vocab[i] for i in top_idx if mean_tfidf[i] > 0]

        titles = sub["name"].tolist()
        example_titles = pd.Series(titles).drop_duplicates().head(
            cfg.EXAMPLE_TITLES_PER_CLUSTER).tolist()
        companies = sub["company"].value_counts()

        score, lean = _technical_lean(terms, titles)
        rows.append({
            "cluster_id": int(cid),
            "size": int(mask.sum()),
            "is_noise": cid == -1,
            "technical_score": score,
            "lean": "n/a (noise)" if cid == -1 else lean,
            "n_companies": int(companies.size),
            "top_companies": "; ".join(f"{c} ({n})" for c, n in companies.head(3).items()),
            "top_terms": ", ".join(terms),
            "example_titles": " | ".join(example_titles),
            # Blank columns for the human pass.
            "job_family": "",
            "specialisation": "",
            "notes": "",
        })

    summary = pd.DataFrame(rows)
    return summary.sort_values(
        ["is_noise", "size"], ascending=[True, False]
    ).reset_index(drop=True)


def write_labelling_worksheet(summary: pd.DataFrame, path) -> None:
    """Markdown worksheet -- one block per cluster, ready to fill in."""
    lines = [
        "# Cluster labelling worksheet",
        "",
        "Fill in **Job family** and **Specialisation** for each cluster, then copy your",
        "labels into `cluster_summary.csv` (columns `job_family`, `specialisation`).",
        "",
        "`lean` is a keyword heuristic to help you triage, not a classification —",
        "always confirm against the terms and titles.",
        "",
    ]
    for _, r in summary.iterrows():
        if r["is_noise"]:
            header = f"## Cluster -1 — NOISE / needs manual review ({r['size']} postings)"
        else:
            header = f"## Cluster {r['cluster_id']} — {r['size']} postings — lean: {r['lean']}"
        lines += [
            header,
            "",
            f"- **Companies:** {r['top_companies']} (across {r['n_companies']})",
            f"- **Top terms:** {r['top_terms']}",
            f"- **Example titles:** {r['example_titles']}",
            "",
            "- **Job family:** ______________________",
            "- **Specialisation:** ______________________",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
