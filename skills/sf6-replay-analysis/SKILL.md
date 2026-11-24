---
name: "sf6-replay-analysis"
description: "Analyze Street Fighter 6 replays from REFramework capture files (when present) and recordings (video or screenshots): read the frame meter and HUD, log key moments by round and round timer, check against SuperCombo frame data, report both players' habits and fixes, and log the player's replays to his SF6 Replay Tracker sheet."
---

# SF6 replay analysis

> **Installed skills only.** This plugin ships the analysis, prediction, dashboard, glossary, character notes, Drive efficiency, Juzzy and Maj skills, and .shog's coaching rules as an example. Other coaching skills named in this text (E.X. Dojo, Coosco, DoctaAfrikan) aren't included: load them only if the player has installed them, otherwise skip those checks.

**Player config.** Read `<coaching folder>\shotokan.json` first (written by shotokan-setup): The player's name, CFN ID, other names and main character. Wherever this skill says "the player", it means that person; their CFN ID is the focus player for ingest and comparisons.


The player submits recorded SF6 replays (OBS or console capture, sometimes paused screenshots) and says which character they played. Their main character is in shotokan.json, but they may play others, so always use the character named for that replay.

**Reference files.** The detail lives in this skill's `references/` folder (`${CLAUDE_PLUGIN_ROOT}/skills/sf6-replay-analysis/references/`). Read a file when the step below names it, before doing that step, not from memory; the rules in this file always apply.

**Guideline skills to load every review.** Before analysing any replay, load each of these skills with the Skill tool and apply them alongside this one. What each one checks in a review: `references/guideline-checks.md` (read it at the start of each review).

`sf6-coach-shog`, `sf6-character-notes`, `sf6-footsies-handbook-maj`, `sf6-fgc-glossary` (when needed), `sf6-drive-efficiency`.

- `sf6-coach-shog`: The player's own coaching rules, which override the other skills where they conflict.

When the player adds another guideline skill, add it to this list.

## Review depth: Full Review vs Quick Review
The player picks the depth by asking for a **"Full Review"** or a **"Quick Review"**. If he doesn't say, default per set: **Quick for sets the player won, Full for sets he lost** (decide once the analyzer gives the result, and say which each set got). This applies when reviewing someone else too, from that player's side.
- **Quick Review (automatic):** run the analyzer, then build every per-set card (habits, story, reads, punishes, fixes, training) from the capture stats with `tools\ranked_build.py` (and `tools\ranked_overview.py` for a cross-set overview). Check video only for rows that look wrong. Fast and consistent across sets, but no intent, no hand-picked turning points, and player reads come from simple thresholds.
- **Full Review (hand-written):** run the analyzer, then go through report.md exchange by exchange, check story moments and surprising rows against the video, correct analyzer mistakes, and write the story, habits, player reads, punishes and fixes by hand using the guideline skills above.
- Tag each set's `sets` row with `review: "Full"` or `review: "Quick"` and show it in the dashboard subtitle, so mixed dashboards are clear.
- Open question (the player, 2026-11-18): which parts of a review benefit from hand-written notes and which don't. Revisit with him before changing either mode.

