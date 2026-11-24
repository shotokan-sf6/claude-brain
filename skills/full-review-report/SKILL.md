---
name: "full-review-report"
description: "Third tier of an SF6 replay review, for Full and Tournament reviews only: after shared-core-review and quick-review-report, load the guideline skills, pull frame data, check story moments on video, and write the hand-written review (story, habits, reads, gameplan, fixes, training) into sf6.db's review_docs. Loaded by sf6-replay-analysis."
---

# Full review: the hand-written layer

Runs after `shared-core-review` and `quick-review-report`, for Full and Tournament reviews. Start from the Quick draft (its numbers, its generated reads and habits) and replace it with judgement: what each player was trying to do, which decisions were good, and what to practice.

**Reference files** live in this skill's `references/` folder (`${CLAUDE_PLUGIN_ROOT}/skills/full-review-report/references/`). Read one before the step that names it.

## 1. Guideline skills
Before analysing, load each of these with the Skill tool and apply them alongside this one. What each one checks in a review: `full-review-guideline-checks.md` (read it at the start of each Full review).

`sf6-the-defense-equation-exdojo`, `sf6-improving-shimmy-exdojo`, `sf6-stagger-pressure-exdojo`, `sf6-player-archetypes-exdojo`, `sf6-structuring-offense-defense-exdojo`, `sf6-consistency-exdojo`, `sf6-how-to-jump-exdojo`, `sf6-jab-strings-exdojo`, `sf6-footsies-101-exdojo`, `sf6-spacing-traps-exdojo`, `sf6-defense-offense-101-exdojo`, `sf6-air-footsies-exdojo`, `sf6-dps-and-divekicks-exdojo`, `sf6-holistic-lens-exdojo`, `sf6-drive-parry-mindgames-exdojo`, `sf6-dealing-with-drive-rush-exdojo`, `sf6-drive-rush-blockstrings-exdojo`, `sf6-delay-option-selects-exdojo`, `sf6-drive-reversal-exdojo`, `sf6-back-recovery-exdojo`, `sf6-beating-unstable-players-exdojo`, `sf6-matchups-gameplans-exdojo`, `sf6-using-pokes-exdojo`, `sf6-hit-confirms-exdojo`, `sf6-simple-gameplan-exdojo`, `sf6-delayed-throw-offense-exdojo`, `sf6-reactions-exdojo`, `sf6-coach-doctaafrikan`, `sf6-coach-coosco`, `sf6-coach-shog`, `sf6-character-notes`, `sf6-footsies-handbook-maj`, `sf6-fgc-glossary` (when needed), `sf6-drive-efficiency`.

`sf6-coach-shog` is .shog's coaching rules, shipped as an example; the player's own coaching skill, if they have one, overrides the others where they conflict. When the player adds another guideline skill, add it to this list.

> **Installed skills only.** This plugin ships the analysis, prediction, dashboard, glossary, character notes, Drive efficiency, Juzzy and Maj skills, and .shog's coaching rules as an example. Other coaching skills named here (E.X. Dojo, Coosco, DoctaAfrikan) aren't included: load them only if the player has installed them, otherwise skip those checks.

