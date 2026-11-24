"""Cache behavior.counts for every capture: beh_cache.json {replay_id: {player: counts}}"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import behavior, paths
DIRS = [d for d in paths.CAPTURE_DIRS if os.path.isdir(d)]   # SHOTOKAN_REPLAYS + SHOTOKAN_CAPTURE_DIRS (see paths.py)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'beh_cache.json')
cache = {}
for d in DIRS:
    for f in sorted(os.listdir(d)):
        if (f.endswith('.json') and len(f) == 14 or f.endswith('.json.gz') and len(f) == 17) and f[:9].isalnum() and f[:9] not in cache:
            try: cache[f[:9]] = behavior.counts(os.path.join(d, f))
            except Exception as e: print('skip', f, e)
json.dump(cache, open(out, 'w'))
print(len(cache), 'replays')
