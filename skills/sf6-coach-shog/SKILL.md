---
name: "sf6-coach-shog"
description: "Sean's (.shog) own SF6 coaching rules and theories: 2MK hit-confirm limits, judging wake-up options, when taking a throw is correct, read vs react, risk vs skill gap, Plant and Harvest, the M. Bison Scissor Kicks theory, the Economy of Buttons, and tracking how players condition each other. Load during every SF6 replay review."
---

> **Example rules.** These are .shog's own coaching rules and theories, shipped as an example of a player's personal rules. They describe how .shog reviews; another player can keep, edit or replace them with their own.


# Coach .shog: Sean's coaching rules

Rules Sean has set for how SF6 replays are coached. They override general advice from the other guideline skills where they conflict. The full-review-report tier of sf6-replay-analysis loads this for every Full and Tournament review. When Sean gives a new coaching rule, add it here rather than to the review skills.

The 2MK and wake-up rules apply to any player being reviewed. The throw rule is written for Sean; when reviewing someone else, apply the same test (tech only a shown pattern) from their side.

## Cancelable 2MK and hit confirms
- **Cancelable 2MK can't be hit-confirmed.** For almost every character whose 2MK is special/super cancelable (Cancel column "Sp SA"), you can't hit-confirm the cancel in practice. The cancel is a buffer you commit to before you know whether it hit. Don't recommend "hit-confirm 2MK into a special" for these. Instead, suggest buffering into something safe or plus on block (e.g. 2MK~Drive Rush, or a special that's safe at that spacing), or a confirm from a different starter.
- **Some 2MKs are confirmable.** A 2MK that **isn't** cancelable but is **+4 or more on hit** (e.g. Sagat's) can usually be confirmed into a linked follow-up. Check the wiki's Cancel and Hit Adv columns before calling any 2MK confirmable.