## 2. Frame data (SuperCombo wiki)
WebFetch is blocked by the wiki's bot check. Use the built-in browser (load the built-in-browser skill first; request_access if the site isn't allowed yet).
- Frame data: `https://wiki.supercombo.gg/w/Street_Fighter_6/<Character>/Frame_data`; overview, strategy, matchups: `.../<Character>`, `.../<Character>/Strategy`, `.../<Character>/Matchups`; system: `.../Street_Fighter_6/Gauges`, `.../Glossary`, `.../Offense`, `.../Defense`.
- Slugs use underscores and keep dots: `C._Viper`, `E._Honda`, `M._Bison`, `A.K.I.`, `Dee_Jay`, `Chun-Li`. If one 404s, take the link from `https://wiki.supercombo.gg/w/Street_Fighter_6`.
- Pull each page's tables in one javascript_tool call:
```js
[...document.querySelectorAll('table')].filter(t=>/Startup|Notes|Punish Adv/.test(t.rows[0]?.innerText||'')).map(t=>[...t.rows].slice(1).map(r=>[...r.cells].map(c=>c.innerText.replace(/\s+/g,' ').slice(0,140)).join(' | ')).join('\n')).join('\n=====\n')
```
- Pull each page once per session, for both characters (punish questions need the opponent's block advantage; the Invuln column matters on wake-up). Matchups pages are sometimes empty placeholders: say so and build matchup notes from frame data and the replay.
- Use numpad notation. Cite the wiki values you pulled, not remembered ones, and say whether each value came from the meter or the wiki.

## 3. Go through the set
- Read report.md exchange by exchange. Correct analyzer mistakes (labels, situations) before writing anything up.
- Check story moments and surprising rows on video (the detail pass in `shared-core-video-processing.md`): spacing, intent, what a player was going for. Pull short clips only for those moments.
- Without a legible frame meter, one-frame timing can't be proven: mark it "likely" or "unclear".
- To compare players' decisions (where they press, which buttons, what it leads to), run `python tools\full_review_decision_presses.py DB --player NAME[,ALIAS] ... [--char C]`.
- Run the report checks in `full-review-report-checks.md`: standard opponent checks, missed anti-airs and Drive Rush checks, covering the whole match, where the player gets hit, where the player deals damage.

## 4. Judge decisions: chess or poker?
- **Chess** decisions have a stock best answer (the optimal punish, spending everything when it kills, the combo route, the on-paper answer in a rare spot): give the answer and say plainly when it was missed.
- **Poker** decisions (neutral spacing, oki, defensive guesses) have several options that beat each other. Give the options and what each beats and loses to, which one the opponent's tendencies favoured (with evidence), and the risk/reward (Defense Equation modifiers: HP, Drive, super, position, score). Judge the decision, not the outcome.
- Say which kind each decision is.
- Apply `sf6-coach-shog`'s rules (2MK confirms, wake-up options, when taking a throw is correct, read vs react, risk vs skill gap). In every Full review include the conditioning check (Structure note #3) and the Plant and Harvest read (Theory #2) in the gameplan.

## 5. Write the review (review_docs)
Pass these in META `review_docs`, then re-ingest with `shared_core_db.py ingest` (this replaces the Quick draft's reads and habits with the hand-written ones):

| Dataset | Rows (today's sets) | What goes in it |
|---|---|---|
| `story` | about 12 | Ranked headlines of what decided the set: category, polarity, headline, detail, evidence (round @ timer), the guideline skill it draws on, "try this" |
| `story_games` | one per game | Result, set score after, summary, turning point |
| `habits` | about 8 | Kind (Strength / Leak / Pattern), area, habit, where seen, times, fix, origin, confidence |
| `archetypes` | one per player | Archetype, lean, confidence, evidence, risk tolerance and temperament (DoctaAfrikan's), how to counter, adaptation; `spectra_override` keyed by internal key when the computed spectrum is wrong (`shared-core-player-spectra.md`) |
| `set_gameplan` | one per player | Plan, mid-set adjustments, what worked, what would have been better (conditioning and Plant and Harvest go here) |
| `fixes` | 3 | Ranked fixes, each with a drill and why |
| `training` | 3 | Blocks with focus, drills and minutes |
| `prediction` | 1 | The graded prediction (from shared-core-review) |

Optional, when the set calls for them: `findings` (notable numbers), `punish` (missed and landed punishes with frame data), `sets` (a hand-written subtitle or note).

## 6. The Full reply
Start with the result (rounds won and lost, how each round ended) and the prediction grade, then:
- **The player's top 3 habits** that cost the most: round + timer references, what happened, the frame-data reason, and a Training Mode fix (with a dummy recording setup when that fits).
- **Opponent's habits** (pressure enders, throw vs shimmy, wake-up choices, neutral pokes, Drive and super spending) with references, and how to exploit each using their frame data.
- **What went well:** 1-2 things to keep doing.
- **Resources:** burnouts and what the other player did with them; the three Drive Rush classes; Drive Impact and Parry; super left unspent; the Drive economy (Drive lost blocking and to punish counters / Drive Impact) and the Drive efficiency part from `sf6-drive-efficiency`.
- **Gameplan:** each player's plan, adjustments, conditioning and Plant and Harvest.
- **Matchup notes** for the opponent's character, from the wiki and this replay.
- **Fixes and training.**
- **Event log** at the end, grouped by round, so the player can scrub to each moment.

## 7. Tournament review (the level above Full)
For tournament sets, or when asked. On top of a Full review:
- **Every key exchange checked on video:** sync the capture to the video (the round timer first showing 98 gives the offset: video_t = offset + (frame-1)/60). For each moment, a composite strip (frames from -1.5 s to +0.5 s, the frame meter held at about +0.7 s, both input histories).
- **Decision audit:** for each major guess (wake-up option, after-block choice, round start, resource spend): situation, options, the on-paper choice from the Defense Equation with modifiers, and a verdict (Good / Acceptable / Could have guessed better). Do the reward math when it's clear (e.g. a reversal that wins 800 and loses about 3,700 has to work more than 4 times in 5).
- **Adaptation timeline:** round by round, what each player changed and what they didn't.
- **Between games:** a 3-4 point checklist the player could have told themselves.
- **Rematch prep:** a scouting report and a numbered gameplan.
- **Longer training plan:** several weeks, with drills, minutes and something measurable.
- Store these as the `tournament` dataset (set_id, part, order, title, body, evidence, verdict) in review_docs (shown as a "Tournament review" section on the set's review page) and set the review to Tournament.

## 8. Dashboards for another player
When asked for a dashboard copy from the other player's side (e.g. "obi1-dash"), run the analyzer with that player as the focus, write the hand-written datasets from their side (format: `sf6-review-dashboard`), and keep it out of the player's tracker and database views.
