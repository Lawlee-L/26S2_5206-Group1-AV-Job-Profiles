# MVP Source Register

## Evidence boundary

The team investigations in [Issues #3, #4, #7, #8 and #9](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles/issues)
identified candidate career systems. The endpoints below were rechecked against
the public official ATS sources on 20 August 2026 before implementation.

“Implemented” means the public endpoint returned structured job data and a
concrete company spider exists. It does not mean the client has approved every
company for final scope, or that collection is permanently permitted.

## Ashby

| Spider | Company | Public board token | Investigation |
|---|---|---|---|
| `fortytwodot` | 42dot | `42dot` | Issue #3 |
| `aurora` | Aurora | `aurora-operations-inc` | Issue #3 |
| `applied_intuition` | Applied Intuition | `applied` | Issue #3 |

Endpoint pattern:
`https://api.ashbyhq.com/posting-api/job-board/<token>`

The live tokens for Aurora and Applied Intuition differ from the short company
names, so they are recorded explicitly rather than guessed at runtime.

## Greenhouse

| Spider | Company | Public board token | Investigation |
|---|---|---|---|
| `avride` | Avride | `avride` | Issue #4 |
| `bot_auto` | Bot Auto | `botauto` | Issue #4 |
| `gatik` | Gatik | `gatikaiinc` | Issue #4 |
| `may_mobility` | May Mobility | `maymobility` | Issue #4 |
| `kodiak` | Kodiak | `kodiak` | Issue #9 |
| `latitude` | Latitude (Ford) | `latitude` | Issue #9 |
| `motional` | Motional | `motional` | Issue #7 |
| `vay` | Vay | `vay` | Issue #8 |
| `xpeng_us` | XPeng US | `xpengmotors` | Issue #8 |

Endpoint pattern:
`https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true`

XPeng covers the US Greenhouse board only, not the separate Feishu/global source.

## Lever

| Spider | Company | Public board token / host | Investigation |
|---|---|---|---|
| `mobileye` | Mobileye | `mobileye` / `api.eu.lever.co` | Issue #7 |
| `weride_us` | WeRide US | `weride` / `api.lever.co` | Issue #8 |
| `woven_by_toyota` | Woven by Toyota | `woven-by-toyota` / `api.lever.co` | Issue #8 |
| `zoox` | Zoox | `zoox` / `api.lever.co` | Issue #8 |

Endpoint pattern:
`https://<host>/v0/postings/<token>?mode=json`

WeRide covers the US Lever board only, not the separate Moka/China source.

## Deferred sources

The MVP intentionally defers sources needing browser automation, encoded client
payloads, custom endpoints with higher maintenance cost, or unresolved AV
relevance filtering. Examples include Waymo/WAF, Inceptio/Moka, GM/Cloudflare,
Huawei relevance filtering, NVIDIA/Workday and several dynamic company pages.

Deferral is a risk-control decision, not a claim that these sources are
impossible. Add each later as its own spider under a method-specific directory
after scope, collection permission, fields and quality checks are agreed.
