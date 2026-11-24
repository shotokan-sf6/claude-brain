# Batch replay recording

Records SF6 replays by replay ID with no clicking: `batch_replays.lua` (inside SF6) searches and plays
each replay, `capture_replay.lua` saves the frame capture, and `batch_record.py` drives OBS and files
the results as `<ID>.mp4` + `<ID>.json` in your replays folder (`SHOTOKAN_REPLAYS`, or `SHOTOKAN_HOME\replays`, set in `batch/.env`; e.g. `D:\SF6-Claude-Coaching\replays`).

## Setup (once)
1. Copy `batch_replays.lua` (from the REFramework mods repo) into `Street Fighter 6\reframework\autorun\` (next to `capture_replay.lua`).
2. OBS: Tools > WebSocket Server Settings > Enable WebSocket server (port 4455, authentication on).
3. Install the Python packages. On Windows, if `pip` isn't recognised, use the launcher:
   `py -m pip install obsws-python python-dotenv`
4. Copy `.env.example` to `.env` (next to `batch_record.py`) and fill it in: the OBS password
   (OBS > Tools > WebSocket Server Settings > Show Connect Info) and your SF6 `reframework\data` path.

## Use
1. In SF6 go to CFN > Replays > Search > Keyword Search, with the cursor on "Search by player name".
   A search result screen, or the Replay ID box already open, also works.
2. Move the mouse off the game window. SF6 menus follow the mouse pointer, and a pointer resting over
   a menu moves the cursor to a different row.
3. Run:

       py batch_record.py ID1 ID2 ID3
       py batch_record.py --file ids.txt          (one ID per line, # comments allowed)
       py batch_record.py --no-obs ID1 ID2        (play and capture only, no video)

Already-recorded IDs are skipped; a failed ID is retried once, then skipped. Progress is in `batch_record.log`.
Stop at any time with Ctrl+C, or the Stop button under "Batch replays" in the REFramework menu.

## How it moves through the menus
The script reads which screen is on top (`app.UIFlowManager`) and only presses keys on screens it knows.
On any other screen it waits, then stops with an error rather than guessing.

| Screen | What it does |
|---|---|
| Keyword Search | waits for the fade-in, then W (wraps from "Search by player name" to "Search by Replay ID") and F |
| Replay ID box | submits the ID directly (`TextInputDialogWidget:InvokeResultEvent`) |
| Search result | F to open the result |
| Replay info | F to start the replay |
| Play Again / End Replay menu | S once to End Replay, then F (a retry presses F only) |
| Search result again (after a replay) | Escape back to Keyword Search |
| A dialog (e.g. "No such replays found") | records its text; the ID fails with `search failed: ...` |

After a replay SF6 rebuilds CFN top > search result > replay info by itself, so the script waits for
each screen to settle before pressing anything.

Timing details that matter:
- **One press = one frame.** As in rkaganda's `flow_control.lua`, a key is reported down for a single
  rendered frame. The game counts a press on every frame a key is down, so at high frame rates
  (menus run around 120 fps) a key held for a few frames moved the cursor several rows.
- **Waits are in real time.** Waits are counted in 1/60 s of the game's clock, not in rendered frames,
  so they don't shrink when the frame rate goes up. The REFramework panel shows the current frame time.
- **Screens fade in.** Keys pressed while a screen is still fading in are dropped, so each screen has a
  settle time before its first key (longer for Keyword Search and the replay info screen).

## If a step goes wrong
1. `py batch_record.py --probe` prints each screen change (also saved to
   `reframework\data\sf6_batch\flows.json`) while you navigate by hand.
2. Override any sequence in `reframework\data\sf6_batch\config.json`, then use Reset scripts in REFramework.
   Each step is `[key, wait]`: the key is pressed once, then the script waits that many 1/60 s ("" only waits).
   Keys are `via.hid.KeyboardKey` names (`F` confirm, `Escape` back, `W`/`S` up/down). Examples:

       {"nav": {"app.UICFNReplayTopTabSearchChildSearchId.FlowParam": [["",30],["W",3],["",20],["F",3],["",40]]},
        "on_end": [["",30],["S",3],["",15],["F",3],["",60]],
        "settle_screen": {"app.UICFNReplayTopTabSearchChildSearchId.FlowParam": 120}}

   `nav` is per screen while looking for the search box; `on_results`, `on_info` and `on_end` run on the
   result, info and end-of-replay screens; `settle_frames` / `settle_screen` set how long a screen must stay
   on top before keys are pressed.
3. When a search fails, the log shows the game's dialog text after `dialog=`.

## Pull replay IDs from Buckler
`buckler_replays.py` gets a player's newest replay IDs (up to 100, Buckler's limit) from their Buckler Battle Log, in the same format `batch_record.py --file` reads. It uses the same method as [sfbuff](https://github.com/alanoliveira/sfbuff): the Buckler site's Next.js data files, with your own logged-in session.
1. Sign in at streetfighter.com/6/buckler in your browser, open DevTools > Network, click any Buckler request and copy its `cookie` request header.
2. Paste it after `BUCKLER_COOKIE=` in `.env` (see `.env.example`). Cookies expire; a 403 means paste a fresh one.
3. Run it, then record:

       python buckler_replays.py <CFN ID>                     100 newest -> ids_<CFN ID>.txt
       python buckler_replays.py <CFN ID> -n 30 --type ranked 30 newest ranked only
       python buckler_replays.py <CFN ID> --json replays.json also save players, characters, MR/LP and round results
       python batch_record.py --file ids_<CFN ID>.txt
It waits between pages and stops at a rate limit (405), maintenance (503) or an expired cookie (403) with a message saying which.
