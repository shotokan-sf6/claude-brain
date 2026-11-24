---
name: "sf6-review-dashboard"
description: "Format for SF6 replay-review dashboards (like \"splash-test\" and \"tuning skills\"): Data-type artifact sections, dataset schemas, page CSS/helpers, and local copies + standalone HTML. Use whenever an SF6 review goes into a dashboard."
---

# SF6 review dashboard format

> **Installed skills only.** This plugin ships the analysis, prediction, dashboard, glossary, character notes, Drive efficiency, Juzzy and Maj skills, and .shog's coaching rules as an example. Other coaching skills named in this text (E.X. Dojo, Coosco, DoctaAfrikan) aren't included: load them only if the player has installed them, otherwise skip those checks.


Use this when an SF6 replay review (sf6-replay-analysis) is put into a dashboard. Keep this layout unless the player asks for changes. If he edits a dashboard's formatting by hand, offer to update this skill from his version.

## 1. Terms (use these everywhere: page text, dataset names, summaries)
- **Round**: one life bar. A **game** is one replay (one replay ID), made of 2 or 3 rounds.
- **Set**: a group of games between the same two players. Formats:
  - **FT2** (first to 2 game wins), also called **BO3** (best of 3). This is a ranked set.
  - **FT3** (first to 3), also called **BO5**.
  - **FT5** (first to 5), also called **BO9**. This one is rarer.
- **Grouping games into sets:**
  - Use the sets the player specifies.
  - If he submits games together and both players are the same in all of them, assume they form a set.
  - If the grouping is unclear, ask before building. Examples: more games than one set's format allows, or a score that doesn't fit the format.
  - A dashboard can hold several sets. Group everything by set, then by game. The page shows one set at a time, chosen with the "Show set" picker (section 5).
- Never call a game a "set", and never call a round a "game".
- Score notation:
  - **Game score**: rounds won within one game ("2-1", P1 first).
  - **Set score**: games won within a set ("3-2", P1 first).

## 2. Artifact and data
- Make the dashboard from the **Data** artifact type (list_types → create_from_type), titled as the player names it (e.g. the folder name). One dashboard per review.
- All data is in **attached JSON files** (upload_asset), declared as `datasets/<id>` with:
  - `source: {kind:"file", url, name, format:"json"}`
  - `fixed: true`
  - `updated: {at, by:"Claude"}`
  - When a file changes, re-upload it, then `update` the dataset's `source.url` and `updated`.
- Refer to players by their in-game names.
  - P1 is the player in focus: The player, or whoever the player asks to review. P2 is the opponent.
  - Column names use lower-case player prefixes (`<p1>_…`, `<p2>_…`).
- Every dataset row has a unique id column, which the page uses as `data-row-key` (`archetypes` rows use `arch_id`).
- Every row in every dataset has `set_id` (archetypes, habits, punish, findings, fixes and training too), so the page can show one set at a time. When adding a set to an existing dashboard, keep the old rows and append the new set's rows with new ids.
- **Don't track total damage dealt.** No damage-dealt tiles, per-game damage charts or damage totals. Damage only appears as the *share* behind situations and lenses, and per hit in the hidden hits table.
- **Rounds are light.** Record each game's round score and who won each round. Don't build a rounds table or a "who wins which round" chart.

## 3. Datasets (ids, columns)
| id | one row per | columns |
|---|---|---|
| `sets` | set | `set_id` ("Set 1"), `order`, `format` (FT2/FT3/FT5), `games` (replay IDs in order), `<p1>_games`, `<p2>_games`, `p1`, `p1_char`, `p2`, `p2_char`, `p1_games`, `p2_games` (generic copies the page reads), `sub` (header line: replays, control types, MR), `winner`, `progression` (set score after each game, e.g. "0-1, 1-1, 1-2, 2-2, 3-2"), `max_deficit_overcome` (e.g. "P1 from 0-2", or null), `note` |
| `games` | game (replay) | `game_id` (replay ID), `set_id`, `game_no`, `winner`, `round_score` (P1 first), `round_winners` (e.g. "P2, P1, P1"), `set_score_after` |
| `hits` | damaging hit or combo | `hit_id`, `set_id`, `game_id`, `round`, `video_time_s`, `round_timer` (shown on the page as "@", e.g. @77), `attacker`, `victim`, `damage`, `starter` (`starter_approx` when read from video), `hits_in_combo`, `victim_move` (from a capture file), `first_hit_type` (High/Low/Overhead/Throw/Jump-in/unread), `hit_kind` (clean hit / counter hit / punish counter / throw / reversal), `anti_air` (true/false), `situation` (neutral / pressure / oki / punish / defense), `lens` (what the victim was doing, see section 4), and from captures `drive_spent`, `super_spent`, `drive_gained`, `drive_damage`, `knockdown`, `kd_adv`, `corner_dist` (see sf6-replay-analysis, "Per combo") |
| `events` | non-damage event | `event_id`, `set_id`, `game_id`, `round`, `video_time_s`, `player`, `type` (perfect parry / burnout), `note` |
| `archetypes` | player | `player`, `character` (incl. Modern/Classic), `archetype`, `lean`, `confidence`, `evidence`, `doc_risk_tolerance`, `doc_temperament`, `counter_note`, `adaptation` (how they adapted), `spectra` (list of eight `{key, axis, left, right, score, label, evidence}`; a reviewer override says "Reviewer's call (computed X/5)" in its evidence) |
| `resources` | player per round | `res_id`, `set_id`, `game_id`, `game_no`, `round`, `player`, `drive_rush`, `drive_parry`, `drive_impact`, `drive_reversal`, `od_specials`, `drive_other`, `drive_total`, `super_bars`, `supers` ("SA2 (2) @80; ..."), `burnouts`, `drive_end`, `super_end`, `gain_hit`, `gain_block`, `parry_regain`, `loss_block`, `loss_hit`, `loss_hit_drive_impact`, `loss_hit_punish_counter` (all in bars) |
| `parries` | Drive Parry | `parry_id`, `set_id`, `game_id`, `game_no`, `round`, `round_timer`, `player`, `frames`, `drive_before`, `cost`, `hits_parried`, `regained`, `net`, `perfect`, `next` (nothing / raw drive rush / punished them / hit / thrown) |
| `habits` | habit | `habit_id`, `player`, `kind` (Strength / Leak / Pattern), `area` (Neutral/Offense/Defense/Drive/Anti-air…), `habit`, `seen` (game, round, timer list), `times`, `fix` (for a Strength, "keep doing" advice), `origin` (which check or skill found it), `confidence` |
| `story_games` | game | `game_id`, `set_id`, `game_no`, `result` (winner + round score), `set_score_after`, `summary` (3-5 sentences), `turning_point` |
| `story` | finding in the Story of the Set | see section 6 |
| `punish` | punish | `punish_id`, `punisher`, `what_was_punished`, `example`, `punish_used`, `damage`, `verdict` (log missed punishes with punisher "none (missed)") |
| `findings` | skill check | `finding_id`, `skill`, `category`, `finding`, `evidence`, `confidence`, `applies_to` (player or both) |
| `fixes` | fix | `fix_id`, `player`, `rank`, `fix`, `drill`, `why` |
| `training` | block | `block_id`, `block` (Primary 50% / Secondary 25% / Free play 25%), `focus`, `drills`, `minutes` |

