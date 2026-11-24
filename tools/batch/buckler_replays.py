"""Pull a player's most recent replay IDs from Buckler's Battle Log (streetfighter.com/6/buckler).

Same approach as sfbuff (github.com/alanoliveira/sfbuff, app/clients/buckler_api_client.rb): Buckler has no
public API, so this reads the Next.js data files the site itself loads:
  1. GET /6/buckler and read buildId from the <script id="__NEXT_DATA__"> block
  2. GET /6/buckler/_next/data/<buildId>/en/profile/<short_id>/battlelog.json?page=N  (10 replays a page, pages 1-10)
Both need a logged-in Buckler session: copy the Cookie header from your own browser (DevTools > Network >
any buckler request > Request Headers > cookie) into BUCKLER_COOKIE in tools\\batch\\.env, or a file passed with
--cookie-file. The script never prints or logs it. Cookies expire; a 403 means paste a fresh one.

usage:
  py buckler_replays.py                                 your 100 newest IDs (CFN ID from shotokan.json) -> ids_<cfn>.txt
  py buckler_replays.py 1234567890                      someone else's, by CFN ID
  py buckler_replays.py -n 30 --type ranked             30 newest ranked IDs
  py buckler_replays.py --json out.json                 also save players, characters, MR/LP and round results
  then: py batch_record.py --file ids_<cfn>.txt
The default CFN ID comes from SHOTOKAN_CFN_ID, else cfn_id in shotokan.json ($SHOTOKAN_HOME, else the first one
found in a folder above this script).
"""
import argparse, datetime, gzip, json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

BASE = os.getenv("BUCKLER_BASE_URL", "https://www.streetfighter.com")
UA = os.getenv("BUCKLER_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36")
TYPES = {1: "ranked", 2: "casual", 3: "battle_hub", 4: "custom_room"}   # replay_battle_type ids, as in sfbuff's BattleType
MAX_PAGES = 10                                                           # Buckler keeps 10 pages of 10 (the last 100)


def default_cfn():
    """Your CFN ID: SHOTOKAN_CFN_ID, else cfn_id in shotokan.json ($SHOTOKAN_HOME or a folder above this script)."""
    if os.getenv("SHOTOKAN_CFN_ID"):
        return os.getenv("SHOTOKAN_CFN_ID")
    here = Path(__file__).resolve().parent
    dirs = ([Path(os.environ["SHOTOKAN_HOME"])] if os.getenv("SHOTOKAN_HOME") else []) + [here, *list(here.parents)[:3]]
    for d in dirs:
        f = d / "shotokan.json"
        if f.exists():
            cfn = json.loads(f.read_text(encoding="utf-8")).get("cfn_id")
            if cfn:
                return str(cfn)
    return None


class BucklerError(RuntimeError):
    pass


def load_cookie(path):
    if path:
        return Path(path).read_text(encoding="utf-8").strip()
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).with_name(".env"))
    except ImportError:
        pass
    c = os.getenv("BUCKLER_COOKIE", "").strip()
    if not c:
        sys.exit("No Buckler cookie: set BUCKLER_COOKIE in tools\\batch\\.env or pass --cookie-file (see the top of this file).")
    if c.lower().startswith("cookie:"):
        c = c.split(":", 1)[1].strip()
    return c


