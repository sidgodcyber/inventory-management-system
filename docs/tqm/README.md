# TQM analysis templates

These files are filled in during Reviews 3 and 4.

| File | Tool | Main data source |
|---|---|---|
| [fmea.md](fmea.md) | Failure Mode and Effects Analysis | Design review + `ERROR` entries |
| [sipoc.md](sipoc.md) | SIPOC process map | Stock workflow (`docs/architecture.md`) |
| [ctq_tree.md](ctq_tree.md) | Critical-to-Quality tree | `docs/SRS.md` section 5 |
| [defect_checksheet.md](defect_checksheet.md) | Defect checksheet | Activity Log → filter **Action = ERROR** → Export CSV |
| [pareto.md](pareto.md) | Pareto analysis | Checksheet totals |
| [fishbone.md](fishbone.md) | Cause-and-effect (Ishikawa) | Top Pareto defect |
| [pdca_log.md](pdca_log.md) | Plan-Do-Check-Act log | Quality report + tests before/after each change |

**Exporting the defect data:** open the Activity Log, set *Action = ERROR* and a date range, press **Apply**, then **Export CSV**. The `Details` column holds `context` (screen and action), `type` (exception class) and `message`; group by `context` or `type` to fill the checksheet.
