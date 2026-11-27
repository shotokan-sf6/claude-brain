# Changelog

Notable changes to the SHOTOKAN Claude plugin, newest first. Every push adds its changes here.

## 0.2.11 (2026-11-27): skills synced
- sf6-character-notes: A.K.I. fireballs (light 52f and OD 44f only; no light / heavy rules), Sinister Slide follow-up names and the rule to name the ending.
- sf6-fgc-glossary: Homura (Mai's SA1 flame stocks).
- quick-review-report: corner time among the numbers to pull.
- shared-core-review: one manifest at a time for several sets; game count as a hint; "(known: ...)" predictions.
- batch-record-replays: the progress bar and how to read it.

## 0.2.10 (2026-11-27): corner time, batch progress bar
- Bundled tools from shotokan-sf6/tools (2026-11-27):
    - New `corner_time.py`: seconds each player spends cornered per round (within 1.5 of the wall, opponent on the inner side, live play only). The analyzer writes `corner.json` and report.md lines; ingest stores `corner_time` and `cornered_frames` / `cornering_frames` / `active_frames` / `cornered_entries` in `set_stats` and `game_stats`; `--backfill DB` fills older sets.
    - `batch/batch_record.py`: a progress bar after each replay, with time left.
- README: corner time and the progress bar.

## 0.2.9 (2026-11-26): notable players, excluded sets
- `shared_core_db.py`:
    - New `player_flags` table and `flag` / `flags` commands, to mark notable / pro players.
    - New `sets.excluded` and an `exclude` command: a set stays in the database but is left out of prediction history and the published site. META `excluded` sets it at ingest.
- shared-core-review: a set whose rounds open with about 30 s of warm-up is a 1v1me betting match. Ask before reviewing it, and ingest it with `excluded: "1v1me"`.
- README: database extras.

## 0.2.8 (2026-11-26): reviewed date
- `shared_core_db.py`: new `sets.reviewed_at`, the time a set was first reviewed. It's set on the first ingest and kept on re-ingest (unlike `ingested_at`), or taken from META `reviewed_at`. Existing databases are backfilled from `ingested_at` (else 2026-11-26) when they're opened. SHOTOKAN Web sorts its latest reviewed sets by it.

## 0.2.7 (2026-11-26): wiki move names, fireball Drive Rush, A.K.I. notes
- Move names checked against the SuperCombo move lists and matched to each capture's inputs, in `shared_core_analyze.py`. A.K.I. had three wrong labels. 2PP is Sinister Slide (was "Snake Step (Akidako)"), with its follow-ups Venomous Fang, Heel Strike and Entrapment (grab). 236K is Snake Step (was "Cruel Fate (Jakeiko)"), and 214K is Cruel Fate. Also named: Orchid Spring, Toxic Wreath, Nightshade Chaser, j.2HP Gong Fu, and SA1-SA3. Jamie: Swagger Step, Arrow Kick, Luminous Dive Kick, Tenshin, Bakkai, The Devil Inside. Alex: Flash Axe / Chop, Power Bomb (attempt / hit), Prowler Stance and its follow-ups, held 5HK / 5HP, j.2HP. Elena: Scratch Wheel, Spinning Scythe, Rhino Horn, the Lynx Song family, Moon Glider, SA1-SA3. Earlier in the day: more supers / specials for A.K.I., C. Viper, Dhalsim, Yasmine, Alex, Ingrid, Chun-Li and Kimberly, and bare `DRIVE_RUSH` counted as Drive Rush (Chun-Li, C. Viper). Use `relabel_moves.py` / `relabel_resolve.py` to bring an existing database up to date.
- `frame_data`: block-advantage aliases for Arrow Kick, Air Knee Smash and Scratch Wheel.
- New `full_review_fireball_drive_rush.py`: fireball Drive Rush value per character and player (damage either way in the next 30 frames, Drive cost, what the first button met, the mixup after a blocked button, round win rates when it netted positive or negative), with raw Drive Rush as the comparison.
- `shared_core_db.py ingest`: META `incomplete: true` stores no winner (a ranked FT2 left at 1-0 or 1-1).
- `profiles_from_db.py`: Entrapment label.
- Skills: full-review-report lists `sf6-fireball-101-exdojo` and `sf6-replay-feedback` (not bundled). sf6-character-notes adds an A.K.I. section from a high-level vs intermediate comparison: throw loops and shimmies, fireball volume, pressure Drive Rush, Sinister Slide / Entrapment, weaknesses and per-round baselines.

## 2026-11-25 (0.2.6)
- MR per game, from sfbuff's formula (github.com/alanoliveira/sfbuff, `app/models/master_rating_calculator.rb`: Elo with K = 16). `shared_core_db.py` stores `games.p1/p2_mr_change` (observed from the same player's MR in the set's next game, calculated for a set's last game) with `mr_change_source`, and `sets.opp_mr_start`, `focus_mr_end`, `opp_mr_end`; ingest fills them and warns when an observed change disagrees with the formula (usually games stored out of played order). New commands `mr DB [SETKEY ...]` (backfill) and `odds DB MY_MR OPP_MR`. On the author's database the formula matched the next game's MR in 314 of 316 game sides; the other two were one set stored in the wrong order.
- `shared_core_blind_manifest.py` adds `mr_odds` when both players have an MR: each player's MR at stake (win / loss) and game, FT2 and FT3 win chances. Every game has 16 MR at stake, so the MR a player would lose is 16 x their game win chance. replay-review-prediction says to start from it and how far to trust it (small gaps played like coin flips; bigger gaps favoured the higher MR more than the formula says).
- `buckler_replays.py --raw FILE` saves Buckler's raw pageProps for each page fetched, to look for fields the script doesn't read yet. (Checked 2026-11-25: neither the battle log nor the Master ranking page says which ranked phase is current.)

## 2026-11-25 (0.2.5)
- Move names for Akuma, Sagat and Ingrid in the bundled `tools/shared_core_analyze.py`, checked against SuperCombo: Akuma's Gou Shoryuken (was labelled "Rising Uppercut"), Gou Hadoken, Zanku Hadoken, Adamant Flame, Demon Raid and its follow-ups, Tatsumaki Zanku-Kyaku, Ashura Senku / Oboro Throw, his supers and the alternate Critical Art Shun Goku Satsu (Raging Demon); Sagat's Low / High Tiger Shot, Tiger Uppercut, Tiger Knee Crush, Tiger Nexus, SA1-SA3 and target combos; Ingrid's Sun Shot, Sun Rise, Sun Flare / Solar Burst, Vanishing Sun, SA1-SA3 and target combos. Ingrid's `22P_DAGEKI` / `22P_Tama` are read as Sun Veil (her counter) catching a strike / projectile: inferred, the wiki lists no 22P. A few guesses are marked in the code comments.
- `frame_data`: block-advantage aliases for Adamant Flame, Tatsumaki Zanku-Kyaku, Tiger Knee Crush, Tiger Nexus, Sun Rise, Sun Shot, Sun Flare and Juri's Tensenrin.
- `shared_core_db.py history`: same-day sets now count as earlier by their first game's played time (to the minute), not their ingest time; `--before` accepts a `T` or a space; same-day sets are sorted in played order, so the recent-habits list picks the right sets. Before this, earlier sets from the same day were always left out of a prediction's history.
- `quick_review_reads.py`: Akuma's anti-air wording says Gou Shoryuken.

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