def get(url, cookie, want_json=True):
    req = urllib.request.Request(url, headers={"Cookie": cookie, "User-Agent": UA, "Accept-Encoding": "gzip",
                                               "Accept": "application/json" if want_json else "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            text = body.decode("utf-8")
            return json.loads(text) if want_json else text
    except urllib.error.HTTPError as e:   # error mapping as in sfbuff's ErrorHandlerMiddleware
        ct = e.headers.get("Content-Type", "")
        if e.code == 404 and "text/html" in ct:
            raise BucklerError("stale-build")            # the site was redeployed: new buildId
        if e.code == 403:
            raise BucklerError("403: not logged in or the cookie expired; copy a fresh Cookie header from your browser")
        if e.code == 405 and e.headers.get("x-amzn-waf-action"):
            raise BucklerError("405: rate limited by Buckler's firewall; wait a few minutes and try again")
        if e.code == 503:
            raise BucklerError("503: Buckler is under maintenance")
        raise BucklerError(f"HTTP {e.code} for {url}")


def build_id(cookie):
    html = get(f"{BASE}/6/buckler", cookie, want_json=False)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise BucklerError("couldn't find __NEXT_DATA__ on the Buckler page (layout changed, or the page is a login/consent wall)")
    return json.loads(m.group(1))["buildId"]


def battlelog(short_id, cookie, want, types=None, delay=1.5):
    """Yield replay dicts, newest first, until `want` have been yielded (after the type filter) or the log ends."""
    bid, got, retried = build_id(cookie), 0, False
    url = lambda page: f"{BASE}/6/buckler/_next/data/{bid}/en/profile/{short_id}/battlelog.json?page={page}"
    for page in range(1, MAX_PAGES + 1):
        try:
            props = get(url(page), cookie)["pageProps"]
        except BucklerError as e:
            if str(e) != "stale-build":
                raise
            if retried:
                raise BucklerError(f"profile {short_id} not found (check the CFN ID)")
            bid, retried = build_id(cookie), True          # redeployed mid-run: fetch the new buildId once
            props = get(url(page), cookie)["pageProps"]
        for r in props.get("replay_list") or []:
            if types and r.get("replay_battle_type") not in types:
                continue
            yield r
            got += 1
            if got >= want:
                return
        if not props.get("replay_list") or props.get("current_page") == props.get("total_page"):
            return
        time.sleep(delay)   # be polite: Buckler rate-limits bursts


def side(r, n):
    p = r.get(f"player{n}_info") or {}
    pl = p.get("player") or {}
    return dict(name=pl.get("fighter_id"), cfn_id=str(pl.get("short_id") or ""), character_id=p.get("playing_character_id") or p.get("character_id"),
                character=p.get("playing_character_name") or p.get("character_name"), control=p.get("battle_input_type"),
                mr=p.get("master_rating"), lp=p.get("league_point"), round_results=p.get("round_results"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cfn_id", nargs="?", help="the player's CFN ID (Buckler short_id); default: yours, from shotokan.json")
    ap.add_argument("-n", "--count", type=int, default=100, help="how many replay IDs (max 100, Buckler's limit)")
    ap.add_argument("--type", action="append", choices=list(TYPES.values()), help="only these battle types (repeatable)")
    ap.add_argument("--out", help="IDs file (default ids_<cfn_id>.txt next to this script)")
    ap.add_argument("--json", help="also write the replays with players, characters, MR/LP and round results")
    ap.add_argument("--cookie-file", help="file holding the Cookie header (else BUCKLER_COOKIE from .env)")
    a = ap.parse_args()
    a.cfn_id = a.cfn_id or default_cfn()
    if not a.cfn_id:
        ap.error("no CFN ID: pass one, or set cfn_id in shotokan.json (or SHOTOKAN_CFN_ID)")
    cookie = load_cookie(a.cookie_file)
    types = {k for k, v in TYPES.items() if v in (a.type or [])} or None
    try:
        reps = list(battlelog(a.cfn_id, cookie, min(a.count, 100), types))
    except BucklerError as e:
        sys.exit(f"Buckler: {e}")
    out = Path(a.out) if a.out else Path(__file__).with_name(f"ids_{a.cfn_id}.txt")
    lines = [f"# {len(reps)} newest replays for CFN {a.cfn_id}, pulled {datetime.datetime.now():%Y-%m-%d %H:%M}"]
    rows = []
    for r in reps:
        p1, p2 = side(r, 1), side(r, 2)
        when = datetime.datetime.fromtimestamp(r["uploaded_at"]).strftime("%Y-%m-%d %H:%M") if r.get("uploaded_at") else "?"
        bt = TYPES.get(r.get("replay_battle_type"), str(r.get("replay_battle_type")))
        lines.append(f"{r['replay_id']}  # {when} {bt}: {p1['name']} ({p1['character'] or p1['character_id']}) vs {p2['name']} ({p2['character'] or p2['character_id']})")
        rows.append(dict(replay_id=r["replay_id"], uploaded_at=when, battle_type=bt, p1=p1, p2=p2))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(reps)} replay IDs -> {out}" + (f" (+ {a.json})" if a.json else ""))


if __name__ == "__main__":
    main()
