# Release revision validation

Verified on 3 October 2026 using local MySQL 8.0.43 and Python 3.14.

## Automated suite

```powershell
$env:AVDB_RUN_MYSQL_TESTS = '1'
python -m unittest discover -s database/tests
```

Result: **59 tests passed**, including two opt-in MySQL tests. Without the flag,
57 tests run and the two MySQL tests are intentionally skipped.

| Check | Result |
| --- | --- |
| Candidate import retains the formal/current A | Passed |
| Import a new classification B for the exact same input | Passed |
| Activate B with matching expected old keys | Passed |
| Incorrect old keys stop instead of overwriting another selection | Passed |
| Re-publication reuses analysis without model calls | Passed |
| Inject failure after pointer/status changes but before operation evidence | Changes rolled back; previous B stayed visible |
| Retry the prepared frozen draft | Passed without rebuilding its snapshot |
| Reactivate an intact previous frozen release | Passed; old row hashes unchanged |
| Earlier-week reversion while a newer week is current | Historical selection changed; current Dashboard unchanged |
| Weekly query after several same-week releases | One formal release only; no duplicate catalogue/job rows |
| Migration with matching current release, sole history and ambiguous history | Current/sole selected; ambiguous/unfrozen left for review |
| Foreign key rejects a selected release from another collection/analysis | Passed |
| Local JSON failure report and append-only log | Written during the injected failure |
| Real backup files | Generated and gzip-validated in isolated tests |
| Importer session audit timezone | UTC |

## Real-data restored-copy check

A full backup of the existing weekly implementation test database was restored
into a new, uniquely named local database. Migration 007 and current views were
applied only to that copy. Then the CLI performed `create-release`, activation,
reversion and reactivation using the existing 25 September collection/analysis.

- New snapshot: **2,902 AV jobs**, **47,752 job-skill rows**, **115 clusters**;
  **2,901 jobs** have extracted skills.
- All 2,902 current detail rows reported the new detail contract available.
- The formal 25 September catalogue contained one row, and its AV job view
  contained 2,902 rows, not both old and new revisions.
- Analysis-run count did not increase: no duplicate analysis import or AI rerun.
- The old frozen snapshot digest was unchanged after switching away and back.
- The original source database's table counts, current release key and snapshot
  digest were unchanged.
- CLI success reports, local JSONL logs, backup files and transactional
  `release_operations` evidence were produced in the isolated workflow.

The existing one skill-less job and missing approved cluster names remain
quality warnings. These tests verify data movement, boundaries and version
safety; they do not certify the classifier's semantic correctness or approve
cluster names.
