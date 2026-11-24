---
name: "sf6-drive-efficiency"
description: "Model the value of SF6 Drive and super spending in replay reviews: compare resource routes vs meterless routes (damage, knockdown advantage, position) on offense, and reversal / parry / Drive Reversal vs blocking on defense."
---

# SF6 Drive efficiency

> **Installed skills only.** This plugin ships the analysis, prediction, dashboard, glossary, character notes, Drive efficiency, Juzzy and Maj skills, and .shog's coaching rules as an example. Other coaching skills named in this text (E.X. Dojo, Coosco, DoctaAfrikan) aren't included: load them only if the player has installed them, otherwise skip those checks.


Use this in every Full replay review (sf6-replay-analysis's full-review-report tier loads it) and whenever the player asks whether a Drive or super spend was worth it. The question is always: **what did the spend buy, compared with the best route that didn't spend?** And on defense: **what did the choice cost in Drive, compared with blocking?**

Drive moves in both directions all the time, not only when a player spends it:
- **Hitting gives Drive back**: the attacker gains Drive when an attack connects, on hit **and on block**.
- **Blocking costs Drive**: every blocked attack drains the blocker's gauge (Drive damage on block).
- **Getting hit can cost Drive**: punish counters and **Drive Impact hits** drain the victim's gauge on top of the damage.
- **Parrying gives Drive back**: each parried hit refunds part of the parry's cost.
So a player's Drive economy = what they spend + what they lose (blocking, punish counters, Drive Impact) - what they gain (hitting, blocks, parries, regen). Burnout usually comes from the losses as much as from the spending.

## 1. Gauge facts (measured, not remembered)
Measured from the player's REFramework captures (Nov 2026 patch). Re-measure after a patch with `tools\drive_measure.py "replays\*.json"` (Drive changes by state) and `tools\drive_contact.py "replays\*.json"` (gains and losses on contact by move type), and cross-check the SuperCombo `Street_Fighter_6/Gauges` page. Drive gauge max 60,000 = 6 bars; super max 30,000 = 3 bars.

| Item | Measured |
|---|---|
| Passive regen | +40 per frame (about 0.24 bar/s); +20 while being hit or held in a throw; +60-100 while walking forward |
| Raw Drive Rush (from neutral) | 1 bar |
| Drive Rush cancel (pressure / combo) | 3 bars, taken about 10 frames into the rush |
| Drive Rush button bonus | the first button out of a Drive Rush is **+4 frames** on block and on hit (a -1 button becomes +3), so it starts pressure and leads to bigger combos than the same button without Drive Rush |
| Last bar spent | the drop that empties the gauge starts burnout on the same frame; it still counts as spending (or as Drive lost blocking) |
| Extended supers | some supers take more after they start: Terry's SA2 takes a 3rd super bar if available and a 3rd hit for 1 Drive bar. They count as one super at their own level, tagged "extended" |
| Raw Drive Rush from parry | 0.5 bar for the parry + 0.5 when the rush starts = 1 bar. This is a raw Drive Rush even when the opponent is still in blockstun: only the 3-bar drop makes it a cancel. The resource log's `drive_rush_cancel` is the 3-bar part of Drive Rush spend; the Drive economy chart shows it as its own Spent slice |
| Drive Impact | 1 bar |
| Drive Reversal | 2 bars |
| OD special | 2 bars |
| Drive Parry | 0.5 bar to start, then 0.3 bar/s held |
| Successful parry | usually +0.5 bar per parried hit; some refunded +1 bar (likely perfect parries; check) |
| Attacker gain on contact (hit or block) | about +0.03 for lights up to +0.15-0.2 for heavier hits and specials, per hit; adds up to ~1-2 bars a round for an active attacker |
| Drive damage to a blocker | about -0.05 for lights, -0.2 to -0.5 for mediums, heavies and specials, per blocked hit; a Drive Impact on block takes more |
| Drive damage to a player getting hit | most hits take none; punish counters about -0.2 to -1 bar; a Drive Impact hit -1 bar or more |

Drive lost while blocking or getting hit is **not** spending (the resource log excludes it from the spending categories), but it is part of the cost of the situation that caused it (section 4).

## 2. What a bar is worth
There's no fixed exchange rate; value a resource by what else it could have bought and what losing it risks.
- **Damage equivalent:** for each character, the median extra damage a bar bought in the player's history (route comparison in section 3, from the database). Use that as the base value of 1 Drive bar and 1 super bar, per character. With fewer than ~5 comparable routes, say the value is uncalibrated rather than inventing one.
- **Scarcity:** the bars that take a player below 2 are worth more, because they sit next to burnout (no Drive Rush, no parry, no Drive Reversal, chip damage, a blocked Drive Impact can stun in the corner). Flag every spend that left the spender at 2 bars or fewer, and every burnout, with what drained them (spending vs blocking vs getting punish-countered).
- **Lethal:** a spend that kills or wins the round is worth it (chess, full-review-report "Chess or poker?"). A spend that adds damage to an opponent who dies anyway is waste.
- **Opportunity:** super bars kept for a Level 3 / CA threat or a reversal have value unspent; note when a spend gave up a later kill threat.
- **Time:** at +40/frame, one bar regenerates in about 4 s of neutral. Early-round spends recover; late-round or low-Drive spends often don't.

## 3. Offense: resource route vs free route
For each combo or pressure sequence that spent Drive or super, compare it with the best route from the **same starter** that spent nothing (or less). Per combo the analyzer records (hits rows, `hits` table in sf6.db):
- `damage`;
- `drive_spent`, `super_spent`: what the attacker spent from 20 frames before the first hit (raw Drive Rush / Drive Impact in) until they were free;
- `drive_gained`: what the attacker got back from hitting during the combo;
- `drive_damage`: the victim's Drive lost during the combo (punish counter, Drive Impact, throws);
- `knockdown` (hard knockdown / back recovery / normal recovery) and `kd_adv`: frames between the attacker being free and the victim being free. On a knockdown, the victim counts as free on their first frame out of the wake-up, even if that frame blocks or gets hit by a meaty. Without a knockdown, it's plain frame advantage after the combo;
- `corner_dist`: the victim's distance to the corner afterwards (0 = in the corner);
- `victim_drive_after`: the victim's Drive afterwards.

Then:
- **Gain** = (damage difference) + (Drive damage difference and Drive gained, at bar value) + (oki and corner difference, judged in words until the thresholds in section 5 exist).
- **Net cost** = Drive spent - Drive gained back by the route's hits.
- **Efficiency** = gain per net bar. Compare it with the bar's value from section 2.
- Verdicts: **worth it** (gain clearly above cost, or it killed, reached the corner, or burnt them out), **marginal**, **waste** (the free route got nearly the same, or the spend left the spender burnt out or at ≤2 bars for little gain).
- Where to get the free route: first from the same player's history in sf6.db (same character and starter, `drive_spent = 0 AND super_spent = 0`); otherwise from the character's SuperCombo combo page, and say it's theoretical.
- **Drive Rush value (from the player):** the reward is generally large (the +4 on block and on hit). A **raw drive rush** (1 bar) is generally Drive-efficient and fairly low risk: the downside is the bar plus a clean or counter hit if it's checked, and it's a safe, easy way to start pressure. Only flag it when the opponent keeps checking it and the player doesn't adjust. A **drive rush cancel** (3 bars) is relatively expensive, so it needs a real payoff (a confirmed combo, the corner, burnout pressure). Don't weigh character-specific Drive Rush strength for now.
- **Pressure spends** (pressure drive rush cancel, OD specials on block, raw drive rush): judge by what came next (hit, throw, blocked and safe, blocked and punished, checked), and count the Drive they took off the blocker plus what the attacker gained from the blocked hits. Report hit rate and average damage per 3-bar Drive Rush over the set.
- **Drive Impact**: what it bought per bar (hit, punish counter, blocked into corner stun, Drive-Impacted back), including the Drive it took off the victim.
- `kd_adv` values above ~60 on knockdowns are rare and worth checking on video (long juggles and supers can confuse the rule).

## 4. Defense: spending to get out vs blocking
At each defensive spend (wake-up reversal, Drive Reversal, Drive Parry, OD reversal, super reversal), compare it with **blocking / taking the throw** (the baseline in sf6-the-defense-equation-exdojo).

**Expected loss from blocking** the situation:
- the **Drive the blocker loses** on each blocked hit, and the Drive the attacker gains from them, plus chip;
- the attacker's likely follow-ups, weighted by **this attacker's shown frequencies** (set and database): throw ~1,200 x their throw rate, shimmy into punish counter x shimmy rate (punish counters also drain Drive), frame-trap counter hit x rate, and a reset of their pressure;
- what staying in the corner / under pressure costs over the next exchange, and how close the blocking Drive drain puts the defender to burnout.

**Expected value of the spend**:
- **Reversal / OD reversal / super:** success x (damage + position + turn back + Drive gained from the hit) minus baited x (punish-counter combo damage + its Drive damage) minus the bars at their value. Use the attacker's bait rate (how often they blocked or shimmied wake-ups).
- **Drive Reversal:** 2 bars to end pressure with recoverable damage and space; worth it when the blocking loss it avoids (including the Drive the rest of the string would have drained) is bigger than 2 bars plus the risk of being baited (-6) (sf6-drive-reversal-exdojo). Flag ones that left the defender at ≤2 bars.
- **Drive Parry:** cost 0.5 bar + 0.3 bar/s held; refunds about **+0.5 bar per parried hit** (sometimes +1), which can make it cheaper than blocking the same string, and a perfect parry gives a punish. Main risk: being **thrown out of parry** (punish-counter throw damage plus Drive lost). Per player the analyzer logs every parry (`parries.json`, `parries` table): frames held, cost, hits parried, Drive regained, net, perfect, and what happened next (nothing, raw drive rush, punished them, hit, thrown). A parry habit with positive or small negative net Drive and few throws is efficient; one that keeps getting thrown or hit is expensive defense.
- **Getting thrown or punish-countered** after a defensive choice is part of that choice's cost (damage and Drive).

Verdict per spend: better than blocking, about even, or worse, with the numbers. Defensive calls are usually poker (full-review-report "Chess or poker?"): judge them against the attacker's shown frequencies, not the single outcome.

## 5. Oki thresholds (to be added)
The player plans to add **knockdown-advantage thresholds** that say which okizeme options a given plus frame allows (e.g. meaty a 5f button, safe jump, strike/throw without a dash, dash-up meaty, needs Drive Rush), per character. When the table exists, turn each `kd_adv` into named oki options and include them in the offense gain. Until then, report `kd_adv` and the recovery type, and describe the oki in words.

## 6. Where the numbers are
- **Per combo** (hits rows / `hits` table): `drive_spent`, `super_spent`, `drive_gained`, `drive_damage`, `knockdown`, `kd_adv`, `corner_dist`, `victim_drive_after`.
- **Per player per round** (`resources.json` / `resources` table): Drive spent by category (Drive Rush, Drive Parry, Drive Impact, Drive Reversal, OD specials, other), super bars spent with each super (as `L<level> <move>[ extended] (<bars> bars[, +<n> Drive]) @<timer>`: the level is the bars its first drain used, and later drains while the player never left the super animation, unless a fresh super start, are added to it), burnouts, gauges left at round end, plus `gain_hit`, `gain_block` (Drive gained by hitting), `parry_regain`, `loss_block` (Drive lost blocking), `loss_hit` (lost getting hit), `loss_hit_drive_impact`, `loss_hit_punish_counter`.
- **Per parry** (`parries.json` / `parries` table): as in section 4.
- report.md has `resources`, `contact`, `Drive efficiency` and `Drive Parries` sections.
- On the dashboards: separate Drive and super spending charts (super by level), the Drive economy section (Out vs In, Drive Parry summary, combos that spent resources), and a Drive economy trend on the Overview. Knockdown advantage is recorded but left off the dashboards until the player adds his oki thresholds.

## 7. Reporting
- In the Resources part of the report, add **Drive efficiency** for each player: the Drive economy per round (spent, lost blocking, lost to punish counters / Drive Impact, gained from hits, blocks and parries), damage bought per net Drive bar and per super bar, the 2-3 best and worst spends (round + timer, route used vs free route, gain, verdict), parry net Drive and times thrown out of parry, and what drained them before each burnout.
- Defensive spends go in the defense section, with the blocking baseline (including the Drive blocking would have cost) beside them.
- Say what's measured vs estimated. Expected-loss figures rest on frequency estimates from small samples: say how many instances they rest on.
- Feed the Resource use spectrum (Conservative ↔ Spendthrift) in player reads: efficiency shows *whether* a spendthrift player is wasting it or cashing in.