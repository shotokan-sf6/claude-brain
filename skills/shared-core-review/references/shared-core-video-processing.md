# Processing video (games with no capture)

Part of the shared-core-review skill (games with no capture; the detail pass is also used by full-review-report for story moments). Read when the skill points here.

## 3. Process the video
When a capture file covers the game, only do the detail pass, for story moments. Put each upload in its own folder and work on a copy. Check that ffmpeg is installed (`which ffmpeg`) and install it if it's missing. If the player sent screenshots, read those first: paused screenshots are the most legible source.

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
