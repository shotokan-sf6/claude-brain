"""Where SHOTOKAN's local data lives. Set environment variables (or put them in tools/.env) instead of editing code.

  SHOTOKAN_HOME          the coaching folder (replays, history, reviews). Default: the folder above tools/,
                         which is right when tools/ sits inside the coaching folder (e.g. D:\\SF6-Claude-Coaching\\tools).
  SHOTOKAN_REPLAYS       capture files and videos. Default: $SHOTOKAN_HOME/replays
  SHOTOKAN_DB            the history database. Default: $SHOTOKAN_HOME/history/sf6.db
  SHOTOKAN_CAPTURE_DIRS  extra folders to search for captures, separated by os.pathsep (';' on Windows, ':' elsewhere).
  SF6_MOVES              move-name files (data/sf6_moves from the mods repo); read by shared_core_analyze.py.
  SHOTOKAN_PLAYER        the player in focus (your in-game name). Default: player_name in $SHOTOKAN_HOME/shotokan.json.
  SHOTOKAN_CFN_ID        their CFN ID. Default: cfn_id in shotokan.json.

shotokan.json (written by the plugin's setup, or by hand):
  {"player_name": ".shog", "other_names": ["shog"], "cfn_id": "1307078698", "main_character": "Cammy", "control": "Classic"}

A tools/.env file (KEY=value per line, # comments) is read first; real environment variables win over it.
"""
import json, os

TOOLS = os.path.dirname(os.path.abspath(__file__))


def _load_env(path=os.path.join(TOOLS, '.env')):
    if not os.path.exists(path):
        return
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()
HOME = os.environ.get('SHOTOKAN_HOME') or os.path.dirname(TOOLS)
REPLAYS = os.environ.get('SHOTOKAN_REPLAYS') or os.path.join(HOME, 'replays')
DB = os.environ.get('SHOTOKAN_DB') or os.path.join(HOME, 'history', 'sf6.db')


def _config():
    p = os.path.join(HOME, 'shotokan.json')
    if not os.path.exists(p):
        return {}
    try:
        return json.load(open(p, encoding='utf-8'))
    except ValueError:
        raise SystemExit(f'{p} is not valid JSON')


CONFIG = _config()
PLAYER = os.environ.get('SHOTOKAN_PLAYER') or CONFIG.get('player_name') or None
PLAYER_NAMES = [n for n in [PLAYER] + list(CONFIG.get('other_names') or []) if n]   # every name the player has used
PLAYER_CFN = os.environ.get('SHOTOKAN_CFN_ID') or (str(CONFIG['cfn_id']) if CONFIG.get('cfn_id') else None)


def require_player(given=None):
    """The player in focus: `given` if passed, else SHOTOKAN_PLAYER / shotokan.json. Stops with a clear message if neither is set."""
    who = given or PLAYER
    if not who:
        raise SystemExit('No player set: pass the player name, or set player_name in ' + os.path.join(HOME, 'shotokan.json') + ' (or SHOTOKAN_PLAYER).')
    return who


CAPTURE_DIRS = [REPLAYS, os.path.join(REPLAYS, '_to_delete')] + [d for d in os.environ.get('SHOTOKAN_CAPTURE_DIRS', '').split(os.pathsep) if d]


def find_capture(replay_id_or_file, extra=()):
    """A capture's path: tries <id>.json and <id>.json.gz in the given folders, then the capture folders. None if not found.
    Accepts a replay ID, a file name, or a stored path from another machine (only its file name is used)."""
    base = str(replay_id_or_file).replace('\\', '/').split('/')[-1]
    stem = base[:-3] if base.endswith('.gz') else base
    if not stem.endswith('.json'):
        stem += '.json'
    for d in [x for x in extra if x] + CAPTURE_DIRS:
        for name in (stem, stem + '.gz'):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    return None
