# Lens groups and the Story of the Set

Part of the sf6-review-dashboard skill (sections 4 and 6). Read when the skill points here.

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
- Follow full-review-report's "Chess or poker?" rule. A stock answer (a punish, a kill combo) gets one `try_this`. A read gets the options in `try_this` with what each one beats, e.g. "poke (beats walk-up) / walk-up throw (beats block) / whiff punish (beats poke)", plus which one fits this opponent's shown tendency.
