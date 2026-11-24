---
name: "sf6-review-dashboard"
description: "Format for SF6 replay-review dashboards (like \"splash-test\" and \"tuning skills\"): Data-type artifact sections, dataset schemas, page CSS/helpers, and local copies + standalone HTML. Use whenever an SF6 review goes into a dashboard."
---

# SF6 review dashboard format

> **Installed skills only.** This plugin ships the analysis, prediction, dashboard, glossary, character notes, Drive efficiency, Juzzy and Maj skills, and .shog's coaching rules as an example. Other coaching skills named in this text (E.X. Dojo, Coosco, DoctaAfrikan) aren't included: load them only if the player has installed them, otherwise skip those checks.


Use this when an SF6 replay review (sf6-replay-analysis) is put into a dashboard. Keep this layout unless the player asks for changes. If he edits a dashboard's formatting by hand, offer to update this skill from his version.

**Reference files.** The detail lives in this skill's `references/` folder (`${CLAUDE_PLUGIN_ROOT}/skills/sf6-review-dashboard/references/`). Read a file when the step below names it, before doing that step, not from memory; the rules in this file always apply.

## 1. Terms (use these everywhere: page text, dataset names, summaries)
- **Round**: one life bar. A **game** is one replay (one replay ID), made of 2 or 3 rounds.
- **Set**: a group of games between the same two players. Formats:
  - **FT2** (first to 2 game wins), also called **BO3** (best of 3). This is a ranked set.
  - **FT3** (first to 3), also called **BO5**.
  - **FT5** (first to 5), also called **BO9**. This one is rarer.
- **Grouping games into sets:**
  - Use the sets the player specifies.
  - If he submits games together and both players are the same in all of them, assume they form a set.
  - If the grouping is unclear, ask before building. Examples: more games than one set's format allows, or a score that doesn't fit the format.
  - A dashboard can hold several sets. Group everything by set, then by game. The page shows one set at a time, chosen with the "Show set" picker (section 5).
- Never call a game a "set", and never call a round a "game".
- Score notation:
  - **Game score**: rounds won within one game ("2-1", P1 first).
  - **Set score**: games won within a set ("3-2", P1 first).

## 2. Artifact and data
- Make the dashboard from the **Data** artifact type (list_types → create_from_type), titled as the player names it (e.g. the folder name). One dashboard per review.
- All data is in **attached JSON files** (upload_asset), declared as `datasets/<id>` with:
  - `source: {kind:"file", url, name, format:"json"}`
  - `fixed: true`
  - `updated: {at, by:"Claude"}`
  - When a file changes, re-upload it, then `update` the dataset's `source.url` and `updated`.
- Refer to players by their in-game names.
  - P1 is the player in focus: The player, or whoever the player asks to review. P2 is the opponent.
  - Column names use lower-case player prefixes (`<p1>_…`, `<p2>_…`).
- Every dataset row has a unique id column, which the page uses as `data-row-key` (`archetypes` rows use `arch_id`).
- Every row in every dataset has `set_id` (archetypes, habits, punish, findings, fixes and training too), so the page can show one set at a time. When adding a set to an existing dashboard, keep the old rows and append the new set's rows with new ids.
- **Don't track total damage dealt.** No damage-dealt tiles, per-game damage charts or damage totals. Damage only appears as the *share* behind situations and lenses, and per hit in the hidden hits table.
- **Rounds are light.** Record each game's round score and who won each round. Don't build a rounds table or a "who wins which round" chart.

## 3. Datasets (ids, columns)
One attached JSON file per dataset: `sets`, `games`, `hits`, `events`, `archetypes`, `resources`, `parries`, `habits`, `story_games`, `story`, `punish`, `findings`, `fixes`, `training`; the page computes the rest (kpis, sit_pct, lens_pct, kind_counts, res_totals, sup_totals, ov_econ, econ, parry_sum). Every column, every calc and how to read the counts: `references/datasets.md`. Read it before writing or changing any dataset.

## 4. Lens: what P1 was doing when hit
Give every hit P1 takes one `lens` group, using these names exactly: Challenging pressure; Challenging okizeme; Counter-hit at mid range; Whiff punished; Walked in; Teched a throw; Blocking, opened up; Jumped; Jumped in on (no anti-air); Own offense beaten by a reversal; Drive Rush / Impact checked; Unsafe move punished; Pressed after turn ended; Unclear / super. What each group covers: `references/lens-and-story.md`.

