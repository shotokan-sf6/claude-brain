---
name: "sf6-replay-analysis"
description: "Analyze Street Fighter 6 replays from REFramework capture files (when present) and recordings (video or screenshots): read the frame meter and HUD, log key moments by round and round timer, check against SuperCombo frame data, report both players' habits and fixes, and log the player's replays to his SF6 Replay Tracker sheet."
---

# SF6 replay analysis

> **Installed skills only.** This plugin ships the analysis, prediction, dashboard, glossary, character notes, Drive efficiency, Juzzy and Maj skills, and .shog's coaching rules as an example. Other coaching skills named in this text (E.X. Dojo, Coosco, DoctaAfrikan) aren't included: load them only if the player has installed them, otherwise skip those checks.

**Player config.** Read `<coaching folder>\shotokan.json` first (written by shotokan-setup): The player's name, CFN ID, other names and main character. Wherever this skill says "the player", it means that person; their CFN ID is the focus player for ingest and comparisons.


The player submits recorded SF6 replays (OBS or console capture, sometimes paused screenshots) and says which character they played. Their main character is in shotokan.json, but they may play others, so always use the character named for that replay.

**Guideline skills to load every review.** Before analysing any replay, load each of these skills with the Skill tool and apply them alongside this one:



- `sf6-coach-shog`: The player's own coaching rules, which override the other skills where they conflict: cancelable 2MK can't be hit-confirmed (non-cancelable +4 on hit can), classify wake-up options (normal = read, invincible reversal = decision, unsafe non-invincible special = input error), and don't say "tech more" by default (only tech a shown pattern; a taken throw is often the safe choice).

- `sf6-character-notes`: character baselines (jumps, Drive Rush, parries, throws per round) and notes, so a habit is judged against what is normal for that character (a Cammy jumping a lot is expected; a Ryu jumping a lot is likely a leak). Suggest new notes when a review shows something character-specific.

- `sf6-footsies-handbook-maj`: Maj's Footsies Handbook (Elements 01-35, Rules #1-#4, projectiles), with SF6 translations. Check neutral baits, the corner, super/DI baiting, "what was this jump meant to land on?", walk-in strike/throw timing, crossup setups, predictability and tactic vs gimmick; cite elements by number. Its examples come from older games: when an SF6 translation proves wrong, update that line.
- `sf6-fgc-glossary` (reference, load when needed): Infil's FGC glossary (General + Street Fighter terms) for consistent wording and quick definitions.

