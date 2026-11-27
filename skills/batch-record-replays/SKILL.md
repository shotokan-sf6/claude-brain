---
name: batch-record-replays
description: Record a list of SF6 replays by replay ID with no one at the controls, using tools\batch\batch_record.py (batch_replays.lua plays each replay in SF6, capture_replay.lua saves the frame capture, OBS records the video) and file them as <ID>.mp4 + <ID>.json in the replays folder. Use after pulling replay IDs from Buckler, or when the player gives replay IDs to record or capture.
---

# Batch record replays

Records SF6 replays by replay ID with `<coaching folder>\tools\batch\batch_record.py` (bundled at `${CLAUDE_PLUGIN_ROOT}/tools/batch/`; setup and details in `tools\batch\README.md`). For each ID the script:
1. asks `batch_replays.lua` (inside SF6, through `reframework\data\sf6_batch\command.json` / `status.json`) to search for and play the replay,
2. starts OBS recording when the match starts and stops it when the match ends,
3. moves the video and the capture into the replays folder (`SHOTOKAN_REPLAYS`, or `<SHOTOKAN_HOME>\replays`) as `<ID>.mp4` and `<ID>.json`.

IDs that already have both files are skipped. A failed ID is retried once (`--retries N` changes that), then skipped. Progress goes to the output and `tools\batch\batch_record.log`: a `--- n/total: <ID>` line before each replay and, after each one, a progress bar (`[####----] n/total (pct%) - ok, skipped, failed; elapsed, time left`), with time left estimated from recorded replays only. When the player asks how a run is going, read the last progress line; it shows status counts only, no results.

## Rules
- The script takes over the game (it presses keys in SF6). Run it only when the player asks to record.
- The OBS WebSocket password is in `tools\batch\.env`. Never open, read, print or copy `.env`. If OBS fails to connect, tell the player to check OBS is open, the WebSocket server is enabled (Tools > WebSocket Server Settings, port 4455), and the password in `.env` matches (Show Connect Info). Or offer `--no-obs` (capture only, no video).
- Don't open any capture, video or log result line that shows who won before the set's blind prediction is written (shared-core-review). Report recording status only: recorded, skipped, failed.
- One run at a time; never start a second copy while one is running.

## Before running
The player needs to have:
- SF6 running with REFramework, `capture_replay.lua` and `batch_replays.lua` loaded,
- the game on CFN > Replays > Search > Keyword Search, cursor on "Search by player name" (a search result screen or the Replay ID box also works),
- the mouse pointer off the game window (SF6 menus follow the pointer),
- OBS open with the WebSocket server on (unless `--no-obs`).

If the script exits with "No status from batch_replays.lua", SF6 isn't running with the Lua script loaded, or `REFRAMEWORK_DATA` in `.env` is wrong: tell the player, don't retry.

## Steps
1. Get the IDs: an IDs file from `buckler_replays.py` (`tools\batch\ids_<CFN ID>.txt`), or IDs the player gives.
2. Run from `<coaching folder>\tools\batch`, in the background (each replay takes a few minutes):
   ```powershell
   py batch_record.py --file ids_<CFN ID>.txt
   py batch_record.py ID1 ID2            # IDs directly
   py batch_record.py --no-obs ID1       # capture only, no video
   ```
3. When it finishes, read the last `done:` line of the output: each ID is `ok`, `skipped` or `failed: <reason>`.
4. Check the replays folder has `<ID>.mp4` and `<ID>.json` for each ok ID. A `WARNING no capture json` line means the video recorded but capture_replay.lua didn't write a capture.
5. Report in a few lines (per ID: recorded / skipped / failed and why), without results. Offer the next step: review with `sf6-replay-analysis` (shared-core-review gzips and files the captures).

## If something goes wrong
- `ConnectionRefusedError [WinError 10061]` from `obsws_python` at startup: OBS isn't open or its WebSocket server is off. Nothing was played or recorded. Ask the player to open OBS (or use `--no-obs`), then run again.
- `search failed: <dialog text>`: the game's dialog, e.g. "No such replays found" (the replay expired or the ID is wrong).
- `timed out waiting for the replay to start`: the game was on an unexpected screen or the pointer moved the menu cursor. Ask the player to put the game back on Keyword Search and run again (recorded IDs are skipped).
- Menu steps misbehaving: `py batch_record.py --probe` prints screen changes while the player navigates by hand; sequences can be overridden in `reframework\data\sf6_batch\config.json` (see the README).
- The player can stop a run with Ctrl+C or the Stop button under "Batch replays" in the REFramework menu; Claude stops it with TaskStop.
