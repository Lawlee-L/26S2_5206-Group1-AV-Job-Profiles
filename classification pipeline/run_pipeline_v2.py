#!/usr/bin/env python
"""v2 pipeline: LLM-normalised records -> embed -> UMAP -> HDBSCAN.

The model turns each raw posting (any language) into a structured English
record and judges whether the role is AV-relevant. AV-relevant and other
postings are then clustered separately, locally, on an embedding of the
record. No posting is dropped: each lands in one group or the other.

    python run_pipeline_v2.py --dry-run              # cost estimate, no API calls
    python run_pipeline_v2.py --limit 50             # paid sample run
    python run_pipeline_v2.py --sweep                # cluster-parameter grid, then exit
    python run_pipeline_v2.py --min-cluster-size 15  # full run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

# UMAP/numba and sentence-transformers emit a lot of non-actionable noise.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from avjobs import config as cfg
from avjobs import clean, cluster, embed, llm, store, validate
from avjobs.llm import SKILL_CATEGORIES

# The model's relevance verdict -> the output subfolder that group is written to.
GROUPS = {True: "av_relevant", False: "not_av_relevant"}

# Same names as v1's postings_enriched.csv wherever the field is the same.
POSTING_COLS = [
    "source_key", "row_index", "company", "name", "date_posted",
    "cluster_id", "cluster_lean", "av_relevant", "av_relevant_model", "relevance_confidence",
    "relevance_reason",
    "seniority", "seniority_source", "experience_min", "experience_max",
    "skills_tools", "skills_domain", "skills_qualifications",
    "language_of_posting", "role_summary",
    "platform", "region", "location", "job_url",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", default=str(cfg.INPUT_JSON))
    p.add_argument("--output-dir", default=str(cfg.OUTPUT_DIR))
    p.add_argument("--model", default=cfg.LLM_MODEL, help="OpenRouter model id")
    p.add_argument("--limit", type=int, help="random sample of N postings (after dedupe)")
    p.add_argument("--min-cluster-size", type=int, default=cfg.MIN_CLUSTER_SIZE)
    p.add_argument("--min-samples", type=int, default=cfg.MIN_SAMPLES)
    p.add_argument("--sweep", action="store_true",
                   help="sweep min_cluster_size x min_samples per group, print the grid, and exit")
    p.add_argument("--no-cache", action="store_true",
                   help="ignore cached LLM replies and embeddings (paid: re-calls the model)")
    p.add_argument("--dry-run", action="store_true", help="print the cost estimate and exit")
    p.add_argument("--db", action="store_true",
                   help="also write the run to <output-dir>/av_job_profiles.sqlite (the tables "
                        "and columns of schema.mysql.sql), reusing records already stored there")
    p.add_argument("--reference-only", action="store_true",
                   help="run the model on the 14 reference postings only, score it against "
                        "the Sonnet 5 answers, and exit (for choosing a model)")
    return p.parse_args()


def cluster_text(record: dict) -> str:
    """What gets embedded: the role, its duties and its skills -- no employer, no boilerplate."""
    skills = [s["name"] for cat in SKILL_CATEGORIES for s in record["skills"][cat]]
    return "\n".join([record["role_summary"], *record["responsibilities"], ", ".join(skills)])


def attach_records(df: pd.DataFrame, results: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add each record's fields as columns. Returns (postings with a record, failures)."""
    ok = [r["record"] is not None for r in results]
    failed = df[[not x for x in ok]][["source_key", "row_index", "company", "name"]].copy()
    failed["error"] = [r["error"] for r in results if r["record"] is None]

    df = df[ok].copy()
    records = [r["record"] for r in results if r["record"] is not None]
    df["record"] = records
    for k in ("prompt_tokens", "output_tokens", "cost_usd"):   # per posting, for the database
        df[k] = [r[k] for r in results if r["record"] is not None]
    df["role_summary"] = [r["role_summary"] for r in records]
    for cat in SKILL_CATEGORIES:
        df[f"skills_{cat}"] = ["; ".join(s["name"] for s in r["skills"][cat]) for r in records]
    df["seniority"] = [r["seniority"] for r in records]
    df["seniority_source"] = "model"
    # Int64 (nullable) so a missing value stays blank in the CSV, as in v1.
    df["experience_min"] = pd.array([r["experience_min"] for r in records], dtype="Int64")
    df["experience_max"] = pd.array([r["experience_max"] for r in records], dtype="Int64")
    df["language_of_posting"] = [r["language_of_posting"] for r in records]
    df["av_relevant_model"] = [r["av_relevant"] for r in records]
    df["relevance_reason"] = [r["relevance_reason"] for r in records]
    df["relevance_confidence"] = [r["relevance_confidence"] for r in records]
    # When the model is unsure, count the posting as AV-relevant: a little noise in the AV
    # group is better than missing its skills. The model's own verdict stays in av_relevant_model.
    df["av_relevant"] = df["av_relevant_model"] | (df["relevance_confidence"] == "Low")
    df["reused_from"] = [r.get("reused_from") for r in results if r["record"] is not None]
    df["cluster_text"] = [cluster_text(r) for r in records]
    return df.reset_index(drop=True), failed