- `sf6-drive-efficiency`: value every Drive and super spend against the best free route (damage, knockdown advantage, corner, Drive damage dealt, Drive gained back) on offense, and against blocking (chip, Drive lost blocking, the attacker's shown follow-up frequencies) on defense; each player's Drive economy (spent, lost blocking, lost to punish counters / Drive Impact, gained from hits, blocks and parries); parry net Drive and times thrown out of parry; what drained each player before a burnout.

When the player adds another guideline skill, add it to this list.

## Review depth: Full Review vs Quick Review
The player picks the depth by asking for a **"Full Review"** or a **"Quick Review"**. If he doesn't say, default per set: **Quick for sets the player won, Full for sets he lost** (decide once the analyzer gives the result, and say which each set got). This applies when reviewing someone else too, from that player's side.
- **Quick Review (automatic):** run the analyzer, then build every per-set card (habits, story, reads, punishes, fixes, training) from the capture stats with `tools\ranked_build.py` (and `tools\ranked_overview.py` for a cross-set overview). Check video only for rows that look wrong. Fast and consistent across sets, but no intent, no hand-picked turning points, and player reads come from simple thresholds.
- **Full Review (hand-written):** run the analyzer, then go through report.md exchange by exchange, check story moments and surprising rows against the video, correct analyzer mistakes, and write the story, habits, player reads, punishes and fixes by hand using the guideline skills above.
- Tag each set's `sets` row with `review: "Full"` or `review: "Quick"` and show it in the dashboard subtitle, so mixed dashboards are clear.
- Open question (the player, 2026-11-18): which parts of a review benefit from hand-written notes and which don't. Revisit with him before changing either mode.

## 0. Capture files first (REFramework)
The player records replays in SF6 with REFramework scripts: `capture_replay.lua` (window "Replay Capture v3.3") autosaves `<ReplayID>.json` when a replay ends, including each player's CFN ID (`p1_cfn_id`/`p2_cfn_id`, Buckler `short_id`; .shog = 1307078698), MR and LP when the replay data carries them, and `export_moves.lua` ("Move Export v4") makes `sf6_moves/<id>_<Name>.json` and `enums.json`. If a capture's CFN ID is missing, check its `player_fields` list for where the ID lives and fix the script. Copies of all tools live in `<coaching folder>\tools\`.
- **Storage:** every replay's capture and video `<ReplayID>.mp4` go in `<coaching folder>\replays\`. After a replay is recorded, move the capture there from the game's `reframework\data` folder and the video there from `C:\Users\seanh\Videos`, then look for both files in that folder. Captures are stored **gzip-compressed as `<ReplayID>.json.gz`** (about 40x smaller): after analysis, `gzip -k` the .json, check the .gz decompresses to the same bytes, then delete the .json. The analyzer and sf6db.py read .json and .json.gz alike. Review outputs stay in their own `<review-folder>\review\`; `enums.json` and `sf6_moves\` are not replays.
- **Look for `<ReplayID>.json`** next to the video (or where the player says). When it exists, it is the source of truth for hits, damage, hit kinds, anti-airs, burnouts, perfect parries, throw techs, Drive Reversals, Drive Rush counts, inputs and timings. **Use video only for story moments**: spacing, intent, what a player was going for, anything the capture doesn't record.
- **History database**: `<coaching folder>\history\sf6.db` (SQLite) is the long-term record of every reviewed set: players (CFN ID + name history), sets, games, hits, events, timings, per-set stats (long format, `set_stats`), player reads, habits and matchup notes, with views `v_sets`, `v_player_matchups` (me vs an opponent) and `v_char_matchups` (my character vs theirs). **After every review, ingest the set** with `tools\sf6db.py ingest DB OUTDIR META.json` (META: set_key, focus, played_date, ranked, review Full/Quick, captures, reads, habits, char_names; see the docstring). Re-ingesting a set replaces it. META also needs `captures_local` (each replay's capture path on the machine running the ingest) and `focus_mr` as a list. The ingest computes both players' eight spectra (spectra table and review_docs archetypes), adding the set's replays to `beh_cache.json` first; `--no-spectra` skips it, and `tools\spectra_backfill.py DB` fills any set without spectra. To compare players' decisions (where they press, which buttons, what it leads to), run `tools\decision_presses.py DB --player NAME[,ALIAS] ... [--char C]`. Match opponents by CFN ID when the capture has it, else by name. Before reviewing a set, query the database for earlier sets against the same opponent and the same character matchup, and say what changed. The Replay Tracker sheet and dashboards are views of it.
- **After every ingest, refresh the long-term views** (see section 7): run `tools\sf6db_export.py DB OUTDIR` and rewrite the sheet's Set Metrics, Player Reads, Opponents and Character Matchups tabs from its output, then re-upload those four tabs to the tracker dashboard.
- **quick-dashboard** (link in shotokan.json, if the player has one) is built from the database too. Ingest with `dash: {"dashboard": "quick-dashboard"}` in META (gives the set the next stable "Set N"), and for a **Full** review also pass `review_docs` (the hand-written story, story_games, habits, archetypes, fixes, training, findings, punish and sets rows, plus `set_gameplan`: each player's gameplan, mid-set adjustments, what worked, and how each should adjust, shown in the dashboard's Gameplan section; and `prediction` when replay-review-prediction was used), which are kept across re-ingests. Then run `tools\quick_dashboard_from_db.py DB OUTDIR --write-reads` (Set review datasets; Quick reviews are regenerated and their reads/habits written back to the DB) and `tools\overview_from_db.py DB OUTDIR` (Overview: ov_sets, overview, gameplan, ov_training, every number computed from the DB). Upload each changed JSON with upload_asset and update that dataset's `source.url` and `updated`. Run the quick-dashboard step before the sheet export, since it can change Player Reads.
- **Prediction first (always)**: before opening any capture, analyzer output or video of a set, write the pre-set prediction with `replay-review-prediction`, even when the player doesn't ask for one; grade it after the review and store it in `review_docs` as `prediction`.
- **Workflow**: stage the capture files and `tools\analyze_capture.py`, then run `python3 analyze_capture.py OUTDIR <focus player name> <FT2|FT3|FT5> <game1.json> <game2.json> ...` (games in set order). It writes `sets/games/hits/events/timings.json` in the sf6-review-dashboard schema, `resources.json` and `parries.json` (below), plus `report.md`.
- **Resource log** (`resources.json`, `resources` table in sf6.db, dataset `resources` on dashboards): per player per round, Drive bars spent by category (Drive Rush, Drive Parry, Drive Impact, Drive Reversal, OD specials, other; `drive_rush_cancel` is the part of Drive Rush spent on 3-bar cancels, the rest is raw), super bars spent with each super (move, bars, round timer), burnouts, and Drive / super left at round end. Drive drops only count as spending while the player isn't in hitstun, blockstun or already burnt out (the drop that empties the gauge starts burnout on that frame and still counts, here and in Drive lost blocking); an uncategorised drop of 15,000+ is counted as OD. Each super is written `L<level> <move>[ extended] (<bars> bars[, +<n> Drive]) @<timer>`: the level is the bars its first drain used, and a later drain while the player never left the super animation (and isn't a fresh super start) is the same super, e.g. Terry's SA2 taking a 3rd bar, with the Drive spent on its 3rd hit. Report extended supers at their own level, not as a Level 3. It also records the **Drive economy**: `gain_hit` / `gain_block` (Drive gained when their attacks hit or are blocked), `parry_regain`, `loss_block` (Drive lost blocking), `loss_hit` (lost getting hit), with `loss_hit_drive_impact` and `loss_hit_punish_counter` split out.
- **Per combo** (hits rows, `hits` table): `drive_spent` and `super_spent` (from 20 frames before the first hit until the attacker is free), `drive_gained`, `drive_damage` (the victim's Drive lost), `knockdown` (hard knockdown / back recovery / normal recovery), `kd_adv` (frames the attacker is free before the victim; on a knockdown the victim's first frame out of the wake-up counts as free even if it blocks or gets hit by a meaty; without a knockdown it's frame advantage after the combo, dropped when over 60), `corner_dist` (victim's distance to the corner afterwards), `victim_drive_after`.
- **Parries** (`parries.json`, `parries` table, dataset `parries`): each Drive Parry with frames held, Drive before, cost, hits parried, Drive regained, net, perfect, and what happened next (nothing, raw drive rush, punished them, hit, thrown). A perfect parry at full Drive shows cost 0 (nothing to refund).
- report.md has `resources R<n>`, `contact R<n>` (gains and losses), `Drive efficiency` (each combo that spent resources or knocked down) and `Drive Parries` sections. Read report.md first; check surprising rows against the video.
- **Characters**: base damage for every character's normals is in `tools\base_damage.json` (SuperCombo, full roster), which the analyzer loads. Character names come from `reframework\data\sf6_moves\char_names.json` (the player names new IDs in the Move Export v4 window); the export, the capture script (v3.2) and the analyzer all read it. For a newly released character, re-pull its normals from SuperCombo into base_damage.json and add its specials/supers to `SPECIALS` in analyze_capture.py; until then, say its counter hits are unmeasured.
- **Decoding rules** (built into the analyzer; use them when reading a raw file):
  - Input bits: 1 up, 2 down, 4 screen-left, 8 screen-right, 16 LP, 32 MP, 64 HP, 128 LK, 256 MK, 512 HK. `input_side` 0 = on the left; convert screen directions to forward/back per side.
  - Move names: `ATK_` normals (`ATK_8xx` = jump normals), `SPA_` specials, `SA1`/`SA2`/`SAA` supers, `CAA` Critical Art, `NGA`/`NGS`/`NGD` throws, `DPA` Drive Parry, `ATK_CTA_4` Drive Reversal, `ATK_CTA_RUSH` / `ATK_CTA_DASH` Drive Rush (cross-check with the `Gauge_RushC` stat). `DRD_*` is a guard animation, **not** Drive Rush.
  - **Drive Rush types** (the analyzer logs them as events). **Cost decides cancel vs raw**: a cancel is the 3-bar Drive Rush (one 30,000 drop about 10 frames in); Drive Parry > Drive Rush costs 0.5 + 0.5 = 1 bar and is a **raw drive rush** wherever the opponent is, even inside a blockstring. For the 3-bar cancels, the opponent's state on the frame the rush starts gives the type: **combo drive rush cancel** = opponent getting hit (cancelled from a confirmed hit); **pressure drive rush cancel** = opponent blocking (in a blockstring); **whiff drive rush cancel** = neither (cancelled from a whiffed button, rare). Always use these names in reports. Only raw and pressure Drive Rushes count toward aggression in player reads (the dashboards' "Raw + pressure DR" column); combo cancels are cashing in on a hit. Before Nov 2026 (analyzer fix) about 30% of logged "cancels" were really parry rushes, so older counts quoted in reviews may be off.
  - Damage = the permanent life the victim lost over the combo (the drop in `hp_recoverable_cap`), so white (recoverable) health a hit cashes in counts; damage that only adds white health (Arjun's blocked pressure, Drive Reversal) counts 0. Hit rows also carry `recoverable` and `white_cashed`. After an analyzer change, `tools\rescore_damage.py DB CAPTURE_DIR` re-scores an existing database.
  - **Counter hit**: first-hit damage at least ~1.15x that normal's SuperCombo base damage. **Punish counter**: hitstun 2 frames longer than the move's counter-hit hitstun (e.g. Blanka 5LP 16 clean / 18 CH / 20 PC).
  - **Anti-air**: the victim is airborne (jump states or posY > 0.3) and the attacker grounded on the first hit; juggles don't count.
  - Read the victim's state ~15 frames before the hit (at the hit frame it's always DAMAGE). For trades, use the attacker's previous move.
  - Burnout = runs of the incapacitated flag; a burnout that starts inside the player's own combo that kills is a `lethal burnout` and is not judged as a burnout (spending everything for lethal is correct); perfect parry = Stats `ParryJust`; throw tech = `ThrowTech`; Drive Reversal = `DrvRev`.
  - **Timings**: frames from the end of blockstun or wake-up to the first action. Sort them into the stagger-pressure slots (frame 1, ~3, ~6, ~12, or held block).
- **Timestamps**: use round + `round_timer` (written "@" on dashboards, e.g. G1 R2 @77).
- **Player rank labels (from the player)**: name each player's level from the capture's LP and MR (`tools\rank.py`, `p1_rank`/`p2_rank` in the `games` table and dashboards):
  - below Master (LP under 25,000): the league name only, e.g. "Diamond", not "Diamond 3". League starts: Rookie 0, Iron 1,000, Bronze 3,000, Silver 5,000, Gold 9,000, Platinum 13,000, Diamond 19,000, Master 25,000;
  - Master with an MR: "<MR> MR"; Master with no MR in the replay: "MR unknown";
  - LP -1: "Unranked" (shown in game as "New Challenger");
  - captures from scripts older than Replay Capture v3.3 have no LP: use the MR if there is one, otherwise leave it blank.
  Keep the LP and MR themselves in the database (`p1_lp`/`p2_lp`, `p1_mr`/`p2_mr`), since later analysis may correlate behaviour with rank or MR.
- With a capture, skip the video passes in section 3 and the health-bar and meter-scan methods in section 5; run the section 5 checks off the analyzer output, and pull short video clips only for the story moments.
- A game with no capture falls back to sections 1-5 as usual. In a mixed set, say which numbers are measured and which are read from video.
- Automatic playback of replay IDs through REFramework isn't set up yet: record via section 1b.

## 1. Confirm the setup (ask only what's missing)
- **The player's character**: he states it. If he doesn't, ask, and don't assume Cammy.
- **Opponent's character**: read it from the HUD name plates or the intro/loading frames. Ask only if it's unclear.
- **Which side the player is on (P1 or P2)**: read it from his player name or the HUD. If you can't tell, ask.
- **Focus**: if the player names something to work on (anti-airs, defense, wake-up, Drive management…), weight the report toward it.
- **Control type**: Classic or Modern (an M icon on the HUD). It changes which moves exist, so check it.
- **Frame meter and input history**: check whether they're on. If they aren't, mention once that turning them on in replay display settings makes the analysis much more accurate, then carry on without them.

## 1b. Recording replays from replay IDs (when the player gives IDs instead of videos)
Use computer use on his PC (load the computer-use skill first). Apps: SF6 (`d:\program files (x86)\steam\steamapps\common\street fighter 6\streetfighter6.exe`; resolve it by that path, the name doesn't resolve) and OBS Studio, plus File Explorer (click tier) and the system-key-combos grant so Win+Tab (Task View) works. OBS saves to `C:\Users\seanh\Videos` (request that folder for device access).
- **SF6 input**: menus move with **WASD** (not the arrow keys), F = confirm, Esc = back. Tapped keys are often missed: use `hold_key` for about 0.15 s. Click an empty area of SF6 first so it has focus.
- **Get to Replays** from the Fighting Ground: Tab (Multi Menu) > D, F (CFN) > D, D, F (Replays, opens on the Search tab).
- **Load a replay**: from the search results, hold Esc to go back to the form (the cursor lands on "Search by player name"), hold S twice to reach Search by Replay ID, hold F to open the dialog. Wait ~1 s, press Return to enter edit mode, wait ~1 s, Backspace x12, type the ID, wait ~1 s, Return to commit, wait ~1.5 s, hold S to move to Search. Zoom on the dialog before searching: if the field still shows a text cursor or the yellow outline instead of Search being highlighted, a key was missed: press Return once more, wait, and hold S again. Then hold F to search and hold F on the result to open its details screen (note the opponent, character and Won/Lost there).
- **Record**: Win+Tab, click the OBS thumbnail (with SF6 first in Task View, about (650,115) in the 1456x819 frame), click Start Recording (about (1192,568)), zoom to confirm it now reads Stop Recording, click SF6 (about (1300,790)) to refocus it, hold F on Watch Replay. Matches run about 2.5 min (2 rounds) to 4.5 min (3 rounds); poll with screenshots every ~50 s. The Ctrl+F9/F10 OBS hotkeys did **not** trigger from simulated keys, and the OBS WebSocket can't be reached from the device shell, so use the button. Don't use `open_application` on OBS when it's already running (it offers to start a second copy: Cancel).
- **Check** the first in-match frame for the frame meter, input history and damage panel.
- **Finish**: at the Play Again / End Replay screen, Win+Tab to OBS and click Stop Recording (zoom to confirm it reads Start Recording again), click SF6, then hold S + F on End Replay. Rename the newest OBS file in Videos to `<ReplayID>.mp4` with device_bash (`ls -t <date>*.mp4 | head -1`), and move it and the capture `<ReplayID>.json` into `<coaching folder>\replays\`. Then stage and analyse it, unless the player only asked for recordings.
- If Claude's own window covers SF6, click an empty part of the SF6 screen before sending keys.
- Release the computer-use lock at the end of the turn.

## 2. Get the frame data (SuperCombo wiki)
WebFetch is blocked by the wiki's bot check. Use the built-in browser (load the built-in-browser skill first). If the site isn't allowed yet, use request_access.

- Frame data: `https://wiki.supercombo.gg/w/Street_Fighter_6/<Character>/Frame_data`
- Overview, strategy, matchups: `.../<Character>`, `.../<Character>/Strategy`, `.../<Character>/Matchups`
- System mechanics: `.../Street_Fighter_6/Gauges` (Drive Rush/Impact/Parry/Reversal, burnout), `.../Glossary`, `.../Offense`, `.../Defense`
- Character slugs use underscores and keep dots: `C._Viper`, `E._Honda`, `M._Bison`, `A.K.I.`, `Dee_Jay`, `Chun-Li`. If a slug 404s, open `https://wiki.supercombo.gg/w/Street_Fighter_6` and take the link from the character list.

Pull each page's tables in **one** javascript_tool call instead of reading the whole page. This compact version keeps only the frame-data, punish and notes tables, one row per line, with long notes trimmed:
```js
[...document.querySelectorAll('table')].filter(t=>/Startup|Notes|Punish Adv/.test(t.rows[0]?.innerText||'')).map(t=>[...t.rows].slice(1).map(r=>[...r.cells].map(c=>c.innerText.replace(/\s+/g,' ').slice(0,140)).join(' | ')).join('\n')).join('\n=====\n')
```
The result comes back into the conversation, not to disk, so pull each page once per session and refer back to it. Get both the player's character and the opponent's: punish and pressure questions need the opponent's block advantage. The Invuln column matters for wake-up questions (e.g. a special that's only throw-invulnerable is not a reversal).