## Judging wake-up options
When either player does something on wake-up, classify it before you coach it:
- **Wake-up normal (e.g. 5LP, 2MK): often intentional.** It beats an opponent's delayed or offbeat offense and catches shimmies. Judge it as a read (did it fit what the opponent was doing?), not as a mistake by default.
- **Invincible reversal (e.g. OD Cannon Spike, OD Shoryuken, invincible supers, Drive Reversal): usually intentional.** Treat it as a decision and judge whether it was a good gamble (meter, health, the opponent's tendencies, whether they were baiting).
- **Non-invincible special that's worse than −5 on block (e.g. Spiral Arrow): treat it as an input error, not a choice.** Look at the input history for the cause, such as buttons mashed during the knockdown or a motion buffered from a blocking or tech input. Coach the execution fix (cleaner wake-up inputs, not mashing on knockdown), not the decision. Check the wiki's Invuln and Block Adv columns to sort a move into one of these three groups.

## Throws: taking one can be correct
Don't tell Sean to "tech more" by default. Taking a throw (~1200) is often the **safe** choice, because a delay tech or a button that gets shimmied usually costs 2500–7000, especially when the opponent has high Drive or a Level 3 available. Only recommend teching when there's a **pattern**: e.g. the opponent repeatedly makes him block one light and then throws, or always throws at the same plus situation. Name the pattern (with round + timer for each instance) and tech that specific spot. When the opponent has shown shimmies, or has meter for a big punish, frame each throw he took as an acceptable cost, not a mistake.

# SF6 structure notes
Sean's notes on how SF6 situations are decided. Add new ones here.

## Structure note #1: read or react, by situation
- **Okizeme is always a read (poker) for both players.** Neither side can generally react to what the other does on wake-up. Each predicts what the other will, or should, do from past behaviour. The exception: some reversals and actions can answer a slow-startup move on reaction.
- **Pressure is mostly reads too.** Actions come too fast to react to, so decisions are usually made in advance.
- **Shimmies and other passive actions are where reactions happen.** By stepping back or waiting, the player gives himself time to see what the opponent shows and answer it: a whiffed throw tech, a wake-up Drive Parry, a jump.
  - **This only works while the player is uncommitted** (walking, blocking or standing still, all of which can be cancelled on any frame). Once they press a button, throw or Drive Rush, they're locked into its startup and recovery and can't react until it ends, so it's back to a read. A shimmy that steps back too late, or presses too early, has already committed before the opponent shows anything, so judge it as a read, not a missed reaction.
- **What can't be reacted to:**
  - The offensive player can't react to a wake-up invincible reversal; it has to be a read (bait it, or block).
  - The defensive player can't react to most meaty buttons or throws with a wake-up reversal; it has to be a read too.
  - There are very specific situations where a wake-up super can be reacted to. Sean will define these later; until then, treat wake-up supers as reads.
  - **Against a reversal, a shimmy back and blocking at point blank are the same option.** The defender can't react to the difference, so both cover the reversal the same way. In a review, judge the choice between covering the reversal and going for a strike or throw, not how the cover was done (stepping back vs standing still).

How to apply it in a review:
1. **Tag each key decision** as oki, pressure, shimmy/passive or neutral, before judging it.
2. **Oki and pressure: judge it as a read, not a reaction.** Did it fit what the opponent had shown before (habits, timings, earlier knockdowns)? Never criticise a player for "not reacting" to a meaty, a throw or a wake-up reversal. Ask whether the read matched the evidence, and what the better read was (chess or poker?).
3. **Shimmy and passive: judge it as a reaction.** After a shimmy or a deliberate wait, did the player punish what the opponent showed (whiffed tech, wake-up parry, jump)? A missed answer here is an execution or attention leak, not a bad read.
4. **Wake-up supers:** treat them as reads on both sides until Sean adds the reactable cases.

## Structure note #2: reaction time in frames
- **Average human reaction:** about 200-250 ms to something seen and about 170 ms to something heard. SF6 runs at 60 frames per second (1 frame is about 16.7 ms), so that is about **12-15 frames** for a visual cue and about **10 frames** for a sound cue.
- **Faster than average is possible** when the player has a read and is watching for one specific action, e.g. waiting for a Drive Rush or a jump they expect.
- **Slower than average is common** when the opponent stacks options or structures their offense so the player has to think about many things at once (see `sf6-reactions-exdojo` on mental stack).

How to apply it in a review:
1. Before calling something "reactable", compare its startup (from frame data or the capture) with about 12-15 frames, plus the startup of the answer. Something faster than the reaction window has to be a read or a pre-decision (Structure note #1).
2. A move in the 15-25 frame range, such as a Drive Impact, a slow overhead or a jump from far, is reactable only if the player was looking for it. Say whether they had reason to expect it (shown habit, situation) or were juggling several threats.
3. When a player misses a reactable answer, check how many options the opponent had shown in that situation. If they were stacked, judge it as a mental-stack problem: narrow what to look for, rather than "react faster".
4. Sound cues (e.g. a Drive Rush or Drive Impact sound) are about 2-5 frames faster than sight. Mention them when they would help.

## Structure note #3: conditioning, and whether the player knows they're doing it
Every repeated action teaches the opponent something. Most of it is involuntary: players react to cues they've been hit by before (classical conditioning: a walk-up after a knockdown starts to trigger a tech by itself), and they do more of what paid off and less of what got punished (operant conditioning). Conditioning fades when it stops being reinforced (an unpunished habit grows back) and returns under pressure even after it seemed gone.

The question for every review is not just what each player did, but **what each player taught the other, and whether they meant to**. A player who conditions on purpose has it in their gameplan: they repeat something early so a different option works later (Theory #2, Plant and Harvest). A player who conditions by accident hands the opponent a free read.

How to track it in a review:
1. **Find the lessons.** For each player, list repeated situations where one side kept doing the same thing (same wake-up option, same tech timing, same follow-up after a blocked string, same poke at a range). Count how often, and in which games and rounds (early vs late).
2. **Check the response.** Did the opponent's behaviour in that situation change after the lesson? E.g. after two wake-up reversals, did they start blocking or baiting on oki? After several throws, did they start teching? Compare rates early and late in the set.
3. **Intentional or accidental.** Intentional: the player later used a different option in the same situation that beat the conditioned response (that's a harvest), or the repeated option sits clearly in their gameplan. Accidental: the opponent cashed in on the conditioned behaviour, or the player never switched. Mark it as a read with a confidence, not a fact.
4. **Tie it to the gameplan.** In the Gameplan section, say what each player was conditioning, whether they harvested it, and what they could have planted on purpose given their character's tools.
5. **Name unreinforced habits.** When a player stops being punished for a habit, expect it to grow (extinction of the punishment); call it out even in sets they won.

# Theories
Sean's numbered theories about how to approach a set. Apply them when judging risk, and add new ones here as Theory #2, #3...

## Theory #1: match your risk to the gap in skill
- **Favourite: take as little risk as you need.** If you feel you can beat someone without taking risks, do. Low-risk play (blocking, safe pokes, stock punishes and combos) is what keeps results consistent; gambles only give a weaker player a way back in.
- **Even match: expect more reads.** When players are close, both are looking for small edges, so the set turns into more poker: more reads, conditioning and calculated guesses.
- **Underdog: take more risk, in the right spots.** A weaker player has to take risks to win, but the risks have to be well chosen: a read on a shown habit, a spot where a hit swings the round (corner, low life, opponent burnt out or without meter). Random gambles don't count.

How to apply it in a review:
1. **Place the set** as favourite, even or underdog for the player being reviewed, from MR or league, earlier sets in sf6.db against this opponent, and how the first games went. Say which one and why. It can change mid-set (e.g. the opponent adapts and the gap closes).
2. **Judge risky decisions against that placement.** Risky decisions are wake-up reversals, Drive Impact, raw supers, hard-read round starts, jumps and committal specials.
   - **Favourite:** flag needless risk as a consistency leak, even when it worked. Name the safe option that would also have won.
   - **Even:** judge each read on whether it came from information the opponent had shown (chess or poker?).
   - **Underdog:** judge whether the risks were taken in the right spots. Flag playing too safe if that gives a stronger player a free set, and flag random gambles.
3. In the prediction (replay-review-prediction), use the placement to predict how much risk each player should take, then grade whether they did.

## Theory #2: Plant and Harvest (credit: PortaJon, Arizona FGC)
Plant and Harvest is a way of structuring a set over time, credited to PortaJon from the Arizona FGC. Early in a set (or round), you **plant** an idea in the opponent's head by showing something, even when it isn't the analytically best choice in that moment. Later, you **harvest** it: the opponent has adjusted to what you showed, and that adjustment opens up a bigger reward for you.

Examples:
- **Plant reversals, harvest breathing room.** Reversal on wake-up more often early than the analytics would say is wise. The opponent learns to bait it by blocking, or backs off their oki. Later that gives you more room on defense: fewer meaties, more free wake-ups.
- **What the reversal plant does and doesn't harvest.** Once the opponent hesitates on their meaties, they are blocking or baiting, not striking, so a Level 3 or another reversal into that hesitation gets blocked. The harvest is the breathing room: getting out of oki, blocking, walking out or taking the turn back. A Level 3 reversal only pays off if the opponent has gone back to meatying, and it is still a big read with big risk, even after proper planting. In reviews, **note it when a reversal harvest works** (a planted Level 3 that wins a round or the game is a very good read, so point out good spots for it), but don't suggest reversal harvests as a routine adjustment.
- **Spot a habit, harvest when it kills.** If the opponent techs throws in a situation, you don't have to shimmy right away. Wait until you have the resources to kill: with full Drive and 3 bars of super, a shimmy that catches a tech often converts into about 6,000 damage.
- **Accidental planting.** A player who mashes reversal-timing buttons on wake-up teaches the opponent to meaty them, because the meaty keeps working. That makes a wake-up reversal (e.g. a Level 3) more likely to land later at a critical moment. Mashing on wake-up isn't good, but understand how the behaviour shapes what the opponent does next.

**Risk and reward of timing the harvest:** hold the harvest too long and you can lose the round or the set before you use it; show it too early and you spend it on a small reward instead of closing out a round. The best harvests come when the payoff is largest: lethal, a round point, or the opponent at low Drive.

How to apply it in a review:
1. For each player, list what they planted (repeated options early in the set or round) and whether it was deliberate (they harvested it later) or accidental (the opponent harvested it instead). Use Structure note #3 to track the response.
2. **Judge the planting by the harvest, not by itself.** An early reversal that lost can still be correct if it set up a later win; say so instead of flagging it as a bad gamble. If nothing was ever harvested, it was just a loss.
3. **Judge the harvest timing.** For a shown habit (e.g. a tech the player could shimmy), note when the harvest came, what resources the player had, and what it was worth. Flag harvests spent for small damage when a kill was close, and habits never cashed in before the round or set ended.
4. **Coach planting on purpose.** Suggest what each player could plant with their character's tools, and when to harvest it.

## Theory #3: The M. Bison Scissor Kicks Theory (credit: PortaJon, Arizona FGC)
Credited to PortaJon from the Arizona FGC. Put the opponent in a rock-paper-scissors (poker) situation that you understand better than they do. M. Bison's Scissor Kicks are about -3 to -5 on block depending on spacing, so by the numbers they're often punishable, or at least the defender should get their turn back. But the Bison player knows the spacing and the situation far better than the defender, so even though they're minus and their turn should be over, they often outplay the defender anyway: the defender doesn't know which spacing they're in, what reaches, or what Bison tends to do next, and hesitates to make the right read.

These situations are powerful when you find them, because the knowledge gap does the work: the opponent's correct answer exists, but they rarely pick it with confidence. The edge comes from understanding, not from frame advantage.

What makes a good one:
- **Technically minus or even**, so the opponent thinks it should be their turn.
- **Spacing- or timing-dependent**, so the right answer changes from case to case and is hard to learn mid-match.
- **Several plausible answers** for the defender (press, block, jump, parry), each beaten by something you have.
- **You know the follow-ups cold**: what is safe at each spacing, and which of your options beats each of their answers.

How to apply it in a review:
1. **Find each player's Scissor Kicks spots:** situations where they were minus (or not clearly ahead) but still won the next exchange more often than not. Log the move, the spacing, the advantage on block and what the opponent did next.
2. **Judge the defender** with Structure note #1 (it's a read, not a reaction) and coach .shog's 2MK and throw rules: did they hesitate (hold block and give the turn back), guess randomly, or have a planned answer? Give the answer that frame data and spacing support, and say how they could learn it (lab the spacing, the attacker's top two follow-ups, as in Doc's pop quiz).
3. **Judge the attacker:** were these spots deliberate (part of the gameplan, repeated in good conditions) or lucky? Suggest situations the player's character could build into their own Scissor Kicks spots.
4. Tie it to Theory #2: a defender who keeps losing these spots is being conditioned to hesitate, which the attacker can harvest later (e.g. with a throw or a Drive Rush once the defender just blocks).

## Theory #4: The Economy of Buttons (credit: James Chen and PortaJon)
Credited to James Chen and PortaJon. In any round there is a finite number of opportunities to press buttons, and both players share them. Some players try to take every opportunity: very aggressive, often taking big risks on offense to run the opponent over. Others press very little: they can be patient, or they can be passive players who get run over. Working out which type the opponent is helps structure the gameplan.

- **Pressing gives information.** The more buttons a player presses, the more the opponent learns about their habits. Starting slow disguises your own plan while you see what the opponent wants to do, which is useful for adjusting your gameplan early.
- **Observant vs passive.** Both press little, but they are different players:
  - **Observant:** doesn't press a lot, but uses the information they gain to make adjustments.
  - **Passive:** doesn't press a lot and fails to take their turn back or challenge unsafe offense. They cede all initiative and let the opponent run them over.
- **Two ways to beat a player through the economy:**
  - **Starve them:** some players struggle when you take most of the buttons (stay active, keep the initiative), because they never get to play their game.
  - **Let them hang themselves:** others struggle when you give them all the buttons, because pressing constantly leaves predictable gaps, unsafe pressure and readable strings.
- **SF6 Drive economy:** a player who presses a lot and often uses pressure Drive Rush cancels on block is likely to lose the Drive economy war (3 bars per cancel, Drive spent into the opponent's block, burnout risk). Letting them take the buttons while you block and punish is often the better trade.

How to apply it in a review:
1. **Measure each player's share of the buttons:** use **decision presses** per round (set_stats `decision_presses` / `press_rounds`, from the analyzer's presses.json): new attacks, specials, supers and throws started while the opponent wasn't being hit, knocked down or getting up. Raw press counts are inflated for the winning player, who gets more presses from combos and oki, so don't compare raw counts. Also use neutral exchanges started (the Initiative spectrum), pressing after their own blocked attack (Temperament, offense), and pressure Drive Rush cancels per round. Compare with the character's baseline (`sf6-character-notes`). How to weight the winner further is still being tuned with Sean. `tools\full_review_decision_presses.py` breaks decision presses down by situation, move and outcome; damage per decision press (damage dealt / decision presses) against the opponent's is the clearest measure of who used their share better (every player measured so far takes 45-50% of a set's presses).
2. **Label each player** as a button taker (aggressive), observant (presses little, adjusts from what they learn) or passive (presses little, doesn't take their turn back or challenge unsafe offense). To tell observant from passive, use the Adaptability spectrum and check whether they took their turn back after the opponent's minus moves and gaps.
3. **Check the fit:** did each player pick the right economy against this opponent? Starving a player who needs buttons, or letting a reckless presser hang themselves, are both correct; letting an observant player have free initiative is not.
4. **Tie it to the Drive economy:** for heavy pressers, compare Drive spent on pressure Drive Rush cancels with Drive lost blocking and burnouts, and say who won the Drive war.
5. **Link to Structure note #3 and Theory #2:** what did each player learn from the other's presses early, and did the slower starter use that information later?