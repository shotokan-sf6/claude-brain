# Changelog

Notable changes to the SHOTOKAN Claude plugin, newest first. Every push adds its changes here.

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