The Matchups page sections are sometimes empty placeholders. If so, say so and build matchup notes from the opponent's frame data and this replay.

The tables use numpad notation (5MP, 2MK, 236HK) with these columns: Damage, Startup, Active, Recovery, Total, Hit Adv, Block Adv, Guard, Cancel, Hitconfirm. Use the same notation in reports. Frame data changes with patches, so always cite the wiki values you pulled, not remembered ones.

## 3. Process the video
When a capture file covers the game (section 0), only do the detail pass, for story moments. Put each upload in its own folder and work on a copy. Check that ffmpeg is installed (`which ffmpeg`) and install it if it's missing. If the player sent screenshots, read those first: paused screenshots are the most legible source.

1. Run `ffprobe` to get the duration, fps and resolution.
2. **Overview pass**: extract frames at about 2–4 fps and tile them into contact sheets with timestamps burned in, for example:
   `ffmpeg -i in.mp4 -vf "fps=3,scale=640:-1,drawtext=text='%{pts\:hms}':x=8:y=8:fontsize=20:fontcolor=white:box=1,tile=4x3" sheets/s_%03d.jpg`
   From the sheets, find round starts and ends, knockdowns, big health swings, Drive gauge drops, burnout (grey gauge), supers, and corner position.
3. **Detail pass**: for each key moment, extract a window at full fps (or at least 30 fps) that starts **1–2 s before the exchange begins** (the lead-up: what each player was doing, such as walking, pressing a button, jumping, blocking, or getting up from a knockdown) and runs through the end of the exchange. The lead-up is what answers how a hit happened (was the player walking forward, did he press into a frame trap, was it a whiff punish), so never start the clip at the hit itself; the input history at the clip's first frames shows the inputs that led in. Crop and zoom on the action, the **frame meter**, and the **input history**, and look at those frames to read what each player actually did.
4. HUD regions at 1920×1080 (scale for other resolutions): **round timer** top centre (about `crop=300:110:810:0`), health bars either side of it, Drive gauges under the health bars, SA gauges bottom corners (`crop=480:110:0:930` and `crop=480:110:1440:930`), input history down the left (P1, about x 0–260, y 225–880) and right (P2, x 1660–1920) edges, damage panel top centre (when the replay's training display is on: Damage / Combo Damage / Attack Type, left column = P1's damage dealt), and the **frame meter** above the bottom HUD (about `crop=1240:135:340:770`) with its "Startup / Total / Advantage" text line per player.
5. **Composite frames**: for the detail pass, build one image per moment that stitches both input histories, the top panel (timer + damage), a shrunk scene, and the frame meter (Python + PIL on an ffmpeg-extracted PNG). Stack two composites per image to halve the reads. At 1080p everything in a composite is legible.

