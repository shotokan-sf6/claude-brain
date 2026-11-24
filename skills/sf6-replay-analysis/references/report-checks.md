# Report checks

Part of the sf6-replay-analysis skill (section 5). Read when the skill points here.

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