## 5. Page layout (top to bottom)
Sections, in this order: 1. Header; 2. Where the damage came from; 3. KPI tiles; 4. Hits landed by kind; 4b. Drive and super spending; 4c. Drive economy; 5. Player reads; 6. Habits; 7. Story of the Set; 8. Punishes; 9. Fixes and drills; 10. Suggested training routine for <P1>; 11. Findings by skill; 12. All hits; 13. How these numbers were made. What goes in each (ids, charts, colours, wording): `references/page-layout.md`. Read it before building or changing the page.

## 6. Story of the Set (the backbone of the review)
The story explains how the guideline skills' findings played out: a set overview card (top 3 highs and lows, then findings by category) and one card per game, with New / Improved / Regressed tags and Low-confidence notes folded away. Write it after the other datasets, with evidence (game, round, timer) for every claim. Columns, categories and layout: `references/lens-and-story.md`.

## 7. Page rules
- The first line is `<meta name="dash-one-writer">`.
- All fixed text is in the HTML. Data-driven parts are `data-draw` elements stored empty or with `—`.
- Tables:
  - `<table data-source="<id>" data-row-key="<key>">`
  - `<th data-field="<col>">`, adding `class="n"` for numbers
  - an empty `<tbody data-draw="t_<id>">`, filled by `ST.table`
- KPI numbers: `<div class="st-big" data-draw="k_…" data-source="kpis">—</div>`, with the "P1 / P2" label under each as `<div class="st-label" data-draw="kl0" data-source="sets">—</div>` (kl0-kl4).
- Legends: `<div class="st-legend" data-draw="leg_sit" data-source="sets"></div>` (and `leg_kind`), drawn with `ST.swatch` from the chosen set.
- Charts: `<div class="st-chart" data-draw="c_…" data-source="…">`. Each chart has a tooltip, value labels, `role="img"` and an aria-label.
- After writing, read `data/users/<me>/check` (it must be `passed`) and `runs` (it should not exist).

## 8. CSS (use as is)
Copy `references/page-css.html` into the page as is (it is the `<style>` block). Every `<select>` relies on it.

## 9. Shared script helpers (use as is)
Set `ST.P1` (the player in focus; P2 always comes from the chosen set's row in `sets` via `ST.p2()`), and add the `ST.table(...)` calls and the one-value KPI drawings for this review. The KPI drawings look like `dash.draw('k_burn', ST.pair('burnouts'))`.

(The script is in `references/helpers.js`: copy it into the page as is.)
HTML hooks the page needs:
- Header and set picker: `h_title`, `h_sub`, `set_pick` (on `#set-pick`); legends `leg_sit`, `leg_kind`; KPI labels `kl0`-`kl4`; P2 habits label `hab_p2_label`; hits filter options `hit_filter_opts` (on `#hit-filter`). Add any new draw name to `ST.REDRAW`.
- Charts: `c_sit`, `c_lens`, `c_kinds`.
- KPI tiles: `k_burn`, `k_aa`, `k_ch`, `k_pc`, `k_pp`, drawn with `ST.pair('burnouts' | 'anti_airs' | 'counter_hits' | 'punish_counters' | 'perfect_parries')`.
- Cards and lists: `arche`, `habits_p1`, `habits_p2` (in `.st-two`), `story`, `fixes` (in `.st-cards`), `training`, `findings` (in `.st-cards`, inside the closed details).
- Tables: `t_punish`, and `t_hits` (inside the closed details, with the `#hit-filter` select).

## 10. Local copies
Save to `<coaching folder>\reviews\<YYYY-MM>\<review folder>\review\` (folder naming as in shared-core-review; write via /mnt/user-data/outputs + device_commit_files):
- `<name>.html`: a standalone page for the player's webserver.
  - Same HTML without the meta line.
  - d3 **inlined** (not from a CDN).
  - Data embedded as `window.__DATA__`.
  - A small `window.dash` shim (data/calc/draw/colors/onData/params no-ops; calc runs the fn on the embedded data) that runs the drawings on load and on resize.
  - The CSS tokens defined in `:root`, with a `prefers-color-scheme: dark` block.
  - Before saving, check it in headless Chromium: no page errors, header and story filled.
- `<name>-summary.md`, in this order: result (sets and games), Story of the Set (overview, then games), habits, punishes, player reads, fixes, training routine, findings by skill, method. The pop quiz is optional, at the end.
- `data\*.json` and `data\*.csv` for every dataset.

## 11. Hand-over
Tell the player:
- the dashboard link;
- the set result(s);
- the top 3 highs and lows;
- the top fixes;
- what's approximate (starters, situations, lens groups, perfect parries, anything marked Low confidence);
- where the local copies are.
