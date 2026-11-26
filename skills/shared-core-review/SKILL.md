---
name: "shared-core-review"
description: "Shared core of every SF6 replay review (Quick and Full): setup, played order, blind prediction, the analyzer, capture storage, the sf6.db ingest, grading the prediction, and the wording and data rules every review follows. Loaded by sf6-replay-analysis before quick-review-report."
---

# Shared core: every SF6 review

The first tier of every review. `sf6-replay-analysis` loads it, then `quick-review-report`, then (for a Full review) `full-review-report`. The rules here apply to all three.

**Player config.** Read `<coaching folder>\shotokan.json` first (written by shotokan-setup): the player's name, CFN ID, other names and main character. Wherever these skills say "the player", it means that person; their CFN ID is the focus player for ingest and comparisons.

The player submits recorded SF6 replays (REFramework captures, OBS or console video, sometimes paused screenshots) and says which character they played. Their main is in shotokan.json, but they may play others, so always use the character named for that replay.

**Reference files** live in this skill's `references/` folder (`${CLAUDE_PLUGIN_ROOT}/skills/shared-core-review/references/`). Read one before the step that names it, not from memory.

**Tools** live in `<coaching folder>\tools\`. The review-step scripts are named by tier: `shared_core_*.py` here, `quick_review_*.py` and `full_review_*.py` in the other tiers.

## 1. Confirm the setup (ask only what's missing)
- **The player's character:** they state it. If they don't, ask; don't assume their main.
- **Opponent's character:** from the capture, the HUD name plates or the intro frames. Ask only if unclear.
- **Which side the player is on (P1/P2):** from their CFN ID (in shotokan.json) or name. Ask if you can't tell.
- **Focus:** if the player names something to work on, weight the review toward it.
- **Control type:** Classic or Modern (it changes which moves exist).
- **Frame meter and input history** (video only): check whether they're on. If not, mention once that turning them on in replay display settings makes the analysis much more accurate, then carry on.
- **Depth:** note whether they asked for a "Quick Review", "Full Review" or "Tournament review". If not, it's decided in step 5.

## 2. Captures and storage
- `capture_replay.lua` (window "Replay Capture v3.3") autosaves `<ReplayID>.json` when a replay ends, with each player's CFN ID (`p1_cfn_id`/`p2_cfn_id`), MR and LP when the replay carries them. `export_moves.lua` writes `sf6_moves/<id>_<Name>.json`, `enums.json` and reads `char_names.json`. If a capture's CFN ID is missing, check its `player_fields` list and fix the script.
- When a capture exists it is the source of truth for hits, damage, hit kinds, anti-airs, burnouts, parries, throw techs, Drive Reversals, Drive Rushes, inputs and timings. Video is only for story moments.
- **Storage:** captures and videos `<ReplayID>.mp4` go in `<coaching folder>\replays\`. Move captures there from the game's `reframework\data` and videos from `the player's video folder`. After analysis, `gzip -k` each capture, check the .gz decompresses to the same bytes, then delete the .json. Every tool reads .json and .json.gz alike.
- **Review folder:** `<coaching folder>\reviews\<YYYY-MM>\<date>_<type>_<opponent>\` (type: ranked, training, tournament or review) holds prediction.json, manifest.json, meta.json and the analyzer's `review\` outputs. One-off analyses go in `work\`.
- Capture details (resource log, per-combo fields, parries, report.md sections, rank thresholds, decoding raw files): `shared-core-capture-data.md`. Read it before interpreting resources, parries or per-combo fields.
- Replay IDs instead of files: `shared-core-recording-from-ids.md` (automatic playback of replay IDs through REFramework isn't set up yet).
- A game with no capture: `shared-core-video-processing.md` (video passes, event log). In a mixed set, say which numbers are measured and which are read from video.

## 3. Played order
Review and analyze games in the order they were played, not recorded, unless the player says otherwise. Captures carry no play time and the batch recorder records newest-first, so take the order from the Buckler battle log the recorder used (`tools\batch\<cfn_id>_replays.json`, field `uploaded_at`), reading only replay IDs and times before the prediction (never results). If no battle log covers the games, ask the player.

## 4. Prediction first (always)
Before opening any capture, analyzer output or video of a set, write the pre-set prediction with `replay-review-prediction`, even when the player doesn't ask:
1. `python tools\shared_core_blind_manifest.py <first game played> --out manifest.json` (first game's header only).
2. `python tools\shared_core_db.py history DB --opp NAME|CFN --opp-char C --my-char C --before <first game's time>` for pre-set history (only earlier sets).
3. Write prediction.json and store it with `python tools\shared_core_db.py predict DB prediction.json` before the analyzer runs. It can't be changed once the set is ingested.