## 0. Capture files first (REFramework)
The player records replays in SF6 with REFramework scripts: `capture_replay.lua` (window "Replay Capture v3.3") autosaves `<ReplayID>.json` when a replay ends, including each player's CFN ID (`p1_cfn_id`/`p2_cfn_id`, Buckler `short_id`; .shog = 1307078698), MR and LP when the replay data carries them, and `export_moves.lua` ("Move Export v4") makes `sf6_moves/<id>_<Name>.json` and `enums.json`. If a capture's CFN ID is missing, check its `player_fields` list for where the ID lives and fix the script. Copies of all tools live in `<coaching folder>\tools\`.
- **Capture data in detail** (resource log, per-combo fields, parries, report.md sections, character data, rank labels, decoding rules for raw files): `references/capture-data.md`. Read it before interpreting resources, parries or per-combo fields, and before reading a raw capture.
- **Storage:** every replay's capture and video `<ReplayID>.mp4` go in `<coaching folder>\replays\`. After a replay is recorded, move the capture there from the game's `reframework\data` folder and the video there from `C:\Users\seanh\Videos`, then look for both files in that folder. Captures are stored **gzip-compressed as `<ReplayID>.json.gz`** (about 40x smaller): after analysis, `gzip -k` the .json, check the .gz decompresses to the same bytes, then delete the .json. The analyzer and sf6db.py read .json and .json.gz alike. Each review gets its own folder, `<coaching folder>\reviews\<YYYY-MM>\<date>_<type>_<opponent>\` (type: ranked, training, tournament or review; e.g. `2026-11-23_ranked_DaFeetLee`), holding prediction.json, meta.json, report.md, the summary and its `review\` outputs; one-off analyses go in `<coaching folder>\work\`. Dashboards and build files can be regenerated from sf6.db, so old ones can be cleared; `enums.json` and `sf6_moves\` are not replays.
- **Look for `<ReplayID>.json`** next to the video (or where the player says). When it exists, it is the source of truth for hits, damage, hit kinds, anti-airs, burnouts, perfect parries, throw techs, Drive Reversals, Drive Rush counts, inputs and timings. **Use video only for story moments**: spacing, intent, what a player was going for, anything the capture doesn't record.
- **History database**: `<coaching folder>\history\sf6.db` (SQLite) is the long-term record of every reviewed set: players (CFN ID + name history), sets, games, hits, events, timings, per-set stats (long format, `set_stats`), player reads, habits and matchup notes, with views `v_sets`, `v_player_matchups` (me vs an opponent) and `v_char_matchups` (my character vs theirs). **After every review, ingest the set** with `tools\sf6db.py ingest DB OUTDIR META.json` (META: set_key, focus, played_date, ranked, review Full/Quick, captures, reads, habits, char_names; see the docstring). Re-ingesting a set replaces it. META also needs `captures_local` (each replay's capture path on the machine running the ingest) and `focus_mr` as a list. The ingest computes both players' eight spectra (spectra table and review_docs archetypes), adding the set's replays to `beh_cache.json` first; `--no-spectra` skips it, and `tools\spectra_backfill.py DB` fills any set without spectra. To compare players' decisions (where they press, which buttons, what it leads to), run `tools\decision_presses.py DB --player NAME[,ALIAS] ... [--char C]`. Match opponents by CFN ID when the capture has it, else by name. Before reviewing a set, query the database for earlier sets against the same opponent and the same character matchup, and say what changed. The Replay Tracker sheet and dashboards are views of it.
- **After every ingest, refresh the long-term views** (see section 7): run `tools\sf6db_export.py DB OUTDIR` and rewrite the sheet's Set Metrics, Player Reads, Opponents and Character Matchups tabs from its output, then re-upload those four tabs to the tracker dashboard.
- **After the ingest**: for a **Quick** review, also run `tools\quick_dashboard_from_db.py DB OUTDIR --write-reads` (on a copy of the database, then copy it back) so its player reads and habits are written to sf6.db; ignore the dashboard files it writes. For a **Full** review, pass `review_docs` in META: the hand-written story, story_games, habits, archetypes, fixes, training, findings, punish and sets rows, plus `set_gameplan` (each player's gameplan, mid-set adjustments, what worked, and how each should adjust) and `prediction` (the graded prediction). They're the review's record and are kept across re-ingests. The quick-dashboard artifact is retired: don't pass `dash` or upload dashboard data (how it was built: `docs/archive/quick-dashboard.md` in the tools repo).
- **Prediction first (always)**: before opening any capture, analyzer output or video of a set, write the pre-set prediction with `replay-review-prediction`, even when the player doesn't ask for one; grade it after the review and store it in `review_docs` as `prediction`.
- **Workflow**: stage the capture files and `tools\analyze_capture.py`, then run `python3 analyze_capture.py OUTDIR <focus player name> <FT2|FT3|FT5> <game1.json> <game2.json> ...` (games in set order). It writes `sets/games/hits/events/timings.json` in the sf6-review-dashboard schema, `resources.json` and `parries.json` (below), plus `report.md`.
- **Timestamps**: use round + `round_timer` (written "@" on dashboards, e.g. G1 R2 @77).
- **Player rank labels**: below Master, the league name only ("Diamond", not "Diamond 3"); Master with an MR, "<MR> MR"; Master with none, "MR unknown"; LP -1, "Unranked". Use `tools\rank.py`; league thresholds and older captures: `references/capture-data.md`. Keep the LP and MR themselves in the database.
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
Read `references/recording-from-ids.md` and follow it.

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

## 3-4. Games with no capture: video and event log
Only when a game has no capture file: read `references/video-processing.md` and follow it (video passes, event log).

## 5. Report
Start with the result (rounds won and lost, and how each round ended). Then:
- **The player's top 3 habits** that cost the most damage or rounds. For each, give the round + timer references, what happened, the frame-data reason, and a specific fix to practice in Training Mode (including a dummy recording setup when that fits).
- **Opponent's habits**: the patterns the opponent leaned on (pressure enders, throw vs. shimmy, wake-up choices, neutral pokes, Drive and super spending), with round + timer references, and how to exploit each one, using the opponent's frame data.
- **What went well**: 1–2 things to keep doing.
- **Resources**: when either player burned out and what the other did with it; Drive Rush usage split into raw drive rush / pressure drive rush cancel / combo drive rush cancel, Drive Impact and Parry usage; super meter left unspent at the end of rounds. Use the resource log for the totals and the Drive economy (Drive lost blocking and to punish counters / Drive Impact matters as much as Drive spent), and add the **Drive efficiency** part from `sf6-drive-efficiency` (what each spend bought vs the free route or vs blocking, parry net Drive, knockdown advantage by recovery type).
- **Matchup notes** for the opponent's character, from the wiki's Matchups and Strategy pages and from this replay.
- **Event log** at the end, grouped by round, so the player can scrub to each moment.

### Checks to run on every replay
Run these on every review; the method and table format for each are in `references/report-checks.md` (read it before writing these parts of the report): Standard opponent checks; Missed anti-airs and Drive Rush checks; Covering the whole match; Where the player gets hit; Where the player deals damage.
Cite frame data inline, and say whether each value came from the meter or the wiki.

### Coaching rules (from the player)
The player's coaching rules (2MK hit confirms, judging wake-up options, when taking a throw is correct), his structure notes and his theories live in `sf6-coach-shog`. Apply them in every report. In every Full review, include the conditioning check (Structure note #3: what each player taught the other, and whether it was intentional) and the Plant and Harvest read (Theory #2) in the Gameplan section.

### Wording results
Don't write a match result as a round score ("Lost 1-2"): a round count reads like a set score. Say the match was won or lost, and talk about rounds separately ("won 1 round"). For a set of several matches, use games: "lost 2 games to 1".

**Throws vs throw techs (from the player):** keep the intent clear in all wording. A **throw** (or throw attempt) is offensive: The player is trying to throw the opponent. A **throw tech** (or throw tech attempt) is defensive: The player presses throw to avoid being thrown, usually on wake-up or after blocking. Never call a defensive tech a "throw attempt", and never call an offensive throw that whiffed a "tech". The analyzer labels the victim's move as `Throw tech attempt` when the throw started just out of blockstun or on wake-up, and `Throw attempt` otherwise: check the situation before writing it up (an offensive throw that whiffs because the opponent walked out of range is a shimmy on the thrower's offense, not a lost tech guess).

### Player spectra
Every player read includes the eight spectra, scored 1-5: Temperament (defense), Temperament (offense), Adaptability, Risk tolerance, Initiative, Composure, Variety, Resource use. Definitions, how each is computed, the raw drive rush risk rule and the reviewer's-call override: `references/player-spectra.md`.

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
The player keeps a Claude Sheet, **SF6 Replay Tracker** (link in shotokan.json, if the player has one). What goes in each tab, the dashboard refresh and the generated database tabs: `references/tracking.md`. Read it before updating the tracker or its dashboard.
