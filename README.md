# SHOTOKAN plugin

SF6 replay reviews from your own capture files. Watch a replay in SF6 with the bundled REFramework scripts, then ask Claude to review the set.

## What it does
- **Setup** (`shotokan-setup`): coaching folder, your name / CFN ID / main character, the Python tools, the history database and the capture scripts.
- **Reviews** (`sf6-replay-analysis`): runs the analyzer on capture files, writes a Full or Quick review (damage sources, Drive economy, decision presses, player reads and spectra, habits, fixes) and adds the set to your history database.
- **Blind predictions** (`replay-review-prediction`): predicts each set before it's analysed, from pre-set facts only, and grades the prediction afterwards.
- **Dashboards** (`sf6-review-dashboard`): an optional review dashboard per set.
- **Reference** (`sf6-fgc-glossary`, `sf6-character-notes`, `sf6-drive-efficiency`): terms, character baselines and Drive valuation.
- **Coaching sources**: Juzzy's sessions and tips, and Maj's Footsies Handbook (paraphrased, credited).
- **Example personal rules** (`sf6-coach-shog`): .shog's own coaching rules and theories, as an example of rules you can keep, edit or replace.

## Requirements
- Claude desktop app with a connected folder (the coaching folder).
- Python 3.10+ on your computer.
- SF6 on PC with REFramework.
- Optional: OBS for video, a Buckler login for pulling replay IDs.

## Install
- In Claude: upload a `.plugin` file built from this repo (zip the repo contents), or add this repo as a plugin marketplace (`shotokan-sf6/claude-brain`) and install `shotokan`.
- Then say "set up SHOTOKAN".

## Bundled
- `tools/`: the analyzer, history database, decision presses, blind manifest and other tools from github.com/shotokan-sf6/tools.
- `mods/`: the REFramework capture and move-export scripts and move-name data from github.com/shotokan-sf6/mods.
- Refresh both with `scripts/sync_bundled.sh <tools checkout> <mods checkout>`; don't edit the bundled copies here.

## Not included
E.X. Dojo, Coosco and DoctaAfrikan coaching skills. Skills that mention them skip those checks unless you install them yourself.

## Known gaps (0.1.0)
- The Replay Tracker sheet and named dashboards are .shog's; other players set their own links in `shotokan.json`.