### Timestamps: round + round timer
Reference every moment as **round number + time left on the round timer**, e.g. **R1 93**, because that's what the player sees when he scrubs the replay in-game.
- Read the round number from the ROUND / FINAL ROUND cards, or by counting rounds.
- Read the timer from the same frame as the moment, not by guessing between contact-sheet frames.
- The timer freezes during super cinematics, KOs and round transitions, so several events can share a second. Separate them as **R1 93a / R1 93b** or with a short description.
- Keep video time in your own notes for re-extracting frames, but don't show it in the report unless there's no timer (training mode shows ∞ or none; then use video time and say so).

### Reading the HUD and input display
- **Input history**: newest at the top; the number is how many frames that input was held. Buttons are coloured icons: light blue = light, yellow = medium, red = heavy; a fist is a punch, a shoe is a kick. Read the shapes from a full-resolution crop, since they're hard to tell apart when shrunk. Two yellows (MP+MK) = Drive Parry; LP+LK = throw / throw-tech attempt.
- **Directions** may be shown absolute rather than relative to facing. When a player is on the right side, check whether a motion reads mirrored (e.g. 236 showing as ↓↙←) before calling it.
- **"EMPTY"** over a Drive gauge and grey Drive bars mean that player is in **burnout**.
- Banner text on a player's side (COUNTER HIT, PUNISH COUNTER, REVERSAL, THROW ESCAPE, HARD KNOCKDOWN) and the combo hit counter appear on the **attacker's / actor's** side.
- "CA" in place of the SA stock number = Critical Art available.

