---
name: shotokan-setup
description: "Set up SHOTOKAN for a new player: coaching folder, player config (name, CFN ID, main character), the bundled Python tools, the history database and the REFramework capture scripts. Use when the player says 'set up SHOTOKAN', 'install the replay tools', 'get started with replay reviews', or when another SHOTOKAN skill finds no shotokan.json."
---

# SHOTOKAN setup

Set up everything a player needs before their first review. Keep the conversation plain: describe what each step does, not file paths, unless the player asks. Work on the player's computer through the device tools (the player must open this chat in the Claude desktop app and connect a folder).

## 1. Coaching folder
- Ask which folder to use as the coaching folder (suggest one, e.g. `D:\SF6-Coaching` or `Documents\SF6-Coaching`). Request access to it if it isn't connected.
- Create `replays\`, `history\`, `observations\` and `tools\` inside it if missing.

## 2. Player config
Ask, one short question at a time (AskUserQuestion where available):
- In-game name and any older names.
- CFN ID (the number on their Buckler profile URL, `streetfighter.com/6/buckler/profile/<ID>`).
- Main character and control type (Classic / Modern).
Write `<coaching folder>\shotokan.json`:
```json
{"player_name": "...", "other_names": [], "cfn_id": "...", "main_character": "...", "control": "Classic", "dashboards": {}}
```
Every other SHOTOKAN skill reads this file for "the player".

## 3. Tools
- Copy `${CLAUDE_PLUGIN_ROOT}/tools/` into `<coaching folder>\tools\` (keep `batch\` as a subfolder). Do not overwrite an existing `tools\.env` or `tools\batch\.env`.
- Write `<coaching folder>\tools\.env` with `SHOTOKAN_HOME=<coaching folder>` (see `tools\.env.example`).
- Check Python 3.10+ is available on the player's computer (`python --version` in the device shell, or ask them to run it). If missing, point them to python.org and stop this step until it's installed.
- Initialise the database: `python tools\sf6db.py init history\sf6.db`.

## 4. Capture scripts (REFramework)
- The player needs REFramework for SF6 (from its GitHub releases page; they download and install it themselves).
- Copy `${CLAUDE_PLUGIN_ROOT}/mods/autorun/*.lua` into the game's `reframework\autorun\` folder and `${CLAUDE_PLUGIN_ROOT}/mods/data/` into `reframework\data\` (the game folder is usually `...\steamapps\common\Street Fighter 6\`). Ask for access to that folder, or give the player the exact copy steps.
- Explain: watching a replay in-game saves `<ReplayID>.json` in `reframework\data`; move captures (and any OBS video `<ReplayID>.mp4`) into `<coaching folder>\replays\` before a review.

## 5. Optional
- Batch recording and pulling replay IDs from Buckler: see `tools\batch\README.md`. The Buckler cookie goes in `tools\batch\.env` and is set by the player; never ask for, read or store it.
- Video (OBS) is optional; reviews work from captures alone.

## 6. Check
- Run `python tools\analyze_capture.py` with no arguments to confirm it starts, and confirm `shotokan.json` and the database exist.
- Tell the player what to do next: watch a replay to capture it, then ask "review my last set".
