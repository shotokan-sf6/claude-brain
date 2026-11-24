---
name: "replay-review-prediction"
description: "Before analyzing any SF6 set, predict both players' gameplans, the winner, score and path to victory, then grade the prediction after the review. Run it for every replay review, even when the player doesn't ask."
---

# Replay review prediction

> **Installed skills only.** This plugin ships the analysis, prediction, dashboard, glossary, character notes, Drive efficiency, Juzzy and Maj skills, and .shog's coaching rules as an example. Other coaching skills named in this text (E.X. Dojo, Coosco, DoctaAfrikan) aren't included: load them only if the player has installed them, otherwise skip those checks.


Runs inside sf6-replay-analysis (shared-core-review step 4) for **every** set review (Quick, Full or Tournament), whether or not the player asks for a prediction. The prediction is written **before** any capture, report.md or video of the set is opened, so it is a real test of how well the database and the guideline skills model the players.

## 1. Gather only pre-set information (blind)
Always in this order: manifest, history, prediction stored, then the analyzer.
- **Pre-set facts:** `python tools\shared_core_blind_manifest.py <captures...> --out manifest.json`. It reads only the first game's header (players, CFN IDs, characters, controls, MR/LP before the set, battle type) and withholds round results, later games' MR/LP (MR moves after each game, so it gives results away), the number of games and all frame data. Never read capture headers or the Buckler list's `round_results` directly before predicting.
- **History:** `python tools\shared_core_db.py history DB --opp <name|CFN> --opp-char <char> --my-char <char> [--before <date or ISO time>] [--exclude <replay IDs>]`: earlier sets vs this opponent, the character matchup, the opponent's reads and habits, and the player's recent leaks and strengths, only from sets before the one predicted (use `--before` when re-predicting or back-testing an older set).
- **Baseline:** start from the MR gap (the higher-MR player wins about 72% of sets in the data (recounted 2026-11-24)); go against it only with direct evidence (history vs this player, a known matchup problem).
- Format (FT2, FT3, ranked/casual) and characters.
- SuperCombo matchup and strategy pages for both characters, and the guideline skills (sf6-matchups-gameplans-exdojo, sf6-simple-gameplan-exdojo, sf6-player-archetypes-exdojo).
- Do not open the capture, the analyzer output or the video yet. If anything about the result was already seen, say so in the prediction.

## 2. Write the prediction (one per set)
For each set, write `prediction.json` with `written_at`, `replays` (the set's replay IDs) and `manifest` (the blind manifest), then store it with `python tools\shared_core_db.py predict DB prediction.json` before running the analyzer. `predict` refuses a set whose games are already in the database, and a stored prediction can't be replaced after ingest; ingest links it to the set and records the grade from `review_docs.prediction`. The prediction covers:
- **Each player's gameplan:** how they want to win neutral, their main approach and defensive tools, the resources they lean on (Drive Rush, Drive Parry, stance, supers), and their likely archetype.
- **Winner and score** (e.g. The player 3-1), with a confidence (High / Medium / Low) and the reason for it.
- **Path to victory** for the predicted winner, and the most likely way the other player wins games.
- **Key factors to watch:** 2-4 specific things that would decide it (e.g. "does the player anti-air the jump-ins", "does he keep pressing into Jus Cool").
Show the prediction to the player before starting the analysis.

## 3. Grade it after the review
Once the review is done, compare each part against what happened:
- Winner and score: right / wrong.
- Gameplans: which parts matched, which the players didn't do, and what they did instead.
- Key factors: which actually decided the set.
- One line on what the prediction missed and why (e.g. no earlier data on this opponent, MR overstated their level, didn't expect a mid-set adjustment).

## 4. Store and show it
- Store the prediction and the grade in the database through ingest: `review_docs` dataset `prediction` (one row per player: predicted plan, winner, score, confidence, path, and the graded outcome).
- On the dashboard, show it in the **Gameplan** section next to `set_gameplan` (each player's plan, mid-set adjustments, what worked, how each should adjust).
- Over several sets, note how often the predictions are right; if they keep missing in the same way, adjust how they are made.