## 5. Analyze and decide the depth
- Run `python3 tools/shared_core_analyze.py OUTDIR <focus player> <FT2|FT3|FT5> <game1> <game2> ...` with the games in played order. It writes `sets/games/hits/events/timings/resources/parries/presses.json` and `report.md`.
- **Depth:** what the player asked for; otherwise **Quick for sets the player won, Full for sets they lost** (from that player's side when reviewing someone else). Say which each set got. Tournament is the level above Full (tournament sets, or when asked).
- Before reviewing, query sf6.db for earlier sets against the same opponent (by CFN ID, else name) and the same character matchup, and say what changed.

## 6. Ingest
Work on a `$HOME` copy of sf6.db (SQLite on the device mount fails), then copy it back and check no `-journal` file is left. Back up first: `sf6.db.bak-<date>-<label>`.
- `python tools\shared_core_db.py ingest DB OUTDIR META.json`. META: `set_key`, `focus`, `played_date`, `ranked`, `review` (Quick / Full / Tournament), `format`, `captures`, `captures_local` (paths on the machine running the ingest), `focus_mr` (a list), `game_times` (played order), `note`, `source`, and `review_docs` with at least the graded `prediction`. Re-ingesting a set replaces it; review_docs are kept.
- The ingest computes both players' eight spectra (definitions: `shared-core-player-spectra.md`), adding the set's replays to `beh_cache.json` first (`--no-spectra` skips it; `tools\spectra_backfill.py DB` fills any set without spectra), and links the stored prediction.
- **Add every reviewed set**, including sets where the player isn't in it.
- An incomplete set (e.g. a ranked FT2 left at 1-1) stays 1-1 with no winner and no prediction grade.
- **1v1me betting matches:** a set whose rounds open with about 30 seconds of warm-up (jumping, random buttons, no real exchange) is a 1v1me betting match (2026-11-26). Tell the player before reviewing it. If it's confirmed, ingest it with META `excluded: "1v1me"`: it stays in sf6.db but is left out of history, predictions and the published site. To exclude a set that's already in the database, run `shared_core_db.py exclude DB SETKEY 1v1me`.
- Grade the prediction (predicted vs actual, path, what happened, lessons) and store it in `review_docs.prediction`.
- The long-term views are the SHOTOKAN site, published from sf6.db (no tracker sheet; retired 2026-11-25).
- sf6.db also has the views `v_sets`, `v_player_matchups` (me vs an opponent) and `v_char_matchups` (my character vs theirs); the site is a view of it.

## 7. Rules every review follows
- **Timestamps:** round + `round_timer`, written "@" (G1 R2 @77).
- **Rank labels:** below Master, the league only ("Diamond"); Master with an MR, "<MR> MR"; without, "MR unknown"; LP -1, "Unranked". Use `tools\rank.py`; keep the LP and MR themselves in the database.
- **Results:** don't write a match as a round score ("Lost 1-2"). Say won or lost, with rounds separately; a set of matches is in games ("lost 2 games to 1").
- **Throws vs throw techs:** a throw is offensive (trying to throw); a throw tech is defensive (pressing throw to avoid being thrown, on wake-up or after blocking). Never mix them. The analyzer labels `Throw tech attempt` when the throw started just out of blockstun or on wake-up and `Throw attempt` otherwise; check the situation (an offensive throw that whiffs because the opponent walked away is a shimmy, not a lost tech).
- **Drive Rush classes:** raw drive rush (from neutral, 1 bar; Drive Parry > Drive Rush is raw even inside a blockstring), pressure drive rush cancel (in a blockstring, 3 bars), combo drive rush cancel (in a combo, 3 bars).
- **Burnouts:** a burnout spent on a combo that kills (lethal) isn't counted.
- **OD specials:** the analyzer marks a special OD when its start drains at least 15,000 Drive within 12 frames. Trust the OD label over the strength label.
- **Confidence:** never make up inputs or frame values; mark what the data can't prove "likely" or "unclear", and ask the player what they were going for when it matters.
- **Reviewing another player** (e.g. "Sayo, playing Ryu"): analyze from that player's side, keep it out of the player's own stats, confirm which in-game name is theirs, and deliver what was asked for.

Then continue with `quick-review-report`.
