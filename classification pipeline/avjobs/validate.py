"""Spot-check the pipeline against the 14 hand-picked reference postings.

These 14 rows are far too few to train or tune on. They are used only as a
known-answer check: where did each land, and do the two trap cases behave?

`test_idx` in the reference files is the row position in the source CSV, so it
maps onto `row_index`. We fall back to (company, title) matching if that ever
stops holding.
"""

from __future__ import annotations

import json
import re
import unicodedata

import pandas as pd

from . import config as cfg

# The two cases called out as the real test of the cluster-first approach.
#
# The pass criteria are deliberately asymmetric, matching how the cases were
# posed. Trap A asserts a positive ("lands in a technical cluster"); Trap B
# asserts only a negative ("does NOT land in a technical cluster") -- a
# program-management or mixed-leadership cluster is a correct home for it, so
# requiring the label "corporate" would fail the pipeline for being right.
TRAP_CASES = {
    27: {
        "label": "TRAP A — misleading title, technical body",
        "title_contains": "Frontend Engineer",
        "expectation": "should land in / near a TECHNICAL cluster",
        "passes": lambda lean: lean == "technical",
    },
    330: {
        "label": "TRAP B — technical-sounding title, non-technical body",
        "title_contains": "Technical Program Manager",
        "expectation": "should NOT land in a technical cluster",
        "passes": lambda lean: lean != "technical",
    },
}