### Reading the frame meter (when it's on)
The frame meter is the main source of truth for what happened in each exchange. Wiki data is the reference for what the player *could* have done.
- **Numbers first**: read the startup and frame-advantage numbers (e.g. +2, -6) the meter prints. They're large text and reliable. Record them in the event log for each key exchange.
- **Catch the hold**: the meter fills during the exchange and then holds after it ends. Read it from the held frame, not mid-action.
- **Bar shape**: there's one row per player. Use the coloured segments for the broad picture: green = startup, pink = active, blue = recovery, yellow = hit/blockstun, light cyan = Drive Rush, grey/white = invulnerable frames or throw animation, orange = projectile/armour-type frames, purple = other special states. Look at gaps between moves (frame traps vs. gaps the opponent could interrupt) and who recovered first. Match a bar's startup/active/recovery shape against the wiki to identify a move when the inputs are ambiguous (e.g. 9f startup, 2(4)2(10)2 active, 15 recovery = Yasmine 5HP).
- **The meter wraps**: it's a circular buffer, so the newest segment isn't always at the right edge. Use the hold point and the printed text line, not left-to-right order alone.
- **Don't over-count cells**: in compressed or sub-1080p video, neighboring cells blur. Only count individual cells when they're clearly separated. Otherwise, rely on the printed numbers and mark cell counts "approximate".
- **Cross-check**: if a meter reading disagrees with the wiki table (e.g. a different block advantage), trust the meter for that exchange. Spacing, counter-hits, punish counters and patch changes all explain differences. Note the discrepancy briefly.

Keep the number of images you look at proportionate. Scan contact sheets first, and only open dense frames for moments that matter.

## 4. Build an event log
For each round, list the events in timer order, for example:
`R1 93 — the player 2MK→DR blocked; meter shows the player -3; opp 4f jab interrupts → lost 1800`
Log the opponent's decisions too (what they did at plus frames, on the player's wake-up, when he blocked, how they spent Drive and super), not just the player's.
Tag each one with a category: neutral, anti-air, whiff punish, punish (missed or landed), oki/wake-up, pressure, defense, Drive usage, burnout, corner, round-end decision.

