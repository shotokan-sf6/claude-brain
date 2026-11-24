# Page layout, section by section

Part of the sf6-review-dashboard skill (section 5). Read when the skill points here.

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
