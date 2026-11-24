# Changelog

Notable changes to the SHOTOKAN Claude plugin, newest first. Every push adds its changes here.

## 2026-11-24 (0.1.0)
- First version. Skills: shotokan-setup (new), sf6-replay-analysis, replay-review-prediction, sf6-review-dashboard, sf6-fgc-glossary, sf6-character-notes, sf6-drive-efficiency, sf6-coach-juzzy-sessions, sf6-coach-juzzy-tips, sf6-footsies-handbook-maj, and sf6-coach-shog as an example of personal rules.
- Skill copies made general: the player comes from shotokan.json (name, CFN ID, main character); personal paths and dashboard links removed; E.X. Dojo, Coosco and DoctaAfrikan checks skipped unless those skills are installed.
- Bundled: tools from shotokan-sf6/tools (894462f) and REFramework scripts and move data from shotokan-sf6/mods (64abfd7); scripts/sync_bundled.sh refreshes them.
- marketplace.json (with a description) so the plugin can be installed from this repo.