For questionable interactions, use the meter's advantage reading when there is one. Otherwise, use the wiki tables. Then use the wiki to answer the follow-ups: was that blocked move punishable, and with which of the player's moves (startup ≤ the opponent's disadvantage)? What fast enough answer was there for a missed punish? Which button would have beaten the opponent's pressure?

## 5. Report
Start with the result (rounds won and lost, and how each round ended). Then:
- **The player's top 3 habits** that cost the most damage or rounds. For each, give the round + timer references, what happened, the frame-data reason, and a specific fix to practice in Training Mode (including a dummy recording setup when that fits).
- **Opponent's habits**: the patterns the opponent leaned on (pressure enders, throw vs. shimmy, wake-up choices, neutral pokes, Drive and super spending), with round + timer references, and how to exploit each one, using the opponent's frame data.
- **What went well**: 1–2 things to keep doing.
- **Resources**: when either player burned out and what the other did with it; Drive Rush usage split into raw drive rush / pressure drive rush cancel / combo drive rush cancel, Drive Impact and Parry usage; super meter left unspent at the end of rounds. Use the resource log for the totals and the Drive economy (Drive lost blocking and to punish counters / Drive Impact matters as much as Drive spent), and add the **Drive efficiency** part from `sf6-drive-efficiency` (what each spend bought vs the free route or vs blocking, parry net Drive, knockdown advantage by recovery type).
- **Matchup notes** for the opponent's character, from the wiki's Matchups and Strategy pages and from this replay.
- **Event log** at the end, grouped by round, so the player can scrub to each moment.

### Coaching rules (from the player)
The player's coaching rules (2MK hit confirms, judging wake-up options, when taking a throw is correct), his structure notes and his theories live in `sf6-coach-shog`. Apply them in every report. In every Full review, include the conditioning check (Structure note #3: what each player taught the other, and whether it was intentional) and the Plant and Harvest read (Theory #2) in the Gameplan section.

### Standard opponent checks (from the player): run these on every replay
1. **Opponent at −4 or worse**: list every exchange where the meter shows the opponent at −4 or worse (the player at +4 or better) **after the player blocked**, with round + timer, the move, the advantage, and whether the player punished. Separate on-block cases from on-hit cases (a −6 during the player's own combo isn't a punish window).
   **Spacing matters (from the player):** a move can be punishable by frame data but not in practice, because pushback leaves the opponent outside the range of the player's fast enough buttons (e.g. a −4 at max range where his 4f lights can't reach). For each window, look at the spacing in the frame (distance between the characters) and compare it with the range of the player's fastest punishes that are quick enough (the wiki's Range column). Label it **Punishable**, **Spacing (out of range)** or **Unclear**, and don't count spacing-limited windows as missed punishes. When one is out of range, say what the player can still do there (e.g. take a turn with a fast button, or walk forward and start pressure).
2. **Unpunished heavy whiffs**: list times the opponent whiffed a heavy normal (or another big-recovery move) and the player didn't punish. On the meter a whiff is the opponent's startup/active/recovery with no hitstun or blockstun on the player's row. Give the move's recovery from the wiki and the player's fastest whiff punish that reaches.
3. **What the opponent does after blocking**: for each time the opponent blocks, read their input history for the next ~30 frames and tally walk back, walk forward, button press (which), jump, Drive Parry, throw/tech, or hold block. Report the tally and what beats the most common choice.

### Missed anti-airs and Drive Rush checks (from the player): run on every replay
For the player being reviewed (the player, or whoever he names):
1. **Missed anti-airs**: every opponent jump that wasn't anti-aired. Find them from the damage panel's Attack Type turning "Overhead/Jump-In" (OCR the panel at ~2 fps with tesseract on an inverted crop) and from scene strips (6 frames, 0.4 s apart) around each one, to confirm the opponent was airborne and not mid-combo. Log round + timer, the situation (neutral range, oki after a hard knockdown, after his own combo, in burnout), what the player was doing, and the result. Note when an anti-air wasn't realistic (a meaty or safe jump on wake-up, no Drive for an OD reversal).
2. **Drive Rush checks**: every time the opponent Drive Rushes (light-cyan segments on the opponent's meter row; flag frames where that row's cyan count jumps, then tile each one about 0.8 s later), log how the player answered (normal and its startup, fireball, Drive Impact, block, block then throw, jump) and whether it **won, lost or was even**, with damage. Skip Drive Rushes that are part of a combo.
3. **Find the patterns**: group both lists by situation and by answer, and say where they're **commonly missed**. Give the faster or safer answer from the wiki.
Meter colour notes: **purple** segments with ~26f startup are **Drive Impact armour**; **light cyan** is Drive Rush.

