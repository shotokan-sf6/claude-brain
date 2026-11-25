# Changelog

Notable changes to the SHOTOKAN Claude plugin, newest first. Every push adds its changes here.

## 2026-11-25 (0.2.4)
- Replay Tracker sheet retired: shared-core-review no longer refreshes a tracker sheet or dashboard after ingest, `shared-core-tracking.md` is removed, and the skills and README no longer mention the tracker. The history database (and the SHOTOKAN site, for .shog) is the long-term view. Bundled `tools/sf6db_export.py` docstring updated to match shotokan-sf6/tools.

## 2026-11-25 (0.2.3)
- New skill `batch-record-replays`: records replays by ID with the bundled `tools/batch/batch_record.py` (SF6 + batch_replays.lua + OBS), checks each `<ID>.mp4` / `<ID>.json` landed, reports recorded / skipped / failed without results so the blind prediction stays blind, and lists fixes for common failures (OBS not running, search dialogs, wrong screen).

## 2026-11-24 (0.2.2)
- Block punish windows: the bundled analyzer measures every blocked move the attacker is still recovering from by 5+ frames, with range and what the defender did, checked against wiki block advantage in the new `tools/frame_data/` (32 characters). Stored in sf6.db (`punish_windows`, set and game stats). quick-review-report reports block punishes; full-review-report checks missed punishes and keeps the `frame_data` aliases up to date.

## 2026-11-24 (0.2.1)
- Bundled tools: spectra scored against everyone except the configured player (`spectra_calibrate.py`), the 7-day personal baseline (`player_baseline.py`, run by ingest) and `character_baselines.py`. shared-core-player-spectra reference updated. sf6-character-notes: Marisa notes and baselines without the player.

## 2026-11-24 (0.2.0)
- Reviews run in tiers: `sf6-replay-analysis` loads `shared-core-review`, then `quick-review-report`, then (Full and Tournament) `full-review-report`, each with its own `references/` (files renamed `shared-core-*` and `full-review-*`).
- quick-review-report loads `sf6-character-notes` for character baselines; the guideline skills (and `sf6-coach-shog`) load in full-review-report.
- Bundled tools from shotokan-sf6/tools with the review-step scripts renamed: `shared_core_analyze.py`, `shared_core_blind_manifest.py`, `shared_core_db.py`, `quick_review_reads.py`, `full_review_decision_presses.py` (the old names are gone; update any scripts or notes that call them).

## 2026-11-24 (0.1.5)
- Bundled tools from shotokan-sf6/tools (evening): Luke's move names (Flash Knuckle L/M/H/OD, Avenger follow-ups, SA1 Vulcan Blast, SA2 Eraser, SA3 Pale Rider), the `relabel_moves.py` fix for labels that partly stay the same, new `relabel_resolve.py`, and `quick_dashboard_from_db.py --set` so Quick reviews get their reads and habits.
- sf6-replay-analysis: review games in the order played unless told otherwise; the Quick-review step uses `--write-reads --set SET_KEY`.

## 2026-11-24 (0.1.4)
- Bundled mods from shotokan-sf6/mods c757834: character names come only from `char_names.json`, which now lists every character. When updating, copy it into `reframework\data\sf6_moves\` with the scripts.

## 2026-11-24 (0.1.3)
- Bundled tools from shotokan-sf6/tools daf2319: M. Bison and Cammy move names, `relabel_moves.py` (replaces `ken_relabel.py`).

## 2026-11-24 (0.1.2)
- Bundled tools from shotokan-sf6/tools 28c333a.
- Bundled tools: Ken's move names (Jinrai follow-ups, Quick Dash moves, supers), and Full-review spectrum overrides now apply. The player-spectra reference names the internal keys an override needs.
- The quick-dashboard step is gone from sf6-replay-analysis; reviews end at the database (Quick reviews still run `quick_dashboard_from_db.py --write-reads` for their reads and habits).
- New reviews go in `<coaching folder>\reviews\<YYYY-MM>\<date>_<type>_<opponent>\`, one-off analyses in `work\`.
- sf6-replay-analysis and sf6-review-dashboard split into a short core plus `references/` files, read only when a step needs them. Analysis: about 7,900 words down to 3,200, with capture data, guideline checks, report checks, player spectra, recording from IDs, video processing and tracking moved out. Dashboard: about 6,900 down to 1,400, with datasets, lens and story, page layout, and the CSS (`page-css.html`) and script helpers (`helpers.js`) as real files copied straight into each page. Every line of the old skills is still in one of the files. Removed from Known gaps.

## 2026-11-24 (0.1.1)
- Bundled tools no longer default to `.shog`: they read the player from `shotokan.json` (or `SHOTOKAN_PLAYER` / `SHOTOKAN_CFN_ID`) and stop with a clear message when it's missing. `buckler_replays.py` takes the CFN ID from it too. Removed from Known gaps. (tools e96a044)

## 2026-11-24 (0.1.0)
- First version. Skills: shotokan-setup (new), sf6-replay-analysis, replay-review-prediction, sf6-review-dashboard, sf6-fgc-glossary, sf6-character-notes, sf6-drive-efficiency, sf6-coach-juzzy-sessions, sf6-coach-juzzy-tips, sf6-footsies-handbook-maj, and sf6-coach-shog as an example of personal rules.
- Skill copies made general: the player comes from shotokan.json (name, CFN ID, main character); personal paths and dashboard links removed; E.X. Dojo, Coosco and DoctaAfrikan checks skipped unless those skills are installed.
- Bundled: tools from shotokan-sf6/tools (894462f) and REFramework scripts and move data from shotokan-sf6/mods (64abfd7); scripts/sync_bundled.sh refreshes them.
- marketplace.json (with a description) so the plugin can be installed from this repo.
