"""Helpers for clustering_decisions.ipynb: data from the database, embeddings, metrics.

Everything here is local: records are read from the pipeline's SQLite database
(no LLM calls), embeddings come from sentence-transformers models on this machine.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "output_full" / "av_job_profiles.sqlite"
EMB_CACHE = ROOT / ".cache" / "notebook_emb"
SKILL_CATEGORIES = ("tools", "domain", "qualifications")


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def load_postings(run_id: int = 1, db_path=DB_PATH) -> pd.DataFrame:
    """One row per analysed posting of one analysis run, with its record and its cluster in that run.

    Run 1 is the full run: its clusters are the original MiniLM / size-8 clustering. Later
    runs reuse the same records, so the records are identical whichever run is read.
    """
    con = sqlite3.connect(db_path)
    df = pd.read_sql("""
        SELECT a.job_analysis_id, j.source_key, j.advertised_job_title AS title,
               c.company_name AS company, a.av_relevant, a.relevance_confidence_label AS confidence,
               a.seniority_code AS seniority, a.raw_response_json,
               cl.cluster_number AS current_cluster
        FROM job_analyses a
        JOIN jobs j USING (job_id)
        JOIN job_sources s USING (source_id)
        JOIN companies c USING (company_id)
        LEFT JOIN job_cluster_assignments x ON x.job_analysis_id = a.job_analysis_id
        LEFT JOIN clusters cl ON cl.cluster_pk = x.cluster_pk
        WHERE a.analysis_run_id = ? AND a.analysis_status = 'success'
        ORDER BY a.job_analysis_id""", con, params=(run_id,))
    df["record"] = df.pop("raw_response_json").map(json.loads)
    df["av_relevant"] = df["av_relevant"].astype(bool)
    df.attrs["analysis_run_id"] = run_id
    return df


# --------------------------------------------------------------------------
# What text to embed
# --------------------------------------------------------------------------
def _skills(record: dict, categories) -> list[str]:
    return [s["name"] for cat in categories for s in record["skills"][cat]]


TEXT_VARIANTS = {
    # A: what the pipeline embeds today (run_pipeline_v2.cluster_text).
    "A_all_skills": lambda r: "\n".join([r["role_summary"], *r["responsibilities"],
                                         ", ".join(_skills(r, SKILL_CATEGORIES))]),
    # B: drop qualifications (degrees, licences): shared by most postings, say little about the work.
    "B_no_qualifications": lambda r: "\n".join([r["role_summary"], *r["responsibilities"],
                                                ", ".join(_skills(r, ("tools", "domain")))]),
    # C: the work only, no skill list.
    "C_work_only": lambda r: "\n".join([r["role_summary"], *r["responsibilities"]]),
    # D: the two-to-three sentence summary alone.
    "D_summary_only": lambda r: r["role_summary"],
}


def texts(df: pd.DataFrame, variant: str) -> list[str]:
    return [TEXT_VARIANTS[variant](r) for r in df["record"]]


# --------------------------------------------------------------------------
# Embeddings
# --------------------------------------------------------------------------
# Models compared, with the prefix each expects for symmetric (clustering) use.
MODELS = {
    "all-MiniLM-L6-v2": {"id": "sentence-transformers/all-MiniLM-L6-v2", "prefix": "", "max_tokens": 256},
    "all-mpnet-base-v2": {"id": "sentence-transformers/all-mpnet-base-v2", "prefix": "", "max_tokens": 384},
    "bge-base-en-v1.5": {"id": "BAAI/bge-base-en-v1.5", "prefix": "", "max_tokens": 512},
    "e5-base-v2": {"id": "intfloat/e5-base-v2", "prefix": "query: ", "max_tokens": 512},
    "gte-base": {"id": "thenlper/gte-base", "prefix": "", "max_tokens": 512},
    "bge-large-en-v1.5": {"id": "BAAI/bge-large-en-v1.5", "prefix": "", "max_tokens": 512},
}


def _chunks(text: str, size: int, overlap: int = 32, max_chunks: int = 12) -> list[str]:
    words = text.split()
    if len(words) <= size:
        return [" ".join(words)]
    step = max(1, size - overlap)
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)][:max_chunks]


def embed(text_list: list[str], model: str, chunk_words: int = 160, batch_size: int = 32) -> tuple[np.ndarray, float]:
    """L2-normalised vector per text (chunks mean-pooled, as in avjobs.embed). Cached on disk.

    Returns (vectors, seconds spent encoding; 0.0 when read from the cache).
    """
    spec = MODELS[model]
    h = hashlib.sha1(f"{spec['id']}|{spec['prefix']}|{chunk_words}".encode())
    for t in text_list:
        h.update(t.encode("utf-8", "ignore"))
    EMB_CACHE.mkdir(parents=True, exist_ok=True)
    path = EMB_CACHE / f"{model}_{h.hexdigest()[:12]}.npy"
    if path.exists():
        return np.load(path), 0.0

    from sentence_transformers import SentenceTransformer

    st = SentenceTransformer(spec["id"])
    st.max_seq_length = spec["max_tokens"]
    chunks, owners = [], []
    for i, t in enumerate(text_list):
        for c in _chunks(t, chunk_words):
            chunks.append(spec["prefix"] + c)
            owners.append(i)
    t0 = time.time()
    vecs = st.encode(chunks, batch_size=batch_size, convert_to_numpy=True,
                     normalize_embeddings=True, show_progress_bar=False)
    seconds = time.time() - t0
    out = np.zeros((len(text_list), vecs.shape[1]), dtype=np.float32)
    np.add.at(out, np.asarray(owners), vecs)
    out /= np.linalg.norm(out, axis=1, keepdims=True)
    np.save(path, out)
    return out, seconds


# --------------------------------------------------------------------------
# Title handling (titles are never embedded, so they are an independent check)
# --------------------------------------------------------------------------
_LEVEL_WORDS = {
    "senior", "sr", "staff", "principal", "lead", "junior", "jr", "intern", "internship", "interns",
    "working", "student", "trainee", "graduate", "entry", "level", "head", "chief", "associate",
    "i", "ii", "iii", "iv", "mandatory", "thesis", "bachelor", "master", "masters", "phd", "praktikum",
}
_STOP = {"and", "or", "of", "the", "for", "in", "to", "with", "a", "an", "at", "on", "as", "by",
         "m", "f", "w", "d", "x", "div", "all", "genders", "h", "field", "area", "position",
         "temporary", "contract", "time", "full", "part", "shift", "month", "months", "remote", "hybrid"}


def title_tokens(title: str) -> frozenset[str]:
    """Role words of a title: brackets, gender tags, level words and filler removed."""
    t = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", str(title).lower())
    words = re.findall(r"[a-z][a-z+#.]*", t)
    out = set()
    for w in words:
        w = w.strip(".")
        if w in _LEVEL_WORDS or w in _STOP or len(w) < 2:
            continue
        if w.endswith("ing") and w[:-3] in {"engineer"}:
            w = w[:-3]
        elif w.endswith("s") and len(w) > 3 and not w.endswith(("ss", "us", "is")):
            w = w[:-1]
        out.add(w)
    return frozenset(out)


def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


# --------------------------------------------------------------------------
# Embedding quality: nearest-neighbour checks against signals NOT in the embedded text
# --------------------------------------------------------------------------
def knn(vectors: np.ndarray, k: int = 10) -> np.ndarray:
    sim = vectors @ vectors.T
    np.fill_diagonal(sim, -np.inf)
    return np.argpartition(-sim, k, axis=1)[:, :k]


def title_agreement(vectors: np.ndarray, df: pd.DataFrame, k: int = 10) -> np.ndarray:
    """Per posting: mean title-word Jaccard with its k nearest neighbours from OTHER companies.

    NaN where all k neighbours are from the posting's own company.
    """
    nn = knn(vectors, k)
    toks = [title_tokens(t) for t in df["title"]]
    comp = df["company"].to_numpy()
    out = np.full(len(df), np.nan)
    for i in range(len(df)):
        other = [j for j in nn[i] if comp[j] != comp[i]]
        if other:
            out[i] = np.mean([jaccard(toks[i], toks[j]) for j in other])
    return out


def neighbour_metrics(vectors: np.ndarray, df: pd.DataFrame, k: int = 10) -> dict:
    """Rank-based, so comparable across models whose raw cosine scales differ.

    title_lift: title_agreement averaged over postings, divided by the title overlap of
        random other-company pairs. Titles are never embedded, so this independently
        tests that neighbours do the same kind of job; other-company only, so reposts
        cannot inflate it.
    employer_ratio: share of neighbours from the same company, divided by the share
        expected by chance. 1.0 = company does not matter; higher = postings group by
        employer (style, product line) rather than by role.
    av_agreement: share of neighbours in the same AV / non-AV group (sanity check).
    """
    nn = knn(vectors, k)
    comp = df["company"].to_numpy()
    av = df["av_relevant"].to_numpy()
    n = len(df)
    counts = pd.Series(comp).value_counts()
    expected = np.mean([(counts[c] - 1) / (n - 1) for c in comp])
    return {"title_lift": float(np.nanmean(title_agreement(vectors, df, k)) / random_title_baseline(df)),
            "employer_ratio": float((comp[nn] == comp[:, None]).mean() / expected),
            "av_agreement": float((av[nn] == av[:, None]).mean())}


def paired_difference(a: np.ndarray, b: np.ndarray, baseline: float, n_boot: int = 1000,
                      seed: int = 0) -> tuple[float, float, float]:
    """Mean of (a - b) over the same postings, in title_lift units, with a 95% bootstrap interval.

    Paired: both options are scored on identical postings, so only their difference is
    resampled. If the interval contains 0, the two options are not distinguishable.
    """
    d = (a - b) / baseline
    idx = np.random.default_rng(seed).integers(0, len(d), (n_boot, len(d)))
    boots = np.nanmean(d[idx], axis=1)
    return float(np.nanmean(d)), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


# --------------------------------------------------------------------------
# Clustering
# --------------------------------------------------------------------------
def umap_reduce(vectors: np.ndarray, n_neighbors: int, n_components: int, seed: int) -> np.ndarray:
    import umap
    return umap.UMAP(n_components=n_components, n_neighbors=n_neighbors, min_dist=0.0,
                     metric="cosine", random_state=seed).fit_transform(vectors)


def hdbscan_labels(dist: np.ndarray, min_cluster_size: int, min_samples: int,
                   method: str = "eom") -> np.ndarray:
    from sklearn.cluster import HDBSCAN
    return HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples, metric="precomputed",
                   copy=True, cluster_selection_method=method).fit_predict(dist)


def cluster_metrics(labels: np.ndarray, vectors: np.ndarray, df: pd.DataFrame, nn15: np.ndarray,
                    rand_title: float) -> dict:
    """Quality of one clustering of one group.

    title_coherence_lift: mean title-word Jaccard over OTHER-company pairs inside each
        cluster (size-weighted), divided by the group's random-pair baseline.
    self_contained: median over clusters of the share of members' 15 nearest neighbours
        (in the full embedding space) that are in the same cluster.
    single_company: share of clusters where one company holds >= 80% of members.
    """
    clustered = labels >= 0
    ids = np.unique(labels[clustered])
    sizes = np.array([(labels == c).sum() for c in ids]) if len(ids) else np.array([0])
    toks = [title_tokens(t) for t in df["title"]]
    comp = df["company"].to_numpy()
    coh, weights, own, single = [], [], [], 0
    for c in ids:
        members = np.where(labels == c)[0]
        pairs = [(a, b) for ai, a in enumerate(members) for b in members[ai + 1:] if comp[a] != comp[b]]
        if len(pairs) > 400:
            pairs = [pairs[i] for i in np.random.default_rng(0).choice(len(pairs), 400, replace=False)]
        if pairs:
            coh.append(np.mean([jaccard(toks[a], toks[b]) for a, b in pairs]))
            weights.append(len(members))
        own.append((labels[nn15[members]] == c).mean())
        single += pd.Series(comp[members]).value_counts(normalize=True).iloc[0] >= 0.8
    return {
        "n_clusters": int(len(ids)),
        "noise_pct": round(100 * float((~clustered).mean()), 1),
        "largest_pct": round(100 * float(sizes.max() / len(labels)), 1),
        "median_size": int(np.median(sizes)),
        "title_coherence_lift": round(float(np.average(coh, weights=weights) / rand_title), 2) if coh else 0.0,
        "self_contained": round(float(np.median(own)), 2) if own else 0.0,
        "single_company_pct": round(100 * single / max(len(ids), 1), 1),
    }


def random_title_baseline(df: pd.DataFrame, n_pairs: int = 20000, seed: int = 0) -> float:
    toks = [title_tokens(t) for t in df["title"]]
    comp = df["company"].to_numpy()
    rng = np.random.default_rng(seed)
    a, b = rng.integers(0, len(df), n_pairs), rng.integers(0, len(df), n_pairs)
    keep = comp[a] != comp[b]
    return float(np.mean([jaccard(toks[i], toks[j]) for i, j in zip(a[keep], b[keep])]))


def stability(labels_a: np.ndarray, labels_b: np.ndarray) -> float:
    """Adjusted Rand index over postings clustered (not noise) in both runs."""
    from sklearn.metrics import adjusted_rand_score
    both = (labels_a >= 0) & (labels_b >= 0)
    return float(adjusted_rand_score(labels_a[both], labels_b[both])) if both.sum() > 1 else 0.0


# --------------------------------------------------------------------------
# Tuning
# --------------------------------------------------------------------------
def tune_group(vectors: np.ndarray, df: pd.DataFrame, grid: dict, seeds=(42, 7, 123)) -> pd.DataFrame:
    """Every UMAP x HDBSCAN setting in `grid` on one group (cached on disk).

    Quality metrics are averaged over the UMAP seeds, so one lucky or unlucky layout
    cannot decide a setting's rank. `stability` is the mean adjusted Rand index between
    the first seed's clustering and each other seed's (postings clustered in both), and
    `seed_agreement` the same over all postings, noise included.
    """
    from sklearn.metrics import adjusted_rand_score
    from sklearn.metrics import pairwise_distances

    key = hashlib.sha1(b"seed-averaged-v2" + vectors.tobytes() + json.dumps(grid, sort_keys=True).encode()
                       + str(seeds).encode()).hexdigest()[:12]
    cache = EMB_CACHE / f"grid_{key}.csv"
    if cache.exists():
        return pd.read_csv(cache)
    nn15 = knn(vectors, 15)
    base = random_title_baseline(df)
    rows = []
    for n_nb in grid["n_neighbors"]:
        for n_comp in grid["n_components"]:
            dists = {s: pairwise_distances(umap_reduce(vectors, n_nb, n_comp, s)) for s in seeds}
            for mcs in grid["min_cluster_size"]:
                for ms in grid["min_samples"]:
                    labels = {s: hdbscan_labels(dists[s], mcs, ms) for s in seeds}
                    per_seed = pd.DataFrame([cluster_metrics(labels[s], vectors, df, nn15, base)
                                             for s in seeds])
                    m = per_seed.mean().round(2).to_dict()
                    m["n_clusters"] = int(round(m["n_clusters"]))
                    m["stability"] = round(float(np.mean(
                        [stability(labels[seeds[0]], labels[s]) for s in seeds[1:]])), 2)
                    m["seed_agreement"] = round(float(np.mean(
                        [adjusted_rand_score(labels[seeds[0]], labels[s]) for s in seeds[1:]])), 2)
                    rows.append({"n_neighbors": n_nb, "n_components": n_comp,
                                 "min_cluster_size": mcs, "min_samples": ms, **m})
    out = pd.DataFrame(rows)
    out.to_csv(cache, index=False)
    return out


RANK_COLUMNS = {"title_coherence_lift": False, "self_contained": False, "seed_agreement": False,
                "noise_pct": True}


def select(results: pd.DataFrame, max_noise: float, max_largest: float, min_agreement: float,
           n_range: tuple[int, int]) -> pd.DataFrame:
    """Apply the selection rule: filter to admissible settings, then rank.

    Admissible: noise <= max_noise %, largest cluster <= max_largest % of the group,
    seed_agreement >= min_agreement, cluster count within n_range. Ranked by the mean of
    four ranks (coherence, self-containment, seed agreement: higher is better; noise: lower).
    """
    ok = results[(results.noise_pct <= max_noise) & (results.largest_pct <= max_largest)
                 & (results.seed_agreement >= min_agreement)
                 & results.n_clusters.between(*n_range)].copy()
    ranks = [ok[c].rank(ascending=asc) for c, asc in RANK_COLUMNS.items()]
    ok["mean_rank"] = sum(ranks) / len(ranks)
    return ok.sort_values("mean_rank")


def cluster_with(vectors: np.ndarray, n_neighbors: int, n_components: int,
                 min_cluster_size: int, min_samples: int, seed: int = 42) -> np.ndarray:
    from sklearn.metrics import pairwise_distances
    reduced = umap_reduce(vectors, n_neighbors, n_components, seed)
    return hdbscan_labels(pairwise_distances(reduced), min_cluster_size, min_samples)