Calcs on the page (not files), all computed from `hits` and `events`:
- `kpis`: one row per set (with `set_id`). For each player:
  - `burnouts`: count of `events` with type burnout.
  - `anti_airs`: hits with `anti_air` true, counted on the attacker.
  - `counter_hits` and `punish_counters`: counted separately, never combined.
  - `perfect_parries`: count of `events` with type perfect parry.
- `sit_pct`: per set, for each victim and situation, the % of that player's damage taken, plus hits.
- `lens_pct`: per set, P1's damage taken by `lens`, as % plus hits.
- `kind_counts`: per set, hits landed by each attacker per `hit_kind`.
- `res_totals`: per set and player, Drive bars by spending category, burnouts and rounds (from `resources`).
- `sup_totals`: per set and player, super bars and counts by level (`lv1`/`lv2`/`lv3`, `n1`/`n2`/`n3`, read from the `L<level>` prefix of each entry in `supers`), extended supers (`ext`) and super bars left unspent at round ends (`left`).
- `ov_econ` (Overview): Drive per round for P1 and the opponent (spent, lost blocking, lost getting hit, gained, parry net, burnouts), one row per set, or per game when there are fewer than 3 sets.
- `econ`: per set and player, Drive out (`spent` = drive_total, `loss_block`, `loss_hit`) and in (`gain_hit`, `gain_block`, `parry_regain`), plus Drive lost to punish counters and Drive Impact, burnouts and rounds (from `resources`).
- `parry_sum`: per set and player, parries, hits parried, cost, regained, net, perfect, and counts of each `next` outcome (from `parries`).

How to read the counts:
- **Burnout**: each time a player's Drive gauge empties. A burnout that lasts into the next round counts once. **A lethal burnout doesn't count** (the player, 2026-11-22): when the gauge empties inside the player's own combo and that combo kills (the opponent stays in hitstun until their HP hits 0, same round), e.g. a combo spending all Drive into SA3 for the kill, the analyzer logs it as event type `lethal burnout`, which no burnout count, tile, spectrum or advice includes.
- **Perfect parry**: read from the on-screen Perfect Parry effect and label, and the frame meter freeze. If a parry can't be read for certain, log it with note "approximate".
- **Anti-air**: a hit that lands on an airborne opponent who is jumping in, whatever the button (normal, DP, air-to-air). Don't count juggles.
- **With capture files** (sf6-replay-analysis section 0), `analyze_capture.py` writes `sets`, `games`, `hits` and `events` directly: use them as is, and read burnouts, perfect parries and anti-airs from the data. Don't call anti-airs from sampled video frames alone: they misread ground counter-hits as anti-airs.

## 4. Lens: what P1 was doing when hit
Give every hit P1 takes one `lens` group. The groups come from the Stagger Pressure, Defense Equation and Reactions skills. Use the same names every time so dashboards can be compared:
- **Challenging pressure**: pressed or mashed during the opponent's blockstring or pressure (not after a knockdown), or got frame-trapped or stagger-checked.
- **Challenging okizeme**: pressed on wake-up into the opponent's oki and got hit.
- **Counter-hit at mid range**: pressed a poke or button in neutral and got counter-hit during its startup.
- **Whiff punished**: a poke or button whiffed in neutral and got punish-countered in its recovery. Kept apart from counter hits (pressing into their button) and from unsafe moves (blocked, then punished).
- **Walked in**: walked into a poke, Drive Rush or spacing trap.
- **Teched a throw**: got shimmied or delay-strike-checked.
- **Blocking, opened up**: was holding block and lost the mixup (low/overhead/throw/cross-up).
- **Jumped**: got anti-aired or air-to-aired.
- **Jumped in on (no anti-air)**: the opponent's jump-in landed.
- **Own offense beaten by a reversal**: P1 was attacking (pressure or oki) and the opponent's reversal hit.
- **Drive Rush / Impact checked**: own Drive Rush or Drive Impact got checked, punished or impacted back.
- **Unsafe move punished**: own blocked move was punished in its recovery (includes blocked reversals). Only when the move that got hit is the one that was blocked.
- **Pressed after turn ended**: own move was blocked and recovered, then P1 started a new button once the opponent was free again and got hit. A turn-taking problem, not an unsafe move.
- **Open question (the player, 2026-11-21): button sequencing.** Some "pressed after turn ended" hits are part of a deliberate sequence, a poker situation rather than a plain leak. Example: 2HP > 2HP loses to a 4f jab after the first 2HP, but conditions the opponent so that 2HP > jab (counter hit) > 2MP works. How button sequencing interacts with frame traps, spacing traps and other habits is still to be worked out with the player; until then, flag repeated sequences rather than calling every one a mistake.
- **Unclear / super**: can't be read (e.g. a super cinematic).

Older dashboards and database rows from before 21 November 2026 use the old names "Pressed at mid range" (now split into Counter-hit at mid range and Whiff punished) and "Pressed in their pressure / on wake-up" (now Challenging pressure and Challenging okizeme).

**Weight advice by raw damage, not just share.** Show the lens as a % of damage taken, but rank and word the advice by how much damage it actually cost and in which rounds. 50% of 2,000 damage in a round the player won matters far less than 30% of a full life bar in a lost round. When a lens is a big share but small in raw damage (or came mostly in won rounds), say so and rank it lower; give damage per round or per lost round next to the % where it helps.
## 5. Page layout (top to bottom)
1. **Header** `h1` (`h_title`): `<P1> (<character>) - <games won> vs <P2> (<character>) - <games won>`, for the chosen set.
   - Under it, a `.st-sub` line (`h_sub`): the set's `sub` (`Replays <id>, <id>, …`, control types, MR), then its format and set score.
   - Then the **set picker**: `<div class="st-filter"><label for="set-pick">Show set</label><select id="set-pick" data-draw="set_pick" data-source="sets"></select></div>`.
     - One option per set ("Set 2: <P1> vs <P2> (<character>), FT2"); the newest set is selected by default. Keep it even when there is only one set.
     - Changing it redraws every section (`ST.REDRAW`). Every section below shows only the chosen set: P2's name, the legends, the KPI labels, the P2 habits card label and the "Show hits by" options all come from that set's row in `sets`.
   - Every `<select>` uses the `.st select` CSS in section 8. Unstyled selects can open as white text on a white list, so never leave one unstyled.
   - Every `<select>` (set picker, "Show hits by") uses the `.st select` CSS in section 8. Unstyled selects open as white text on a white list in some themes, so never leave one unstyled.
