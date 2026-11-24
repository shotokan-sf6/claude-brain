---
name: "sf6-replay-analysis"
description: "Analyze Street Fighter 6 replays from REFramework capture files (when present) and recordings (video or screenshots): read the frame meter and HUD, log key moments by round and round timer, check against SuperCombo frame data, report both players' habits and fixes, and log the player's replays to their SF6 Replay Tracker sheet."
---

# SF6 replay analysis

The entry point for every SF6 replay review. A review runs in tiers, each a separate skill; load them with the Skill tool in this order and follow each in turn:

| Review | Tiers, in order |
|---|---|
| **Quick** | `shared-core-review` → `quick-review-report` |
| **Full** | `shared-core-review` → `quick-review-report` → `full-review-report` |
| **Tournament** | Full, plus the Tournament section of `full-review-report` |

- **shared-core-review:** setup, played order, the blind prediction, the analyzer, capture storage, the sf6.db ingest, grading, and the rules every review follows (wording, rank labels, throws vs throw techs, Drive Rush classes, lethal burnouts, incomplete sets).
- **quick-review-report:** the stats layer: generated reads and habits in sf6.db, the numbers to pull, lessons held, and the Quick reply. In a Full review it is the starting draft.
- **full-review-report:** the hand-written layer: guideline skills, frame data, video checks, chess or poker, the review_docs datasets, the Full reply, Tournament reviews.

**Choosing the depth:** what the player asks for ("Quick Review", "Full Review", "Tournament"). If they don't say, **Quick for sets the player won, Full for sets they lost**, decided once the analyzer gives the result (shared-core-review step 5). Load `shared-core-review` first either way: the prediction has to be written before any result is seen. Say which depth each set got.

**Several sets at once:** run shared-core-review for each set (each with its own prediction before its analyzer run), then the Quick or Full tiers per set.

**Naming:** the tiers' scripts follow the same prefixes (`shared_core_*.py`, `quick_review_*.py`, `full_review_*.py` in `<coaching folder>\tools\`), and so do their reference files (each tier's `references/` folder).

The tiers exist so each can be tuned on its own.
