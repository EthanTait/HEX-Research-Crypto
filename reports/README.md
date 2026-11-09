# reports/

Course deliverables and the figures they use.

```
reports/
├── research-plan/          # individual plans as submitted (Oct 7)
├── milestones/
│   └── milestone-1/        # INSTRUCTIONS.md (course sheet), PLAN.md, milestone-1.md + .html (figures embedded)
├── tick-study/             # separate pathway for Hank's tick capture (decided 2026-11-09)
├── paper/                  # final research paper (later)
└── slides/                 # presentation (later)
```

Every figure in a deliverable is produced by a script in `python/scripts/` and embedded in the deliverable's html by `build_report.py`; no png is tracked. Large binaries (pptx/pdf) are fine in moderation; commit the submitted versions only.