2. **Where the damage came from** (`.st-grid2`, two cards):
   - Left: **by situation**. `ST.hbars` of `sit_pct`, with each player's bars side by side and values in %.
   - Right: **Where the damage you took came from**. `ST.hbars` of `lens_pct` (P1 only), labelled "% (hits)".
   - Under the cards, a note defining the situations (pressure = blockstring or tick that wasn't a knockdown; oki = after a knockdown) and saying percentages are of each player's total damage taken.
3. **KPI tiles** (`.st-tiles`), each showing "P1 / P2" in that order: Burnouts · Anti-airs · Counter hits · Punish counters · Perfect parries.
4. **Hits landed by kind**: legend plus a grouped bar chart of `kind_counts`.
4b. **Drive and super spending**: a note that Drive and super are separate gauges, then two full-width cards (one above the other, not side by side, so the lines under the bars fit). Drive card: label (bars; a full gauge is 6; chip and Drive lost to hits aren't spending), a five-colour legend (Drive Rush `#2f9e6b`, Drive Parry `#2f6fd6`, Drive Impact `#d9622b`, Drive Reversal `#8e5bd6`, OD specials `#c9a227`) and one stacked bar per player from `res_totals` with "X Drive bars, N burnouts over R rounds". Super card: label (bars; a full gauge is 3; an extended super counts at its own level), legend (Level 1 `#2f6fd6`, Level 2 `#c9a227`, Level 3 / Critical Art `#d6336c`) and one stacked bar per player from `sup_totals` with "N supers (a Level 1, b Level 2, c Level 3 / CA; e extended), X bars; Y bars left unspent at round ends". Both use `ST.stackBars`. Under it a closed `<details>` "Spending by round" with the `resources` table (game, round, player, each category, totals, supers used, burnouts, Drive / super left).
4c. **Drive economy**: a note on what Out and In mean (passive regen not shown), then a card with the legend (Spent `#2f9e6b`, Lost blocking `#d9622b`, Lost getting hit `#d6336c`, Gained landing hits `#2f6fd6`, Gained on block `#8e5bd6`, Gained from parries `#c9a227`) and, per player, an Out bar and an In bar on the same scale with totals, plus a line "Lost X to punish counters and Y to Drive Impact hits; N burnouts over R rounds" (`econ`). Then `h3` **Drive Parry** with the `parry_sum` table and a closed `<details>` "Every parry" (`parries` table); and a closed `<details>` "Combos that spent Drive or super, and what they bought" (hits with `drive_spent` or `super_spent` > 0: game, round, @, attacker, starter, damage, Drive spent, super spent, Drive back, their Drive lost, knockdown, to corner). Knockdown advantage (`kd_adv`) stays off the page until the player adds his oki thresholds.
   On the **Overview** tab, before "What to work on next": **Drive economy over time**, a note naming the unit (set by set, or game by game with fewer than 3 sets), a line chart of P1's spent / lost blocking / lost getting hit / gained per round (`ov_econ`, colours as in 4c, gained `#2f6fd6`), and a closed `<details>` table with both players' columns. Add its draws to `ST.OVDRAW`.
5. **Player reads**: one card per player with Archetype (lean, confidence), then the eight spectra (`ST.spectra`: axis name, left label, five dots with the score filled, right label, then "label: evidence"), then How they adapted, Evidence and What it costs / how to beat it. Older rows without `spectra` fall back to Risk tolerance and Temperament.
6. **Habits**: two columns (`.st-two`), one card per player, filled by `ST.habits`. Each item shows:
   - a tag "Kind · Area" (green for Strength, red for Leak, plain for Pattern), then the habit;
   - "Seen: … (N×)";
   - the fix, in a green-bordered `.st-try` box;
   - a muted "Source: …".
7. **Story of the Set**: section 6. Make one story per set, in set order.
8. **Punishes** table.
9. **Fixes and drills**: info cards (`.st-cards`), one per fix, in rank order. Each card has:
   - "#rank · player" label;
   - the fix as the heading;
   - the drill in a `.st-try` box;
   - Why.
10. **Suggested training routine for <P1>**: one card listing the `training` blocks, each block with its focus, drills and minutes.
11. **Findings by skill**: closed `<details>`, summary "Findings by skill (N)". Cards with the label "skill · category · applies_to · confidence", then the finding and its evidence.
12. **All hits**: closed `<details>`, summary "All hits (N)". Inside: the "Show hits by" select (Both / P1 / P2) and the hits table.
13. **How these numbers were made**: closed `<details id="method">`. Cover:
    - the health-bar reading rate;
    - OCR of the damage panel and side labels;
    - how burnouts, perfect parries and anti-airs were read;
    - the frame-data source and date;
    - which parts come from watching frames.
    - When capture files were used, say so: hits, damage, hit kinds, anti-airs, burnouts, perfect parries and timings are measured from the REFramework capture; only story moments and intent come from video. Add "@ = round timer."

Not shown for now:
- the matchup pop quiz (Coach-DoctaAfrikan's method). It may still go in the summary md.
- total damage, and round-by-round tables or charts.

Colors: P1 = `dash.colors[0]`, P2 = `dash.colors[1]` everywhere (charts and legend swatches). Winner text: `.st-ok` if P1 won, `.st-bad` if P2 won.

## 6. Story of the Set (the backbone of the review)
The story explains how the skills' findings played out in the games: what worked, what cost games, and what changed from game to game. Every finding sits in one **category**:

| Category | Default skills (a finding can override its skill's default) |
|---|---|
| **Neutral** | footsies-101, spacing-traps, using-pokes, air-footsies, how-to-jump, dps-and-divekicks, dealing-with-drive-rush, reactions |
| **Offense** | jab-strings, stagger-pressure, improving-shimmy, delayed-throw-offense, drive-rush-blockstrings, hit-confirms, simple-gameplan, structuring-offense-defense (offense half) |
| **Defense** | the-defense-equation, defense-offense-101, delay-option-selects, drive-reversal, drive-parry-mindgames, back-recovery, structuring-offense-defense (defense half) |
| **Player reads / profile** | player-archetypes, beating-unstable-players, holistic-lens, consistency, matchups-gameplans, coach-doctaafrikan (or that finding's own category) |

If a skill gains a category tag later, use the tag instead of this table.

**`story` dataset columns:**
- `story_id`
- `set_id`
- `scope`: "set", or the game_id
- `category`
- `polarity`:
  - Worked well
  - To improve
  - Change: a new pattern, or an improvement or regression in an existing one
- `change`: New / Improved / Regressed / null
- `rank`: importance within its scope, 1 = most important
- `headline`: one line
- `detail`: what happened and why it mattered, with frame data where relevant
- `evidence`: game, round and timer
- `skills`: which skills drove it, comma-separated
- `try_this`: for To improve and Regressed; optional otherwise
- `confidence`: High / Medium / Low

**Layout** (drawn by `ST.story`, one block per set):
1. **Set overview card** (scope "set"):
   - Heading: "<set_id> · <format> · <winner> <set score>".
   - The `progression` line, plus `max_deficit_overcome` when there is one (e.g. "came back from 0-2").
   - Two columns: **Top 3 highs** (Worked well, by rank) and **Top 3 lows** (To improve, by rank). Prefer High-confidence findings; use Medium ones to fill.
   - Then the rest of the set-level findings, grouped under the four category headings.
   - The set overview is shorter and broader than the game cards.
2. **Game cards** in order. Each has:
   - Heading: "Game N · <replay id> · <winner> <round score> · set <set_score_after>".
   - The summary and turning point from `story_games`.
   - The game's findings grouped by category, with more detail than the set overview.
   - Change rows get a "New" / "Improved" / "Regressed" tag, so you can see where a pattern first appears, gets better or slips. Example: "Regressed: started pressing after blocked 2MP again (G3 R2 61)".

**Confidence display:**
- **High** findings are highlighted with a `.st-hi` accent border and a "High" badge.
- **Medium** findings are shown normally.
- **Low** findings go in a closed `<details>` at the bottom of their card ("Low-confidence notes (N)"), never shown open by default.

Writing the story:
- Write it after the other datasets are done.
- Every claim must point to evidence (game, round, timer).
- When a pattern shows up across games, put it in the set overview and tag where it changed in the game cards. Don't repeat the same text in every game.
- Follow sf6-replay-analysis's "Chess or poker?" rule. A stock answer (a punish, a kill combo) gets one `try_this`. A read gets the options in `try_this` with what each one beats, e.g. "poke (beats walk-up) / walk-up throw (beats block) / whiff punish (beats poke)", plus which one fits this opponent's shown tendency.

## 7. Page rules
- The first line is `<meta name="dash-one-writer">`.
- All fixed text is in the HTML. Data-driven parts are `data-draw` elements stored empty or with `—`.
- Tables:
  - `<table data-source="<id>" data-row-key="<key>">`
  - `<th data-field="<col>">`, adding `class="n"` for numbers
  - an empty `<tbody data-draw="t_<id>">`, filled by `ST.table`
- KPI numbers: `<div class="st-big" data-draw="k_…" data-source="kpis">—</div>`, with the "P1 / P2" label under each as `<div class="st-label" data-draw="kl0" data-source="sets">—</div>` (kl0-kl4).
- Legends: `<div class="st-legend" data-draw="leg_sit" data-source="sets"></div>` (and `leg_kind`), drawn with `ST.swatch` from the chosen set.
- Charts: `<div class="st-chart" data-draw="c_…" data-source="…">`. Each chart has a tooltip, value labels, `role="img"` and an aria-label.
- After writing, read `data/users/<me>/check` (it must be `passed`) and `runs` (it should not exist).

## 8. CSS (use as is)
```html
<style>
.st { font-family: var(--font-anthropic-sans); color: var(--color-fg); max-width: 1100px; }
.st h1 { font-family: var(--font-anthropic-serif); font-weight: 400; font-size: var(--cds-font-size-title); margin: 0 0 var(--cds-gap-xs); }
.st h2 { font-size: var(--cds-font-size-heading); font-weight: var(--cds-font-weight-medium); margin: var(--cds-gap-xl) 0 var(--cds-gap-sm); }
.st h4 { font-size: var(--cds-font-size-caption); font-weight: var(--cds-font-weight-medium); text-transform: uppercase; letter-spacing: 0.04em; color: var(--color-fg-muted); margin: var(--cds-gap-md) 0 var(--cds-gap-xs); }
.st-sub { color: var(--color-fg-muted); margin: 0 0 var(--cds-gap-xs); }
.st-note { color: var(--color-fg-muted); font-size: var(--cds-font-size-caption); margin: var(--cds-gap-sm) 0; }
.st-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--cds-gap-md); margin-top: var(--cds-gap-lg); }
.st-card { background: var(--color-panel); border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); padding: var(--cds-pad-lg); }
.st-label { color: var(--color-fg-muted); font-size: var(--cds-font-size-caption); }
.st-big { font-family: var(--font-anthropic-serif); font-weight: 400; font-size: 1.9rem; font-variant-numeric: tabular-nums; line-height: 1.25; }
.st-grid2, .st-two { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: var(--cds-gap-md); }
.st-chart { position: relative; min-height: 120px; }
.st-chart svg { display: block; }
.st-chart text { font-size: var(--cds-font-size-caption); fill: var(--cds-text-secondary); }
.st-chart .st-val { fill: var(--color-fg); font-variant-numeric: tabular-nums; }
.st-tip { position: absolute; pointer-events: none; background: var(--cds-surface-popover); border: 1px solid var(--cds-border); box-shadow: var(--cds-shadow-popover); border-radius: var(--cds-radius); padding: var(--cds-pad-sm) var(--cds-pad-md); font-size: var(--cds-font-size-caption); white-space: nowrap; }
.st-legend { display: flex; gap: var(--cds-gap-md); font-size: var(--cds-font-size-caption); color: var(--color-fg-muted); margin: 0 0 var(--cds-gap-xs); flex-wrap: wrap; }
.st-sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; vertical-align: -1px; }
.st-wrap { overflow-x: auto; }
.st table { border-collapse: collapse; width: 100%; font-size: var(--cds-font-size-caption); font-variant-numeric: tabular-nums; }
.st th, .st td { text-align: left; padding: var(--cds-pad-xs) var(--cds-pad-sm); border-bottom: 1px solid var(--color-border-line); vertical-align: top; }
.st th { color: var(--color-fg-muted); font-weight: var(--cds-font-weight-medium); }
.st td.n, .st th.n { text-align: right; }
.st-ok { color: var(--color-ok); }
.st-bad { color: var(--color-bad); }
.st-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: var(--cds-gap-md); }
.st-card h3 { font-size: var(--cds-font-size-body); font-weight: var(--cds-font-weight-medium); margin: 0 0 var(--cds-gap-xs); }
.st-card p { margin: 0 0 var(--cds-gap-xs); font-size: var(--cds-font-size-caption); line-height: 1.5; }
.st-k { color: var(--color-fg-muted); }
.st-try { font-size: var(--cds-font-size-caption); line-height: 1.5; border-left: 3px solid var(--color-ok); padding-left: var(--cds-pad-sm); margin: var(--cds-gap-xs) 0; }
.st-tag { display: inline-block; font-size: var(--cds-font-size-caption); border: 1px solid var(--color-border-line); border-radius: 999px; padding: 0 var(--cds-pad-sm); margin-right: var(--cds-gap-xs); }
.st-tag.good { color: var(--color-ok); } .st-tag.bad { color: var(--color-bad); }
.st-item { padding: var(--cds-pad-sm) 0; border-bottom: 1px solid var(--color-border-line); }
.st-item:last-child { border-bottom: 0; }
.st-item.st-hi { border-left: 3px solid var(--cds-chart-1, var(--color-ok)); padding-left: var(--cds-pad-sm); }
.st-head { font-weight: var(--cds-font-weight-medium); font-size: var(--cds-font-size-caption); margin: 0 0 var(--cds-gap-xs); }
.st-muted { color: var(--color-fg-muted); font-size: var(--cds-font-size-caption); }
.st-story { display: grid; gap: var(--cds-gap-md); margin-bottom: var(--cds-gap-xl); }
.st-filter { display: flex; gap: var(--cds-gap-sm); align-items: center; margin: 0 0 var(--cds-gap-sm); font-size: var(--cds-font-size-caption); }
.st select { font: inherit; font-size: var(--cds-font-size-body); color: var(--color-fg); background: var(--color-panel); border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); padding: var(--cds-pad-xs) var(--cds-pad-sm); color-scheme: light dark; cursor: pointer; }
.st select option { color: var(--color-fg); background-color: var(--color-panel); }
.st select:focus-visible { outline: 2px solid var(--cds-chart-1, var(--color-ok)); outline-offset: 1px; }
.st select { font: inherit; font-size: var(--cds-font-size-body); color: var(--color-fg); background: var(--color-panel); border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); padding: var(--cds-pad-xs) var(--cds-pad-sm); color-scheme: light dark; cursor: pointer; }
.st select option { color: var(--color-fg); background-color: var(--color-panel); }
.st select:focus-visible { outline: 2px solid var(--cds-chart-1, var(--color-ok)); outline-offset: 1px; }
.st details { margin-top: var(--cds-gap-lg); }
.st details > summary { cursor: pointer; color: var(--color-fg-muted); font-size: var(--cds-font-size-caption); }
.st details li { margin-bottom: var(--cds-gap-xs); font-size: var(--cds-font-size-caption); color: var(--color-fg-muted); }
</style>
```

## 9. Shared script helpers (use as is)
Set `ST.P1` (the player in focus; P2 always comes from the chosen set's row in `sets` via `ST.p2()`), and add the `ST.table(...)` calls and the one-value KPI drawings for this review. The KPI drawings look like `dash.draw('k_burn', ST.pair('burnouts'))`.

```js
window.ST = window.ST || {};
ST.fmt = d3.format(',');
ST.pct = d3.format('.0%');
ST.cols = () => [dash.colors[0], dash.colors[1] || dash.colors[0]];
ST.P1 = '<P1 name>';
// ---- chosen set ----
ST.sets = () => { const d = dash.data('sets'); return d.status === 'ok' ? [...d.data].sort((a, b) => a.order - b.order) : []; };
ST.SET = () => { const s = document.getElementById('set-pick'); const all = ST.sets(); return (s && s.value) || (all.length ? all[all.length - 1].set_id : null); };
ST.set = () => ST.sets().find((r) => r.set_id === ST.SET()) || {};
ST.p2 = () => ST.set().p2 || 'Opponent';
ST.inSet = (r) => r.set_id === ST.SET();
ST.REDRAW = ['h_title', 'h_sub', 'leg_sit', 'leg_kind', 'kl0', 'kl1', 'kl2', 'kl3', 'kl4', 'k_burn', 'k_aa', 'k_ch', 'k_pc', 'k_pp', 'c_sit', 'c_lens', 'c_kinds',
  'arche', 'habits_p1', 'habits_p2', 'hab_p2_label', 'story', 't_punish', 'fixes', 'training', 'findings', 'hit_filter_opts', 't_hits'];
dash.draw('set_pick', (el) => { const all = ST.sets(); if (!all.length) return; const cur = ST.SET(); el.replaceChildren();
  all.forEach((r) => { const o = ST.el('option', null, `${r.set_id}: ${r.p1} vs ${r.p2} (${r.p2_char}), ${r.format}`); o.value = r.set_id; if (r.set_id === cur) o.selected = true; el.appendChild(o); });
  if (!el.dataset.bound) { el.dataset.bound = '1'; el.addEventListener('change', () => ST.REDRAW.forEach((n) => dash.draw(n))); } });
ST.swatch = (i, text) => { const s = ST.el('span'); const sw = ST.el('span', 'st-sw'); sw.style.background = ST.cols()[i]; s.append(sw, document.createTextNode(text)); return s; };
dash.draw('h_title', (el) => { const r = ST.set(); el.textContent = r.set_id ? `${r.p1} (${r.p1_char}) - ${r.p1_games} vs ${r.p2} (${r.p2_char}) - ${r.p2_games}` : '—'; });
dash.draw('h_sub', (el) => { const r = ST.set(); el.textContent = r.set_id ? `${r.sub} · ${r.set_id}: ${r.format} (BO${r.format === 'FT2' ? 3 : r.format === 'FT3' ? 5 : 9}), ${r.winner} won ${Math.max(r.p1_games, r.p2_games)}-${Math.min(r.p1_games, r.p2_games)}` : '—'; });
dash.draw('leg_sit', (el) => { el.replaceChildren(ST.swatch(0, ST.P1 + ' took'), ST.swatch(1, ST.p2() + ' took')); });
dash.draw('leg_kind', (el) => { el.replaceChildren(ST.swatch(0, ST.P1), ST.swatch(1, ST.p2())); });
[0, 1, 2, 3, 4].forEach((i) => dash.draw('kl' + i, (el) => { el.textContent = `${ST.P1} / ${ST.p2()}`; }));
dash.draw('hab_p2_label', (el) => { const r = ST.set(); el.textContent = r.set_id ? `${r.p2} (${r.p2_char})` : '—'; });
dash.draw('hit_filter_opts', (el) => { const keep = el.value; el.replaceChildren(); [['', 'Both'], [ST.P1, ST.P1], [ST.p2(), ST.p2()]].forEach(([v, t]) => { const o = ST.el('option', null, t); o.value = v; el.appendChild(o); });
  el.value = [ST.P1, ST.p2()].includes(keep) ? keep : ''; });
ST.el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
ST.kv = (k, v) => { const p = ST.el('p'); p.appendChild(ST.el('span', 'st-k', k + ': ')); p.appendChild(document.createTextNode(v == null ? '—' : v)); return p; };
ST.empty = (el, d) => { el.replaceChildren(); if (d.status !== 'ok') { el.textContent = d.status === 'error' ? 'Failed to load' : '—'; return true; } return false; };

// ---- calcs (all from hits + events) ----
ST.p2of = (sets, sid) => (sets.find((r) => r.set_id === sid) || {}).p2;
dash.calc('kpis', { title: 'Per-player counts by set', description: 'Burnouts, anti-airs, counter hits, punish counters and perfect parries per player, one row per set.', inputs: ['hits', 'events', 'sets'],
  fn: (allHits, allEv, sets) => sets.map((st) => { const hits = allHits.filter((h) => h.set_id === st.set_id), ev = allEv.filter((e) => e.set_id === st.set_id);
   const o = { set_id: st.set_id }; [ST.P1, st.p2].forEach((p, i) => { const k = i ? 'p2_' : 'p1_';
    o[k + 'burnouts'] = ev.filter((e) => e.player === p && e.type === 'burnout').length;
    o[k + 'perfect_parries'] = ev.filter((e) => e.player === p && e.type === 'perfect parry').length;
    o[k + 'anti_airs'] = hits.filter((h) => h.attacker === p && h.anti_air === true).length;
    o[k + 'counter_hits'] = hits.filter((h) => h.attacker === p && h.hit_kind === 'counter hit').length;
    o[k + 'punish_counters'] = hits.filter((h) => h.attacker === p && h.hit_kind === 'punish counter').length; }); return o; }) });
dash.calc('sit_pct', { title: 'Damage taken by situation (%)', description: 'Share of each player\'s damage taken, by situation, per set.', inputs: ['hits', 'sets'],
  fn: (allHits, sets) => sets.flatMap((st) => { const hits = allHits.filter((h) => h.set_id === st.set_id); const sits = ['neutral', 'pressure', 'oki', 'punish', 'defense'];
    const tot = (p) => d3.sum(hits.filter((h) => h.victim === p), (h) => +h.damage) || 1;
    return sits.map((s) => { const r = { set_id: st.set_id, label: s }; [ST.P1, st.p2].forEach((p, i) => { const hs = hits.filter((h) => h.victim === p && h.situation === s);
      r['v' + i] = d3.sum(hs, (h) => +h.damage) / tot(p); r['n' + i] = hs.length; }); return r; }).filter((r) => r.n0 + r.n1 > 0); }) });
dash.calc('lens_pct', { title: 'Where P1\'s damage taken came from (%)', description: 'Share of P1 damage taken by what P1 was doing, per set.', inputs: ['hits', 'sets'],
  fn: (allHits, sets) => sets.flatMap((st) => { const mine = allHits.filter((h) => h.set_id === st.set_id && h.victim === ST.P1); const tot = d3.sum(mine, (h) => +h.damage) || 1;
    return d3.rollups(mine, (v) => ({ v0: d3.sum(v, (h) => +h.damage) / tot, n0: v.length }), (h) => h.lens || 'Unclear / super')
      .map(([label, o]) => ({ set_id: st.set_id, label, ...o })).sort((a, b) => b.v0 - a.v0); }) });
dash.calc('kind_counts', { title: 'Hits landed by kind', description: 'Hits each attacker landed per hit kind, per set.', inputs: ['hits', 'sets'],
  fn: (allHits, sets) => sets.flatMap((st) => { const hits = allHits.filter((h) => h.set_id === st.set_id);
    return ['clean hit', 'counter hit', 'punish counter', 'throw', 'reversal'].map((k) => ({ set_id: st.set_id, kind: k,
      p1: hits.filter((h) => h.attacker === ST.P1 && h.hit_kind === k).length, p2: hits.filter((h) => h.attacker === st.p2 && h.hit_kind === k).length })); }) });
ST.pair = (f) => (el) => { const k = dash.data('kpis'); const r = k.status === 'ok' ? k.data.find(ST.inSet) : null; el.textContent = r ? `${r['p1_' + f]} / ${r['p2_' + f]}` : '—'; };

// ---- tables ----
ST.table = (name, id, opts = {}) => dash.draw(name, (tb) => {
  const d = dash.data(id); const table = tb.closest('table');
  const ths = table ? [...table.querySelectorAll('th')] : []; const key = table ? table.getAttribute('data-row-key') : null;
  tb.replaceChildren();
  if (d.status !== 'ok') { const tr = ST.el('tr'); const td = ST.el('td', null, d.status === 'error' ? 'Failed to load' : '—'); td.colSpan = ths.length || 1; tr.appendChild(td); tb.appendChild(tr); return; }
  let rows = d.data; if (opts.filter) rows = rows.filter(opts.filter);
  rows.forEach((r) => { const tr = ST.el('tr'); if (key) tr.setAttribute('data-key', encodeURIComponent(String(r[key])));
    ths.forEach((th) => { const f = th.getAttribute('data-field'); let v = r[f];
      if (v == null || v === '') v = '—'; else if (typeof v === 'number' && !/round|order|rank|game_no/.test(f)) v = ST.fmt(v);
      const td = ST.el('td', th.classList.contains('n') ? 'n' : null, String(v));
      if (f === 'winner') td.classList.add(r[f] === ST.P1 ? 'st-ok' : 'st-bad'); tr.appendChild(td); });
    tb.appendChild(tr); }); });
ST.table('t_punish', 'punish', { filter: ST.inSet });
ST.table('t_hits', 'hits', { filter: (r) => { const s = document.getElementById('hit-filter'); return ST.inSet(r) && (!s || !s.value || r.attacker === s.value); } });
document.querySelectorAll('#hit-filter').forEach((s) => s.addEventListener('change', () => dash.draw('t_hits')));

// ---- horizontal % bars: rows {label, v0, n0, [v1, n1]}; series = number of players shown ----
ST.hbars = (el, rows, series, names, aria) => {
  el.replaceChildren(); const W = el.clientWidth || 500, bh = 12, gap = 3, gh = series * (bh + gap) + 12;
  const svg = d3.select(el).append('svg').attr('width', '100%').attr('role', 'img').attr('aria-label', aria);
  const tip = d3.select(el).append('div').attr('class', 'st-tip').style('display', 'none');
  const lab = svg.append('g'); lab.selectAll('text').data(rows).join('text').attr('x', 0).text((r) => r.label);
  let lw = 0; lab.selectAll('text').each(function () { lw = Math.max(lw, this.getComputedTextLength()); });
  const narrow = W < 460, left = narrow ? 0 : lw + 10, top = narrow ? 16 : 0, rowH = gh + top;
  lab.selectAll('text').attr('y', (r, i) => i * rowH + (narrow ? 11 : bh));
  svg.attr('height', rows.length * rowH + 4);
  const x = d3.scaleLinear().domain([0, d3.max(rows, (r) => Math.max(r.v0 || 0, r.v1 || 0)) || 1]).range([0, Math.max(40, W - left - 80)]);
  rows.forEach((r, i) => { for (let s = 0; s < series; s++) { const y = i * rowH + top + s * (bh + gap), v = r['v' + s] || 0, n = r['n' + s] || 0;
    svg.append('rect').attr('x', left).attr('y', y).attr('height', bh).attr('rx', 2).attr('width', Math.max(2, x(v))).style('fill', ST.cols()[s])
      .on('pointermove', (ev) => { const [mx, my] = d3.pointer(ev, el); tip.style('display', null).text(`${r.label} · ${names[s]}: ${ST.pct(v)} (${n} hits)`);
        tip.style('left', Math.min(mx + 12, el.clientWidth - tip.node().offsetWidth - 4) + 'px').style('top', (my - 34) + 'px'); })
      .on('pointerleave', () => tip.style('display', 'none'));
    svg.append('text').attr('class', 'st-val').attr('x', left + Math.max(2, x(v)) + 6).attr('y', y + bh - 2).text(`${ST.pct(v)} (${n})`); } });
};
dash.draw('c_sit', (el) => { const d = dash.data('sit_pct'); if (ST.empty(el, d)) return; ST.hbars(el, d.data.filter(ST.inSet), 2, [ST.P1 + ' took', ST.p2() + ' took'], 'Share of damage taken by situation'); });
dash.draw('c_lens', (el) => { const d = dash.data('lens_pct'); if (ST.empty(el, d)) return; ST.hbars(el, d.data.filter(ST.inSet), 1, [ST.P1 + ' took'], 'Share of damage taken by what ' + ST.P1 + ' was doing'); });

// ---- grouped vertical bars (hits by kind) ----
ST.bars = (el, rows, cat, fields, labels, aria) => {
  el.replaceChildren(); const W = el.clientWidth || 600, H = 220, m = { t: 18, r: 8, b: 26, l: 36 };
  const svg = d3.select(el).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', aria);
  const x0 = d3.scaleBand().domain(rows.map((r) => r[cat])).range([m.l, W - m.r]).padding(0.25);
  const x1 = d3.scaleBand().domain(fields).range([0, x0.bandwidth()]).padding(0.08);
  const y = d3.scaleLinear().domain([0, d3.max(rows, (r) => d3.max(fields, (f) => +r[f])) || 1]).nice().range([H - m.b, m.t]);
  svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4).tickFormat(d3.format('d'))).call((g) => g.select('.domain').remove()).call((g) => g.selectAll('line').attr('stroke', 'var(--cds-chart-grid)'));
  svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x0).tickSizeOuter(0)).call((g) => g.selectAll('line,path').attr('stroke', 'var(--cds-chart-axis)'));
  const tip = d3.select(el).append('div').attr('class', 'st-tip').style('display', 'none');
  const g = svg.append('g').selectAll('g').data(rows).join('g').attr('transform', (r) => `translate(${x0(r[cat])},0)`);
  g.selectAll('rect').data((r) => fields.map((f, i) => ({ r, f, i, v: +r[f] }))).join('rect')
    .attr('x', (d) => x1(d.f)).attr('width', x1.bandwidth()).attr('y', (d) => y(d.v)).attr('height', (d) => y(0) - y(d.v)).style('fill', (d) => ST.cols()[d.i]).attr('rx', 2)
    .on('pointermove', (ev, d) => { const [px, py] = d3.pointer(ev, el); tip.style('display', null).style('left', Math.min(px + 10, W - 160) + 'px').style('top', (py - 30) + 'px').text(`${d.r[cat]} · ${labels[d.i]}: ${d.v}`); })
    .on('pointerleave', () => tip.style('display', 'none'));
  g.selectAll('text.st-val').data((r) => fields.map((f) => ({ f, v: +r[f] }))).join('text').attr('class', 'st-val')
    .attr('x', (d) => x1(d.f) + x1.bandwidth() / 2).attr('y', (d) => y(d.v) - 4).attr('text-anchor', 'middle').text((d) => d.v);
};
dash.draw('c_kinds', (el) => { const d = dash.data('kind_counts'); if (ST.empty(el, d)) return; ST.bars(el, d.data.filter(ST.inSet), 'kind', ['p1', 'p2'], [ST.P1, ST.p2()], 'Hits landed by kind'); });

// ---- cards ----
ST.cards = (name, id, build, filter) => dash.draw(name, (el) => { const d = dash.data(id); if (ST.empty(el, d)) return; d.data.filter((r) => ST.inSet(r) && (!filter || filter(r))).forEach((r) => el.appendChild(build(r))); });
ST.cards('arche', 'archetypes', (r) => { const c = ST.el('div', 'st-card'); c.appendChild(ST.el('h3', null, `${r.player} · ${r.character}`));
  [['Archetype', `${r.archetype} (${r.lean}), confidence ${r.confidence}`], ['Risk tolerance', r.doc_risk_tolerance], ['Temperament', r.doc_temperament], ['Evidence', r.evidence], ['How to beat this', r.counter_note]].forEach(([k, v]) => c.appendChild(ST.kv(k, v))); return c; });
ST.habits = (player) => (el) => { const d = dash.data('habits'); if (ST.empty(el, d)) return;
  d.data.filter((r) => ST.inSet(r) && r.player === (typeof player === 'function' ? player() : player)).forEach((r) => { const it = ST.el('div', 'st-item'); const h = ST.el('div', 'st-head');
    h.append(ST.el('span', 'st-tag' + (r.kind === 'Strength' ? ' good' : r.kind === 'Leak' ? ' bad' : ''), `${r.kind} · ${r.area}`), document.createTextNode(r.habit));
    it.append(h, ST.el('p', null, 'Seen: ' + r.seen + (r.times ? ` (${r.times}×)` : '')), ST.el('div', 'st-try', r.fix), ST.el('div', 'st-muted', `Source: ${r.origin} · confidence ${r.confidence}`)); el.append(it); }); };
dash.draw('habits_p1', ST.habits(ST.P1)); dash.draw('habits_p2', ST.habits(() => ST.p2()));
ST.cards('fixes', 'fixes', (r) => { const c = ST.el('div', 'st-card'); c.append(ST.el('div', 'st-label', `#${r.rank} · ${r.player}`), ST.el('h3', null, r.fix), ST.el('div', 'st-try', 'Drill: ' + r.drill), ST.kv('Why', r.why)); return c; });
dash.draw('training', (el) => { const d = dash.data('training'); if (ST.empty(el, d)) return; const c = ST.el('div', 'st-card');
  d.data.filter(ST.inSet).forEach((r) => { const it = ST.el('div', 'st-item'); it.append(ST.el('div', 'st-head', `${r.block} · ${r.minutes} min · ${r.focus}`), ST.el('p', null, r.drills)); c.append(it); }); el.append(c); });
ST.cards('findings', 'findings', (r) => { const c = ST.el('div', 'st-card'); c.append(ST.el('div', 'st-label', [r.skill, r.category, r.applies_to, r.confidence].join(' · ')), ST.el('p', null, r.finding), ST.kv('Evidence', r.evidence)); return c; });

// ---- Story of the Set ----
ST.CATS = ['Neutral', 'Offense', 'Defense', 'Player reads / profile'];
ST.storyItem = (r) => { const it = ST.el('div', 'st-item' + (r.confidence === 'High' ? ' st-hi' : '')); const h = ST.el('div', 'st-head');
  if (r.change) h.append(ST.el('span', 'st-tag' + (r.change === 'Improved' ? ' good' : r.change === 'Regressed' ? ' bad' : ''), r.change));
  if (r.polarity !== 'Change') h.append(ST.el('span', 'st-tag' + (r.polarity === 'Worked well' ? ' good' : ' bad'), r.polarity));
  if (r.confidence === 'High') h.append(ST.el('span', 'st-tag', 'High'));
  h.append(document.createTextNode(r.headline)); it.append(h, ST.el('p', null, r.detail), ST.el('div', 'st-muted', `${r.evidence} · ${r.skills}`));
  if (r.try_this) it.append(ST.el('div', 'st-try', 'Try this: ' + r.try_this)); return it; };
ST.storyBody = (card, items) => { ST.CATS.forEach((cat) => { const xs = items.filter((r) => r.category === cat && r.confidence !== 'Low').sort((a, b) => a.rank - b.rank);
    if (!xs.length) return; card.append(ST.el('h4', null, cat)); xs.forEach((r) => card.append(ST.storyItem(r))); });
  const low = items.filter((r) => r.confidence === 'Low'); if (low.length) { const det = ST.el('details'); det.append(ST.el('summary', null, `Low-confidence notes (${low.length})`)); low.forEach((r) => det.append(ST.storyItem(r))); card.append(det); } };
dash.draw('story', (el) => { const s = dash.data('story'), sets = dash.data('sets'), games = dash.data('story_games');
  if (ST.empty(el, s) || sets.status !== 'ok' || games.status !== 'ok') return;
  [...sets.data].filter(ST.inSet).forEach((st) => { const wrap = ST.el('div', 'st-story'); const ov = ST.el('div', 'st-card');
    const mine = s.data.filter((r) => r.set_id === st.set_id), setRows = mine.filter((r) => r.scope === 'set');
    const hd = ST.el('h3', null, `${st.set_id} · ${st.format} · `); hd.append(ST.el('span', st.winner === ST.P1 ? 'st-ok' : 'st-bad', `${st.winner} wins ${Math.max(st.p1_games, st.p2_games)}-${Math.min(st.p1_games, st.p2_games)}`)); ov.append(hd);
    ov.append(ST.kv('Set score by game', st.progression + (st.max_deficit_overcome ? ` · came back ${st.max_deficit_overcome}` : '')));
    const two = ST.el('div', 'st-two'); [['Top 3 highs', 'Worked well'], ['Top 3 lows', 'To improve']].forEach(([t, pol]) => { const col = ST.el('div'); col.append(ST.el('h4', null, t));
      setRows.filter((r) => r.polarity === pol && r.confidence !== 'Low').sort((a, b) => (a.confidence === 'High' ? 0 : 1) - (b.confidence === 'High' ? 0 : 1) || a.rank - b.rank).slice(0, 3).forEach((r) => col.append(ST.storyItem(r))); two.append(col); });
    ov.append(two); const top = new Set(); ['Worked well', 'To improve'].forEach((pol) => setRows.filter((r) => r.polarity === pol && r.confidence !== 'Low').sort((a, b) => (a.confidence === 'High' ? 0 : 1) - (b.confidence === 'High' ? 0 : 1) || a.rank - b.rank).slice(0, 3).forEach((r) => top.add(r.story_id)));
    ST.storyBody(ov, setRows.filter((r) => !top.has(r.story_id))); wrap.append(ov);
    games.data.filter((g) => g.set_id === st.set_id).sort((a, b) => a.game_no - b.game_no).forEach((g) => { const c = ST.el('div', 'st-card');
      c.append(ST.el('h3', null, `Game ${g.game_no} · ${g.game_id} · ${g.result} · set ${g.set_score_after}`), ST.el('p', null, g.summary), ST.kv('Turning point', g.turning_point));
      ST.storyBody(c, mine.filter((r) => r.scope === g.game_id)); wrap.append(c); });
    el.append(wrap); }); });
```
HTML hooks the page needs:
- Header and set picker: `h_title`, `h_sub`, `set_pick` (on `#set-pick`); legends `leg_sit`, `leg_kind`; KPI labels `kl0`-`kl4`; P2 habits label `hab_p2_label`; hits filter options `hit_filter_opts` (on `#hit-filter`). Add any new draw name to `ST.REDRAW`.
- Charts: `c_sit`, `c_lens`, `c_kinds`.
- KPI tiles: `k_burn`, `k_aa`, `k_ch`, `k_pc`, `k_pp`, drawn with `ST.pair('burnouts' | 'anti_airs' | 'counter_hits' | 'punish_counters' | 'perfect_parries')`.
- Cards and lists: `arche`, `habits_p1`, `habits_p2` (in `.st-two`), `story`, `fixes` (in `.st-cards`), `training`, `findings` (in `.st-cards`, inside the closed details).
- Tables: `t_punish`, and `t_hits` (inside the closed details, with the `#hit-filter` select).

## 10. Local copies
Save to `<coaching folder>\<review-folder>\review\` (write via /mnt/user-data/outputs + device_commit_files):
- `<name>.html`: a standalone page for the player's webserver.
  - Same HTML without the meta line.
  - d3 **inlined** (not from a CDN).
  - Data embedded as `window.__DATA__`.
  - A small `window.dash` shim (data/calc/draw/colors/onData/params no-ops; calc runs the fn on the embedded data) that runs the drawings on load and on resize.
  - The CSS tokens defined in `:root`, with a `prefers-color-scheme: dark` block.
  - Before saving, check it in headless Chromium: no page errors, header and story filled.
- `<name>-summary.md`, in this order: result (sets and games), Story of the Set (overview, then games), habits, punishes, player reads, fixes, training routine, findings by skill, method. The pop quiz is optional, at the end.
- `data\*.json` and `data\*.csv` for every dataset.

## 11. Hand-over
Tell the player:
- the dashboard link;
- the set result(s);
- the top 3 highs and lows;
- the top fixes;
- what's approximate (starters, situations, lens groups, perfect parries, anything marked Low confidence);
- where the local copies are.