# Location integration validation — 7 October 2026

## Scope and result

**Passed:** current importer + MySQL views + existing Flask country/work-mode
queries. This does not claim that the frontend dropdown values or new
city/region API parameters have been implemented. Their tasks are in
[LOCATION_INTEGRATION](LOCATION_INTEGRATION.md).

Implementation builds on SJ's parser from
[PR #64](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles/pull/64),
with additional ambiguity/negative-mode guards and importer/release integration.
No existing demo DB, original input file, classification result or running
service connection was changed. No AI/model call was made.

## Automated tests

- `python -m unittest discover -s database/tests`: **160 tests passed** with
  `AVDB_RUN_MYSQL_TESTS=1` and local development credentials in environment
  variables. This includes three opt-in MySQL test methods. Without the flag,
  three are skipped; that is not the command used for final validation.
- Backend, from its directory: `python -m pytest tests -q`: **16 passed**.
- `git diff --check`: passed (only Windows line-ending notices).

MySQL tests create new random target names and retain them for inspection.
They cover fresh collection writes, old null-location snapshot enhancement,
same-analysis release reuse, unchanged old rows/hashes, safe reactivation,
historical selection, rollback of a later unclassified collection, and an
injected activation failure which must restore the previous selection.

Parser tests cover Germany/Delaware, India/Indiana, Israel/Illinois and
Netherlands/Newfoundland collisions; mixed-country and partially unresolved
lists; city/region hierarchy; district versus city; remote-country prefixes;
explicit/negative/conflicting work modes; missing/long values; and frozen QA
which must not reinterpret legacy history using new rules.

## Real dataset and population counts

Input: Li's `2026-09-25/jobs_history_translated.json` and the matching Sunjol
`output_full/` artifacts, obtained from the prepared local demo input copies.
Source SHA-256:

```text
9ef073c17f0266f40e7e00f0c12a8af5170cf213853e2416d191167991ecfd91
```

Classification artifact commit:
`e4f1b77cc56f048c06196e7a27865d98084c2e2a`.
All 5,139 keys reconcile to 4,518 analysed postings and 621 duplicate links.
The AV release has 2,902 postings, of which 2,412 are active.

| Population | Rows | Country known | City populated | Region populated | Work mode explicit | Missing raw location | Nonempty but country unresolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| All source postings | 5,139 | 4,856 | 4,168 | 3,056 | 202 | 120 | 163 |
| All non-duplicate AV postings | 2,902 | 2,672 | 2,096 | 1,344 | 175 | 90 | 140 |
| Active non-duplicate AV postings | 2,412 | 2,197 | 1,711 | 1,084 | 140 | 89 | 126 |

These are rule-coverage counts, **not verified geocoding accuracy**. For active
AV jobs, explicit modes are remote **118**, hybrid **13**, onsite **9**;
the remaining **2,272** are unknown, not implicitly onsite. Unknown countries
include ambiguous/multi-country locations, not just absent source values.

## Full real-data workflow

New validation DB: `av_location_validation_20261007_c169dbfe`.
Backup restore target: `av_location_validation_20261007_c169dbfe_restore`.
Both are test copies, not an instruction to point the team's demo at them.

Thirteen audited CLI operations exercised collection import, analysis plan /
import, simulated legacy null-location publication, same-analysis release
creation, QA, activation, reversion/reactivation, backup and new-DB restore.

Verified:

- Original source file checksum remains identical; all source records still
  match the classification input contract.
- Old frozen snapshot row hashes/root hash remain unchanged.
- The enhanced release reuses the same collection, analysis and cluster run.
- Switching back restores the old fields; switching forward reuses the intact
  frozen new snapshot rather than reinterpreting it.
- Current and weekly AV readers expose enriched fields; raw weekly readers
  expose the collection observation's own fields.
- Restore preserves frozen hashes, counts and QA after current views are
  rebound to the explicitly selected restore DB. Restored views do not read
  the original validation DB.
- Existing video demo DBs' current release keys/root hashes remain unchanged.
- A final read-only replay of current rules matches all **5,139** stored
  source rows and **2,902** AV snapshot rows: zero field mismatches.

## Existing backend against real MySQL

The unmodified Flask app was called with its test client against the validation
DB. Every response was HTTP 200, and pagination totals matched independent SQL:

| Query | Active AV jobs |
| --- | ---: |
| No filter | 2,412 |
| `country=US` | 1,126 |
| `country=DE` | 152 |
| `country=IN` | 4 |
| `remote_type=remote` | 118 |
| `remote_type=hybrid` | 13 |
| `remote_type=onsite` | 9 |
| `country=US&remote_type=remote` | 102 |

Job responses retain `city`, `stateRegion`, `countryCode`, `remoteType` and raw
`location`. A US job-detail request also succeeds with its location preserved.
`country=United States` returns zero: the frontend must send the country **code**.
City/region filters are still a backend hand-off, not a passing feature claim.

### Administrative QA performance limitation

Full published-release QA succeeded but was slow in this local run: about
144 seconds on the validation DB and 567 seconds on the restored DB. It runs
the existing global consistency/view checks, not just location parsing. The
eight real backend filter checks together completed in about 7 seconds; they
are a different workload. Do not treat absent intermediate CLI output as an
automatic import failure, and do not start a second writer while an operation
is running. Optimising full administrative QA remains separate follow-up work;
this validation does not claim that it is fast on every restored DB.

## Local evidence and remaining work

Full evidence is retained locally under
`E:\UWA\S4\CITS5206 Information Technology Capstone Project\location-validation-20261007\`:
`av_location_validation_20261007_c169dbfe.json`,
`backend_location_checks.json`, `final_rule_replay.json`, per-operation
`audit/reports/`, append-only `audit/logs/weekly_import.jsonl`, and `backups/`.
These machine-specific artifacts/backups are not repository deliverables.
Team members should rerun against their own explicitly selected test DB.

Remaining owner work: review unresolved formats/dictionary coverage, upgrade
the intended DB through the documented route, add backend city/region/options
support, correct frontend country values/work-arrangement labels, and verify
the UI. This change intentionally leaves unsupported employment type unknown.