def usage_totals(results: list[dict]) -> dict:
    """Tokens and billed cost of the calls made in this run (cache hits cost nothing)."""
    fresh = [r for r in results if not r["cached"]]
    return {"n_api_postings": len(fresh),
            "n_cached": len(results) - len(fresh),
            "prompt_tokens": sum(r["prompt_tokens"] for r in fresh),
            "output_tokens": sum(r["output_tokens"] for r in fresh),
            "cost_usd": round(sum(r["cost_usd"] for r in fresh), 6)}


def group_stats(labels: np.ndarray) -> dict:
    return {"n_postings": len(labels), "n_clusters": len(set(labels) - {-1}),
            "n_noise": int((labels == -1).sum())}


def cluster_group(part: pd.DataFrame, embeddings: np.ndarray, args,
                  first_id: int) -> tuple[np.ndarray, pd.DataFrame]:
    """UMAP + HDBSCAN + summary for one relevance group.

    Cluster ids start at first_id so they stay unique across both groups; noise stays -1.
    """
    reduced = cluster.reduce_dimensions(embeddings)
    labels = cluster.run_hdbscan(cluster.distance_matrix(reduced),
                                 args.min_cluster_size, args.min_samples)
    labels = np.where(labels >= 0, labels + first_id, -1)
    stats = group_stats(labels)
    print(f"  {stats['n_clusters']} clusters, {stats['n_noise']} noise "
          f"({100 * stats['n_noise'] / len(labels):.1f}%)")
    return labels, cluster.summarize_clusters(part, labels)


def write_group_outputs(group_dir: Path, part: pd.DataFrame, summary: pd.DataFrame) -> None:
    group_dir.mkdir(parents=True, exist_ok=True)
    cols = [c for c in POSTING_COLS if c in part.columns]
    clustered, noise = part[part["cluster_id"] >= 0], part[part["cluster_id"] == -1]
    clustered[cols].to_csv(group_dir / "postings_enriched.csv", index=False)
    # The JSON also carries the full record, including each skill's evidence quote.
    clustered[cols + ["record"]].to_json(group_dir / "postings_enriched.json",
                                         orient="records", indent=2, force_ascii=False)
    noise[cols].to_csv(group_dir / "needs_review.csv", index=False)
    summary.to_csv(group_dir / "cluster_summary.csv", index=False)
    cluster.write_labelling_worksheet(summary, group_dir / "cluster_labelling_worksheet.md")


