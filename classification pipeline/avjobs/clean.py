"""Load and dedupe postings.

v2 sends each posting's full description to the model, so v1's boilerplate
stripping, requirements slicing and English-only filter are gone from here.
They remain in Experiment 2.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as cfg


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------
_WS_RE = re.compile(r"[ \t ]+")
_MULTINL_RE = re.compile(r"\n{3,}")
_BULLET_RE = re.compile(r"^\s*[•●▪‣⁃*·]\s*", re.M)

_UNICODE_FIXES = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-", " ": " ",
    "…": "...", "﻿": "",
}


def normalize_text(text: str) -> str:
    """Unicode-normalise, flatten smart punctuation, tidy whitespace."""
    text = unicodedata.normalize("NFKC", text)
    for bad, good in _UNICODE_FIXES.items():
        text = text.replace(bad, good)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _BULLET_RE.sub("- ", text)
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MULTINL_RE.sub("\n\n", text)
    return text.strip()


# --------------------------------------------------------------------------
# Loading + dedupe
# --------------------------------------------------------------------------
def _content_hash(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text.lower()).strip()
    return hashlib.sha1(collapsed.encode("utf-8")).hexdigest()


def load_postings(path) -> pd.DataFrame:
    """Load the ATS-export JSON: a list of {metadata: {...}, data: {...}} records."""
    rows = []
    for rec in json.loads(Path(path).read_text(encoding="utf-8")):
        meta, data = rec.get("metadata") or {}, rec.get("data") or {}
        rows.append({
            # The durable join key (ATS id). row_index below is only stable
            # within one export of the file.
            "source_key": meta.get("source_key") or "",
            "company": (meta.get("company") or "Unknown").strip(),
            "name": (data.get("advertised_job_title") or "").strip(),
            "description": data.get("job_description") or "",
            "date_posted": data.get("date_posted") or "",
            "platform": meta.get("platform") or "",
            "region": meta.get("region") or "",
            "location": data.get("location") or "",
            "job_url": data.get("job_url") or "",
        })
    df = pd.DataFrame(rows)
    df["row_index"] = np.arange(len(df))
    df["description_norm"] = df["description"].map(normalize_text)
    return df


def dedupe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Drop exact and near-exact duplicate descriptions.

    Exact duplicates are caught by a normalised content hash. Near-duplicates
    (the same role reposted with a tweaked line or a new location) are caught
    with TF-IDF cosine similarity, compared only within a company -- two
    different employers using the same ATS template are not the same job.

    Returns (kept, dropped). `dropped` records which row each duplicate mapped to.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    df = df.copy()
    df["content_hash"] = df["description_norm"].map(_content_hash)

    # -- exact duplicates: keep the first occurrence --------------------------
    first_of_hash = df.drop_duplicates(subset="content_hash", keep="first")
    hash_to_keeper = dict(zip(first_of_hash["content_hash"], first_of_hash["row_index"]))
    key_to_keeper = dict(zip(first_of_hash["content_hash"], first_of_hash["source_key"]))
    is_exact_dup = df.duplicated(subset="content_hash", keep="first")

    drop_records: list[dict] = []
    for _, row in df[is_exact_dup].iterrows():
        drop_records.append({
            "source_key": row["source_key"],
            "row_index": row["row_index"],
            "company": row["company"],
            "name": row["name"],
            "duplicate_of_row_index": hash_to_keeper[row["content_hash"]],
            "duplicate_of_source_key": key_to_keeper[row["content_hash"]],
            "duplicate_type": "exact",
            "similarity": 1.0,
        })

    survivors = df[~is_exact_dup].copy()

    # -- near duplicates, within each company ---------------------------------
    near_dup_rows: set[int] = set()
    for _, group in survivors.groupby("company", sort=False):
        if len(group) < 2:
            continue
        texts = (group["name"] + "\n" + group["description_norm"]).tolist()
        try:
            vec = TfidfVectorizer(ngram_range=(1, 3), min_df=1, sublinear_tf=True)
            matrix = vec.fit_transform(texts)
        except ValueError:
            continue  # degenerate group (e.g. all-empty text)
        sim = cosine_similarity(matrix)
        np.fill_diagonal(sim, 0.0)
        idx = group["row_index"].to_numpy()

        # Keep the earliest row in each near-duplicate pair.
        for i in range(len(group)):
            if idx[i] in near_dup_rows:
                continue
            for j in range(i + 1, len(group)):
                if idx[j] in near_dup_rows:
                    continue
                if sim[i, j] >= cfg.NEAR_DUP_THRESHOLD:
                    near_dup_rows.add(int(idx[j]))
                    row = group.iloc[j]
                    drop_records.append({
                        "source_key": row["source_key"],
                        "row_index": int(idx[j]),
                        "company": row["company"],
                        "name": row["name"],
                        "duplicate_of_row_index": int(idx[i]),
                        "duplicate_of_source_key": group.iloc[i]["source_key"],
                        "duplicate_type": "near",
                        "similarity": round(float(sim[i, j]), 4),
                    })

    kept = survivors[~survivors["row_index"].isin(near_dup_rows)].copy()
    dropped = pd.DataFrame(drop_records, columns=[
        "source_key", "row_index", "company", "name",
        "duplicate_of_row_index", "duplicate_of_source_key",
        "duplicate_type", "similarity",
    ])
    return kept.reset_index(drop=True), dropped