def _norm(s: str) -> str:
    """Casefold and strip punctuation/dash variants for tolerant comparison."""
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    s = s.replace("–", "-").replace("—", "-").replace("’", "'")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _same_title(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    # Exports truncate or re-punctuate titles, so accept containment either way.
    return na == nb or na.startswith(nb) or nb.startswith(na)


def _same_company(a: str, b: str) -> bool:
    """Tolerate employer renames between exports ('AV Ride' vs 'Avride')."""
    na, nb = _norm(a).replace(" ", ""), _norm(b).replace(" ", "")
    if not na or not nb:
        return False
    return na == nb or na.startswith(nb) or nb.startswith(na)


def load_reference() -> pd.DataFrame | None:
    if not (cfg.TEST_SET_JSON.exists() and cfg.REFERENCE_JSON.exists()):
        return None
    tests = json.loads(cfg.TEST_SET_JSON.read_text(encoding="utf-8"))
    answers = json.loads(cfg.REFERENCE_JSON.read_text(encoding="utf-8"))

    by_idx = {a["test_idx"]: a for a in answers}
    rows = []
    for t in tests:
        a = by_idx.get(t["test_idx"], {})
        rows.append({
            "test_idx": t["test_idx"],
            "ref_company": t.get("company", ""),
            "ref_title": t.get("name", ""),
            "ref_av_relevant": a.get("av_relevant"),
            "ref_seniority": a.get("seniority"),
            "ref_experience_min": a.get("experience_min"),
            "ref_experience_max": a.get("experience_max"),
            "ref_tools": ", ".join(a.get("raw_skills_tools", []) or []),
            "ref_domain": ", ".join(a.get("raw_skills_domain", []) or []),
            "ref_qualifications": ", ".join(a.get("raw_skills_qualifications", []) or []),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Model check (--reference-only): score a model's records against Sonnet 5
# --------------------------------------------------------------------------
def reference_postings() -> pd.DataFrame:
    """The 14 reference postings as model input: the exact text Sonnet 5 answered."""
    tests = json.loads(cfg.TEST_SET_JSON.read_text(encoding="utf-8"))
    return pd.DataFrame({
        "source_key": [f"reference:{t['test_idx']}" for t in tests],
        "test_idx": [t["test_idx"] for t in tests],
        "company": [t["company"] for t in tests],
        "name": [t["name"] for t in tests],
        "description": [t["description"] for t in tests],
    })


def _skill(s: str) -> str:
    # Lighter than _norm: keeps + # . so "C++", "C#" and "Node.js" stay distinct from "C".
    return " ".join(re.sub(r"[^\w+#.]+", " ", str(s).lower()).split())


def _skill_found(ref: str, names: set[str]) -> bool:
    """Loose match: equal, or one name contains the other as whole words."""
    return any(ref == n or f" {ref} " in f" {n} " or f" {n} " in f" {ref} " for n in names)


def score_against_reference(postings: pd.DataFrame, results: list[dict]) -> pd.DataFrame:
    """One row per reference posting: where the model agrees with Sonnet 5, and what it cost."""
    from .llm import SKILL_CATEGORIES

    answers = {a["test_idx"]: a for a in json.loads(cfg.REFERENCE_JSON.read_text(encoding="utf-8"))}
    rows = []
    for (_, p), res in zip(postings.iterrows(), results):
        rec, ref = res["record"], answers[p["test_idx"]]
        row = {"test_idx": p["test_idx"], "title": p["name"], "error": res["error"],
               "output_tokens": res["output_tokens"], "reasoning_tokens": res.get("reasoning_tokens", 0),
               "cost_usd": res["cost_usd"]}
        if rec:
            skills = [s for cat in SKILL_CATEGORIES for s in rec["skills"][cat]]
            names = {_skill(s["name"]) for s in skills}
            ref_names = {_skill(x) for cat in SKILL_CATEGORIES for x in ref[f"raw_skills_{cat}"] or []}
            description = _norm(p["description"])
            row |= {
                "av_relevant_agrees": rec["av_relevant"] == ref["av_relevant"],
                "seniority_agrees": rec["seniority"] == ref["seniority"],
                "experience_min_agrees": rec["experience_min"] == ref["experience_min"],
                "experience_max_agrees": rec["experience_max"] == ref["experience_max"],
                "n_skills": len(skills),
                "ref_skills_found": sum(_skill_found(r, names) for r in ref_names) / max(len(ref_names), 1),
                "evidence_verbatim": sum(_norm(s["evidence"]) in description for s in skills) / max(len(skills), 1),
                "model_seniority": rec["seniority"], "ref_seniority": ref["seniority"],
                "model_experience": f"{rec['experience_min']}-{rec['experience_max']}",
                "ref_experience": f"{ref['experience_min']}-{ref['experience_max']}",
                "model_av_relevant": rec["av_relevant"], "ref_av_relevant": ref["av_relevant"],
                "relevance_confidence_agrees": rec["relevance_confidence"] == ref["relevance_confidence"],
                "model_confidence": rec["relevance_confidence"], "ref_confidence": ref["relevance_confidence"],
            }
        rows.append(row)
    return pd.DataFrame(rows)


def build_report(
    postings: pd.DataFrame,
    summary: pd.DataFrame,
    dropped: pd.DataFrame,
) -> tuple[pd.DataFrame | None, str]:
    """Join reference labels onto pipeline output and render a markdown report."""
    ref = load_reference()
    if ref is None:
        return None, "_Reference files not found — spot-check skipped._\n"

    lean_by_cluster = dict(zip(summary["cluster_id"], summary["lean"]))
    terms_by_cluster = dict(zip(summary["cluster_id"], summary["top_terms"]))
    examples_by_cluster = dict(zip(summary["cluster_id"], summary["example_titles"]))

    by_row = postings.set_index("row_index")
    dropped_map = (
        dict(zip(dropped["row_index"], dropped["duplicate_of_row_index"]))
        if not dropped.empty else {}
    )

    records = []
    for _, r in ref.iterrows():
        idx = r["test_idx"]
        note = ""
        row = None

        # test_idx is a row position in the ORIGINAL CSV. Against any other
        # export it points at an unrelated posting, so the title must agree
        # before we trust it -- otherwise we would silently score the wrong row.
        if idx in by_row.index and _same_title(by_row.loc[idx]["name"], r["ref_title"]):
            row = by_row.loc[idx]
        elif (idx in dropped_map and dropped_map[idx] in by_row.index
              and _same_title(by_row.loc[dropped_map[idx]]["name"], r["ref_title"])):
            row = by_row.loc[dropped_map[idx]]
            note = f"deduped into row {dropped_map[idx]}"
        else:
            cand = postings[
                postings["name"].map(lambda n: _same_title(n, r["ref_title"]))
                & postings["company"].map(
                    lambda c: _same_company(c, r["ref_company"])
                )
            ]
            if cand.empty:  # title alone, in case the employer is renamed
                cand = postings[postings["name"].map(
                    lambda n: _same_title(n, r["ref_title"]))]
                note = "matched by title only"
            else:
                note = "matched by company+title"
            if cand.empty:
                records.append({**r.to_dict(), "found": False,
                                "note": "not found in this dataset"})
                continue
            row = cand.iloc[0]

        cid = int(row["cluster_id"])
        records.append({
            **r.to_dict(),
            "found": True,
            "note": note,
            "pipeline_title": row["name"],
            "cluster_id": cid,
            "cluster_lean": lean_by_cluster.get(cid, "?"),
            "cluster_terms": terms_by_cluster.get(cid, ""),
            "cluster_examples": examples_by_cluster.get(cid, ""),
            "pipeline_seniority": row["seniority"],
            "pipeline_seniority_source": row["seniority_source"],
            "pipeline_experience_min": row["experience_min"],
            "pipeline_experience_max": row["experience_max"],
            "pipeline_tools": row["skills_tools"],
            "pipeline_domain": row["skills_domain"],
            "pipeline_qualifications": row["skills_qualifications"],
        })

    table = pd.DataFrame(records)

    # ---- agreement stats -------------------------------------------------
    found = table[table["found"]]
    sen_match = (found["pipeline_seniority"] == found["ref_seniority"]).sum()

    def _num_match(col_p, col_r):
        both = found[found[col_r].notna() & found[col_p].notna()]
        if both.empty:
            return 0, 0
        return int((both[col_p].astype("Float64") == both[col_r].astype("Float64")).sum()), len(both)

    exp_min_hit, exp_min_n = _num_match("pipeline_experience_min", "ref_experience_min")
    exp_max_hit, exp_max_n = _num_match("pipeline_experience_max", "ref_experience_max")

    lines = [
        "# Known-answer spot-check (14 reference postings)",
        "",
        "These 14 postings are a sanity check, not a training or tuning set.",
        "",
        "## Agreement with the reference labels",
        "",
        f"- Postings located in pipeline output: **{len(found)}/{len(table)}**",
        f"- Seniority exact match: **{sen_match}/{len(found)}**",
        f"- experience_min exact match: **{exp_min_hit}/{exp_min_n}** (where both are non-null)",
        f"- experience_max exact match: **{exp_max_hit}/{exp_max_n}** (where both are non-null)",
        "",
        "## Trap cases",
        "",
    ]

    for idx, meta in TRAP_CASES.items():
        sub = table[table["test_idx"] == idx]
        if sub.empty:
            lines += [f"### {meta['label']}", "", f"- Row {idx} not in the reference set.", ""]
            continue
        row = sub.iloc[0]
        if not row["found"]:
            lines += [f"### {meta['label']}", "", f"- Row {idx} not found in output ({row['note']}).", ""]
            continue
        actual_lean = row["cluster_lean"]
        verdict = "PASS" if meta["passes"](actual_lean) else "REVIEW"
        lines += [
            f"### {meta['label']}",
            "",
            f"- **Posting:** {row['ref_company']} — {row['ref_title']}",
            f"- **Reference `av_relevant`:** {row['ref_av_relevant']}",
            f"- **Expectation:** {meta['expectation']}",
            f"- **Landed in:** cluster `{row['cluster_id']}` (lean: **{actual_lean}**)",
            f"- **Cluster terms:** {str(row['cluster_terms'])[:240]}",
            f"- **Neighbours:** {str(row.get('cluster_examples', ''))[:200]}",
            f"- **Verdict:** {verdict}",
            "",
        ]

    lines += ["## Per-posting comparison", "",
              "| # | Title | Cluster (lean) | Seniority (ref) | Exp min (ref) | Exp max (ref) |",
              "|---|-------|----------------|-----------------|---------------|---------------|"]
    for _, r in table.iterrows():
        if not r["found"]:
            lines.append(f"| {r['test_idx']} | {r['ref_title'][:40]} | not found | — | — | — |")
            continue
        sen_flag = "OK" if r["pipeline_seniority"] == r["ref_seniority"] else "diff"
        lines.append(
            f"| {r['test_idx']} | {str(r['ref_title'])[:40]} "
            f"| {r['cluster_id']} ({r['cluster_lean']}) "
            f"| {r['pipeline_seniority']} ({r['ref_seniority']}) {sen_flag} "
            f"| {r['pipeline_experience_min']} ({r['ref_experience_min']}) "
            f"| {r['pipeline_experience_max']} ({r['ref_experience_max']}) |"
        )
    lines.append("")
    return table, "\n".join(lines)
