"""batch_record.py - record a list of SF6 replays by replay ID, with no one at the controls.

Works with batch_replays.lua (search + play inside SF6) and capture_replay.lua (frame capture).
For each ID it asks the Lua script to play the replay, starts OBS recording when the match
starts, stops it when the match ends, then moves the video and the capture json into the
replays folder as <ID>.mp4 and <ID>.json.

Setup (once):
  py -m pip install obsws-python python-dotenv   (or pip install ...)
  OBS: Tools > WebSocket Server Settings > Enable (port 4455). Put the password in .env yourself.
  Copy batch_replays.lua next to capture_replay.lua in reframework/autorun.
  Copy .env.example to .env (next to this script) and fill it in.

Usage:
  py batch_record.py A7LWJNR6U PCJFRDBW3 TUE445BB9
  py batch_record.py --file ids.txt          (one ID per line, # comments allowed)
  py batch_record.py --probe                 (no recording: print screen changes, to calibrate)
  py batch_record.py --no-obs ID ...         (play and capture only, no video)
SF6 must be running on CFN > Replays > Search (Keyword Search or a search result), with the window able
to receive input and the mouse pointer off the game window.
"""
import argparse, json, os, shutil, sys, time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    pass

DATA = Path(os.getenv("REFRAMEWORK_DATA", r"C:\Program Files (x86)\Steam\steamapps\common\Street Fighter 6\reframework\data"))
_home = os.getenv("SHOTOKAN_HOME")
_replays = os.getenv("SHOTOKAN_REPLAYS") or os.getenv("REPLAYS_DIR") or (os.path.join(_home, "replays") if _home else None)
if not _replays:
    sys.exit("Set SHOTOKAN_REPLAYS (or SHOTOKAN_HOME, or REPLAYS_DIR) in batch/.env: the folder captures and videos are moved to.")
REPLAYS = Path(_replays)
BATCH = DATA / "sf6_batch"
OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = int(os.getenv("OBS_PORT", "4455"))
START_TIMEOUT = int(os.getenv("START_TIMEOUT", "120"))     # seconds from search to match start
MATCH_TIMEOUT = int(os.getenv("MATCH_TIMEOUT", "900"))     # longest replay
END_TIMEOUT = int(os.getenv("END_TIMEOUT", "90"))          # closing the replay menu

LOG = Path(__file__).with_name("batch_record.log")


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def status():
    for _ in range(20):
        try:
            return json.loads((BATCH / "status.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            time.sleep(0.05)
    return {}


_seq = int(time.time())


def command(action, replay_id=None):
    global _seq
    _seq += 1
    BATCH.mkdir(parents=True, exist_ok=True)
    tmp = BATCH / "command.tmp"
    tmp.write_text(json.dumps({"seq": _seq, "action": action, "replay_id": replay_id}), encoding="utf-8")
    os.replace(tmp, BATCH / "command.json")
    return _seq


def wait_for(pred, timeout, what, poll=0.25):
    t0, last = time.time(), None
    while time.time() - t0 < timeout:
        s = status()
        key = (s.get("phase"), s.get("top_flow"), s.get("note"), s.get("msg"))
        if key != last:
            extra = f" dialog={s.get('msg')}" if s.get("msg") else ""
            log(f"  phase={s.get('phase')} screen={s.get('top_flow')} fight_st={s.get('fight_st')} note={s.get('note')}{extra}")
            last = key
        if s.get("phase") == "error":
            raise RuntimeError(s.get("note"))
        if pred(s):
            return s
        time.sleep(poll)
    raise TimeoutError(f"timed out waiting for {what}")


class Obs:
    def __init__(self):
        import obsws_python as obs
        pw = os.getenv("OBS_PASSWORD")          # read from .env, never printed or logged
        self.cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=pw, timeout=5)
        log(f"OBS connected ({self.cl.get_version().obs_version})")

    def start(self):
        if self.cl.get_record_status().output_active:
            self.cl.stop_record(); time.sleep(1)
        self.cl.start_record()

    def stop(self):
        return self.cl.stop_record().output_path


def move_when_free(src, dst, timeout=60):
    t0 = time.time()
    while True:
        try:
            shutil.move(str(src), str(dst)); return
        except (PermissionError, OSError):
            if time.time() - t0 > timeout:
                raise
            time.sleep(1)


def record_one(rid, obs):
    vid, cap = REPLAYS / f"{rid}.mp4", REPLAYS / f"{rid}.json"
    if vid.exists() and cap.exists():
        log(f"{rid}: already in replays, skipped"); return "skipped"
    seq = command("play", rid)
    log(f"{rid}: searching")
    wait_for(lambda s: s.get("seq") == seq and s.get("phase") == "playing", START_TIMEOUT, "the replay to start")
    if obs:
        obs.start(); log(f"{rid}: recording")
    try:
        wait_for(lambda s: s.get("phase") in ("ending", "done"), MATCH_TIMEOUT, "the match to end", poll=1)
    finally:
        out = obs.stop() if obs else None
    log(f"{rid}: match over")
    wait_for(lambda s: s.get("phase") == "done", END_TIMEOUT, "the replay to close")
    REPLAYS.mkdir(parents=True, exist_ok=True)
    if out and not vid.exists():
        move_when_free(out, vid); log(f"{rid}: video -> {vid}")
    src = DATA / f"{rid}.json"
    if src.exists() and not cap.exists():
        move_when_free(src, cap); log(f"{rid}: capture -> {cap}")
    elif not cap.exists():
        log(f"{rid}: WARNING no capture json found in {DATA}")
    return "ok"


def probe():
    log("probe: printing screen changes; navigate SF6 by hand, Ctrl+C to stop")
    last = None
    while True:
        s = status()
        key = (s.get("top_flow"), s.get("fight_st"), s.get("phase"), s.get("msg"))
        if key != last:
            extra = f" dialog={s.get('msg')}" if s.get("msg") else ""
            log(f"screen={s.get('top_flow')} fight_st={s.get('fight_st')} phase={s.get('phase')}{extra}")
            last = key
        time.sleep(0.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--file")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--no-obs", action="store_true")
    ap.add_argument("--retries", type=int, default=1)
    a = ap.parse_args()
    if not (BATCH / "status.json").exists():
        sys.exit(f"No status from batch_replays.lua in {BATCH}. Is SF6 running with the script loaded, and REFRAMEWORK_DATA right?")
    if a.probe:
        command("idle"); return probe()
    ids = list(a.ids)
    if a.file:
        ids += [l.split("#")[0].strip() for l in Path(a.file).read_text().splitlines()]
    ids = [i.upper() for i in ids if i]
    if not ids:
        sys.exit("No replay IDs given.")
    obs = None if a.no_obs else Obs()
    results = {}
    for rid in ids:
        for attempt in range(a.retries + 1):
            try:
                results[rid] = record_one(rid, obs); break
            except Exception as e:
                log(f"{rid}: FAILED ({e}){' - retrying' if attempt < a.retries else ''}")
                results[rid] = f"failed: {e}"
                command("idle"); time.sleep(3)
    command("idle")
    log("done: " + ", ".join(f"{k} {v}" for k, v in results.items()))


if __name__ == "__main__":
    main()