def reference_check(args) -> int:
    """--reference-only: the model on the 14 reference postings, scored against Sonnet 5."""
    df = validate.reference_postings()
    if args.dry_run:
        print(json.dumps(llm.estimate_cost(df, args.model, use_cache=not args.no_cache), indent=2))
        return 0
    t0 = time.time()
    results = llm.normalise_postings(df, args.model, use_cache=not args.no_cache)
    seconds = time.time() - t0
    table = validate.score_against_reference(df, results)
    ok = table[table["error"].isna()]
    if ok.empty:
        print(table[["test_idx", "error"]].to_string(index=False))
        return 1

    usage = usage_totals(results)
    n_api = max(usage["n_api_postings"], 1)
    agree = ["av_relevant_agrees", "relevance_confidence_agrees", "seniority_agrees",
             "experience_min_agrees", "experience_max_agrees"]
    summary = {
        "model": args.model, "records": f"{len(ok)}/{len(table)}",
        **{c: f"{int(ok[c].sum())}/{len(ok)}" for c in agree},
        "ref_skills_found": round(ok["ref_skills_found"].mean(), 2),
        "evidence_verbatim": round(ok["evidence_verbatim"].mean(), 2),
        "skills_per_posting": round(ok["n_skills"].mean(), 1),
        "output_tokens_per_posting": round(usage["output_tokens"] / n_api),
        "reasoning_tokens_per_posting": round(
            sum(r["reasoning_tokens"] for r in results if not r["cached"]) / n_api),
        "cost_usd": usage["cost_usd"],
        "seconds_per_posting": round(seconds / n_api, 1),
    }
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = args.model.replace("/", "_").replace(":", "_")
    table.to_csv(out_dir / f"reference_check_{slug}.csv", index=False)
    (out_dir / f"reference_check_{slug}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    args = parse_args()
    # OPENROUTER_API_KEY comes from .env (kept out of the code and never printed).
    load_dotenv(cfg.PROJECT_ROOT / ".env")
    if args.reference_only:
        return reference_check(args)
    t0 = time.time()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print("\n[1/5] Loading and deduplicating")
    df = clean.load_postings(args.input)
    n_input = len(df)
    df, dropped = clean.dedupe(df)
    print(f"  {n_input} postings, {len(dropped)} duplicates removed -> {len(df)}")
    if args.limit:
        df = df.sample(n=min(args.limit, len(df)), random_state=cfg.RANDOM_SEED)
        df = df.reset_index(drop=True)
        print(f"  --limit: random sample of {len(df)}")

    if args.dry_run:
        est = llm.estimate_cost(df, args.model, use_cache=not args.no_cache)
        print(json.dumps(est, indent=2))
        return 0

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = None
    reused = {}
    if args.db:
        conn = store.connect(out_dir / "av_job_profiles.sqlite")
        store.load_jobs(conn, args.input)   # temporary, until the team's job import exists
        if not args.no_cache:
            reused = store.reusable_records(conn, df, args.model)

    print("\n[2/5] LLM normalisation")
    if args.db:
        print(f"  {len(reused)} reused from the database")
    fresh = iter(llm.normalise_postings(df[~df["source_key"].isin(reused)], args.model,
                                        use_cache=not args.no_cache))
    results = [reused.get(key) or next(fresh) for key in df["source_key"]]
    usage = usage_totals(results)
    df, failed = attach_records(df, results)
    print(f"  {len(df)} records, {len(failed)} failures; this run billed "
          f"${usage['cost_usd']:.4f} for {usage['n_api_postings']} postings")

    print("\n[3/5] Embedding role_summary + responsibilities + skills")
    # Titles are not embedded: some are not English, and MiniLM is English-only.
    embeddings = embed.embed_postings(df["cluster_text"], use_cache=not args.no_cache)

    print(f"\n[4/5] Clustering each relevance group separately (HDBSCAN, "
          f"min_cluster_size={args.min_cluster_size}, min_samples={args.min_samples})")
    df["cluster_id"] = -1
    summaries, next_id = {}, 0
    for relevant, name in GROUPS.items():
        mask = (df["av_relevant"] == relevant).to_numpy()
        print(f"  {name}: {mask.sum()} postings")
        if args.sweep:
            table = cluster.sweep_min_cluster_size(cluster.reduce_dimensions(embeddings[mask]))
            print(table.to_string(index=False))
            (out_dir / name).mkdir(exist_ok=True)
            table.to_csv(out_dir / name / "cluster_sweep.csv", index=False)
            continue
        labels, summaries[name] = cluster_group(df[mask], embeddings[mask], args, next_id)
        df.loc[mask, "cluster_id"] = labels
        next_id = max(next_id, labels.max() + 1)
    if args.sweep:
        return 0

    # Ids are unique across groups, so one lookup serves both (noise is "n/a" in each).
    summary = pd.concat(summaries.values(), ignore_index=True)
    df["cluster_lean"] = df["cluster_id"].map(dict(zip(summary["cluster_id"], summary["lean"])))

    print("\n[5/5] Writing outputs")
    for relevant, name in GROUPS.items():
        write_group_outputs(out_dir / name, df[df["av_relevant"] == relevant], summaries[name])
    # Every posting in one file (both groups, clustered and noise), keyed by the
    # source file's metadata.source_key unchanged -- the file to import into MySQL.
    df[POSTING_COLS + ["record"]].to_json(out_dir / "postings_all.json", orient="records",
                                          indent=2, force_ascii=False)
    dropped.to_csv(out_dir / "duplicates_removed.csv", index=False)
    failed.to_csv(out_dir / "llm_failures.csv", index=False)
    # Relevance calls the model was unsure of: the ones a person should check first.
    df[df["relevance_confidence"] == "Low"][POSTING_COLS].to_csv(
        out_dir / "relevance_review.csv", index=False)
    table, report = validate.build_report(df, summary, dropped)
    (out_dir / "validation_report.md").write_text(report, encoding="utf-8")
    if table is not None:
        table.to_csv(out_dir / "validation_spotcheck.csv", index=False)
    meta = {
        "input": args.input, "n_input_rows": n_input, "n_after_dedupe": n_input - len(dropped),
        "n_duplicates_removed": len(dropped), "limit": args.limit,
        "n_records": len(df), "n_llm_failures": len(failed),
        "model": args.model, "prompt_version": llm.PROMPT_ID,
        "temperature": cfg.LLM_TEMPERATURE, **usage,
        "embedding_model": cfg.EMBED_MODEL, "embedded_text": "role_summary+responsibilities+skills",
        "min_cluster_size": args.min_cluster_size, "min_samples": args.min_samples,
        "groups": {name: group_stats(df.loc[df["av_relevant"] == relevant, "cluster_id"].to_numpy())
                   for relevant, name in GROUPS.items()},
        "languages": df["language_of_posting"].value_counts().to_dict(),
        "started_at": started_at, "runtime_seconds": round(time.time() - t0, 1),
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  wrote {out_dir}/")
    if conn:
        run_key = store.save_run(conn, df, failed, dropped, summaries, meta)
        print(f"  wrote {out_dir / 'av_job_profiles.sqlite'} (analysis run {run_key})")
        for table, n in store.row_counts(conn).items():
            print(f"    {table}: {n}")
        conn.close()
    print(f"\nDone in {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
