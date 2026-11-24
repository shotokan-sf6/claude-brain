# Datasets and page calcs

Part of the sf6-review-dashboard skill (section 3). Read when the skill points here.

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
- **With capture files** (shared-core-review), `shared_core_analyze.py` writes `sets`, `games`, `hits` and `events` directly: use them as is, and read burnouts, perfect parries and anti-airs from the data. Don't call anti-airs from sampled video frames alone: they misread ground counter-hits as anti-airs.