### Covering the whole match (method)
To find every exchange, not a sample: extract frames at 5 fps, detect the frames where the frame-meter rows change and then hold (diff a mask of the two text/bar rows against the neighbouring frames), and tile each hold as one row (timer + both input histories + the meter), about 12 rows per image. Then build a second set of tiles of the top HUD (health, Drive, damage panel) every 2 s for round flow. tesseract struggles with the meter text over busy backgrounds, so read the tiles visually.
Meter colour notes: **orange** segments are projectile frames (e.g. Yasmine's 22P boomerang shows as 25f startup / 50f total); a long **white/grey** run with a total around 129F is a throw animation.

### Where the player gets hit (from the player): run on every replay
Find **every** time the player takes damage: track his health bar width per frame at 5 fps (pink plus yellow pixels in the bar row; the bar turns yellow at low health) and flag the drops. Ignore drops during super cinematics and round transitions. For each hit, tile the frames about 0.9 s, 0.45 s and 0 s before the drop (timer, both input histories, meter) and classify it on two axes:
- **What the player was doing**: walking (forward/back), pressing a button and getting **counter-hit** (his row shows startup frames cut off by hitstun), **whiffing** and getting **punish-countered** (his move ran into recovery with no stun on her row), an unsafe move blocked and punished, crouching or holding a non-blocking direction, blocking and getting thrown, jumping and getting anti-aired, or pressing on wake-up.
- **Situation** (the player's definitions): **wake-up / oki** = right after either player's knockdown; **pressure** = either player is plus on block; **neutral** = neither player has frame advantage.
Report a table (round + timer, situation, what he was doing, how he got hit, damage), then totals by category and situation, with the biggest-damage entries called out.

### Where the player deals damage: run on every replay
Run the same method on the **opponent's** health bar (its fill is blue on the right; it also turns yellow at low health). Classify each hit the player lands by situation (neutral / pressure / oki) and by how he got it: counter hit, punish (of a blocked unsafe move or a whiff), throw (including throws against Drive Parry), frame trap, wake-up meaty, anti-air, Drive Rush or Drive Impact, super or Critical Art. Report the same table and totals, and compare them with the getting-hit totals (where does he win exchanges vs. lose them).

Cite frame data inline. Say whether each value came from the meter ("meter: -6") or the wiki ("236HK is -X on block per SuperCombo"), and list the wiki pages used under Sources.

### Wording results
Don't write a match result as a round score ("Lost 1-2"): a round count reads like a set score. Say the match was won or lost, and talk about rounds separately ("won 1 round"). For a set of several matches, use games: "lost 2 games to 1".

**Throws vs throw techs (from the player):** keep the intent clear in all wording. A **throw** (or throw attempt) is offensive: The player is trying to throw the opponent. A **throw tech** (or throw tech attempt) is defensive: The player presses throw to avoid being thrown, usually on wake-up or after blocking. Never call a defensive tech a "throw attempt", and never call an offensive throw that whiffed a "tech". The analyzer labels the victim's move as `Throw tech attempt` when the throw started just out of blockstun or on wake-up, and `Throw attempt` otherwise: check the situation before writing it up (an offensive throw that whiffs because the opponent walked out of range is a shimmy on the thrower's offense, not a lost tech guess).

### Player spectra (from the player)
Describe player traits as **spectra between two opposite ends**, scored 1-5 (3 = in between), alongside the archetype in every player read. `tools\spectra.py` computes them from the captures (with `tools\behavior.py` / `beh_cache.json`); cut points are the 20/40/60/80th percentiles of all player-sets in sf6.db, so recalibrate as the pool grows. Each score comes with its evidence line.
- **Temperament (defense):** Impulsive ↔ Mindful. Share of after-block / wake-up choices made on reversal timing (an attack, special, super, throw, jump or parry within 2 frames).
- **Temperament (offense):** Impulsive ↔ Mindful. After their attack is blocked, how often they press again (attack, jump, Drive Rush) within 3 frames of being free.
- **Adaptability:** Inelastic ↔ Elastic. Elastic = adjusts; inelastic = keeps doing the same thing even when it isn't working or hurts them. Measured by how often moves that got them counter-hit, punished or Drive-Rush-checked in earlier games were still used in later games (lights excluded; strengths merged). Needs 2+ games. **Only a losing plan counts as inelastic** (the player, 2026-11-21): a reuse counts when the player lost that game or was behind in the set going into it, or the move kept getting punished (2+ times or 2,000+ damage, weighted 1.5x). In a game they won while not behind, a reused move only counts if it cost 3,500+ damage there. Not changing a winning plan is neutral: "Kept a winning plan" (3/5), not inelastic.
- **Risk tolerance:** Low ↔ High. Risky options per round (wake-up reversals, Drive Impacts, Drive Reversals, raw Drive Rushes at half weight, supers, forward jumps).
- **Raw Drive Rush in risk/reward (from the player):** treat it as fairly low risk: it costs 1 Drive bar, plus a clean or counter hit if it's checked, and it's a generally safe, easy way to start pressure. It only becomes a problem when the opponent keeps checking it and the player doesn't adjust; flag that as a leak, not the Drive Rush itself. Don't weigh character-specific Drive Rush strength for now.
- **Initiative:** Reactive ↔ Proactive. Forward share of neutral movement, averaged with the share of neutral exchanges they start.
- **Composure:** Steady ↔ Tilts. Action rate after taking a 2,000+ combo or losing a round, against the rest of the time.
- **Variety:** Scripted ↔ Mixed. Spread of their after-block and wake-up choices.
- **Resource use:** Conservative ↔ Spendthrift. Drive bars + half a point per super bar + 1 per burnout, per round. Pair it with Drive efficiency: spendthrift and efficient is cashing in, spendthrift and wasteful is a leak.
- **Reviewer's call:** in a Full review, when my read of the video disagrees with a computed score, my call wins: set `spectra_override` `{axis: [score, reason]}` in that player's archetypes row, and the card shows "Reviewer's call (computed X/5)". Quick reviews use the computed scores.
- When a new behaviour-based spectrum looks useful, suggest it to the player rather than adding it silently.

## 5b. Chess or poker? (how to judge a decision)
Some SF6 decisions work like **chess**: there is a stock, best answer, and missing it is a mistake.
- Examples: the optimal punish for a blocked move; spending all resources (Drive, super) when a punish kills; the right combo route from a starter; the on-paper defensive answer in a rare situation.
- Give one answer and say plainly when it was missed.

Most decisions work like **poker**: incomplete information, odds and the opponent's tendencies.
- Neutral spacing, oki and defensive guesses usually have several reasonable options that beat each other, like rock-paper-scissors. Example: poke beats walk-up, walk-up/throw beats block, whiff punish beats poke.
- Don't present one "correct" choice. Give:
  - the options and what each one beats and loses to;
  - which one the opponent's shown tendencies favoured, with evidence;
  - the risk/reward of each (Defense Equation modifiers: HP, Drive, super, position, round/set score).
- A choice that lost can still be a good read if the odds favoured it. Judge the decision, not the outcome ("could you have guessed better?").
- Say which kind each decision is, so tactical misses (chess) aren't mixed up with reads that didn't pay off (poker).

## 6. Be honest about confidence
Without a legible frame meter, sampled frames can't prove one-frame timing. Even with the meter, exact spacing and inputs the display didn't show stay uncertain. Mark these "likely" or "unclear" rather than stating them as fact, and ask the player what he was going for when it matters. Never make up inputs or frame values.

## 6b. Reviewing another player
- **OD specials:** the analyzer marks a special as OD when its start drains at least 15,000 Drive within 12 frames, and relabels it "(OD)". Shared motion names (e.g. Cannon Spike) otherwise all read as one strength, so trust the OD label over the strength label, and check unexpected strength labels against the Drive gauge.
- **Copy of a dashboard from the other player's side:** when the player asks for one (e.g. "obi1-dash"), run the analyzer with that player as the focus player, write the hand-written datasets from their side, and keep it out of the player's tracker and database views.
When the player asks for a review of someone else (e.g. "Sayo, playing Ryu"), analyse from that player's side, keep it out of the player's tracker, and deliver what he asks for (e.g. a dashboard for just those replays). Confirm which in-game name is that player when it isn't obvious.

## 6b. Review levels: Quick, Full, Tournament
Tournament is the level above Full, for tournament sets or whenever the player asks for it. On top of a Full review:
- **Every key exchange checked on video:** sync the capture to the video (round timer first showing 98 gives the offset: video_t = offset + (frame-1)/60). For each moment, make a composite strip (frames from -1.5 s to +0.5 s, the frame meter held at about +0.7 s, both input histories) and read it.
- **Decision audit:** for each major guess (wake-up option, after-block choice, round-start choice, resource spend), give the situation, the options, the on-paper choice from the Defense Equation with its modifiers, and a verdict: Good / Acceptable / Could have guessed better. Do the reward math when it's clear (e.g. a reversal that wins 800 and loses about 3,700 has to work more than 4 times in 5).
- **Adaptation timeline:** round by round, what each player changed and what they didn't.
- **Between games:** a 3-4 point checklist the player could have told themselves after each game.
- **Rematch prep:** a scouting report on the opponent and a gameplan in numbered steps.
- **Longer training plan:** several weeks, with drills, minutes and something measurable (e.g. wake-up reversals per game).
- Store these as the `tournament` dataset (set_id, part, order, title, body, evidence, verdict) in review_docs and show them as a "Tournament review" section on the Set review tab.
- Set the review label to Tournament.

## 7. Tracking across replays: the SF6 Replay Tracker
The player keeps a Claude Sheet, **SF6 Replay Tracker** (link in shotokan.json, if the player has one). After every analysis, append the replay to it through the Claude Docs connector (read topic.sheets first, then readSheets and read each tab's last rows before writing; append below the last record, never overwrite).
- **Replay ID**: the SF6 replay ID (e.g. `8YAM8FTYB`), shown on the replay's details screen in-game. Use it on every tab and in "Seen in". If the player sends a recording without one, ask for it; only if he doesn't have it, use the date analysed + number.
- **Matches**: Replay, My char, Opp char, Opponent, Result, Opp MR, My MR, Coverage ("Full" or "Sampled"), Notes (one line per round), Rounds won, Rounds lost. Result is just **Won** or **Lost**; round counts go only in their own columns.
- **Habits**: Player (the player / Opponent), Replay ("All" for the player's, the replay ID for an opponent's), Category (Defense, Neutral, Offense, Oki, Round closing, Resources, Execution, Strength), Habit, Seen in (round + timer refs, with replay IDs for the player's), Times, What to do. The player's habits are global: when a new replay shows one that already exists, add its refs to Seen in and update Times instead of adding a row. Opponent habits are per replay.
- **Anti-airs** and **Drive Rush checks**: if the tracker has these tabs, add one row per entry. If it doesn't, offer to add them before writing.
- **Hits Taken**: one row per hit. Situation = Neutral / Pressure / Oki / Unclear. "What I was doing" uses only these labels so the Summary counts work: Pressed button, Walking, Blocking, Whiffed button, Unsafe special, Crouching, Jumping, Wake-up press, Throw tech, Unclear. Put "Thrown" in "How I got hit" for throws. For a KO, put the damage if the damage panel shows it, and "KO" in Notes.
- **Hits Dealt**: one row per hit. Situation = Neutral / Pressure / Oki / Punish.
- **Punish Windows**: every opponent −4 or worse on block, with Punished? = Yes / No, and in Notes whether it was **in range** or **spacing** (out of range of a fast enough punish). Only an in-range "No" is a missed punish.
- **Matchup Notes**: add new punishes to learn, habits, throw patterns and dangers for the opponent's character. Don't duplicate an existing row: update its "Seen in" with the new replay ID instead. Leave Status alone unless the player asks, except to suggest in the report when a "To learn" punish was landed.
- **Summary** fills itself from Matches (one row per replay, up to 16; extend rows 6–21 by copying the last formula row if needed).
Then refresh the **SF6 Replay Tracker dashboard** (link in shotokan.json, if the player has one). It can't read the sheet live, so it shows copies: re-read each changed tab, upload it with upload_asset as JSON shaped `{"value": {"rows": {"1": [header...], "2": [...]}}}`, and update that dataset's `source.url` and `updated` (datasets: matches, hits_taken, hits_dealt, punish_windows, matchup_notes, habits).
- **Database tabs** (Set Metrics, Player Reads, Opponents, Character Matchups): these are generated from sf6.db, not appended by hand. After each ingest, run `python sf6db_export.py sf6.db OUTDIR` (writes set_metrics.json, player_reads.json, opponents.json, char_matchups.json as {header, rows}). In the sheet, read each tab's used range, clear rows 2 and below, and write the new rows from A2 (keep text such as `'2-0` starting with an apostrophe so it stays text); keep long text columns wrapped and fit the rest. Then upload each tab to the dashboard as `{"value": {"rows": {"1": header, "2": [...]}}}` (strip the leading apostrophes) and update `source.url` and `updated` on datasets set_metrics, player_reads, opponents and char_matchups. The dashboard's "Long-term: set by set" charts and the Opponents, Character Matchups and Player Reads tables read these. If a tab nears the sheet's 500k-cell limit, keep only summaries or recent rows in the sheet; the database keeps everything.
In the report, compare this replay with earlier ones from the Summary tab (e.g. hits taken while pressing buttons going up or down) and list any "To learn" punishes that came up.