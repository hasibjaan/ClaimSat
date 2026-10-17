---
description: Build a ClaimSat phase from the build plan
argument-hint: <phase number, e.g. 0>
---

Build **Phase $ARGUMENTS** of ClaimSat.

1. Read `CLAUDE.md` and the Phase $ARGUMENTS section of `CLAIMSAT_BUILD_PROMPT.md`, plus the shared rules at the top of that file.
2. Check what earlier phases already built, so you extend it rather than redo it.
3. Build only this phase. Ask before creating cloud resources or deploying.
4. Run every acceptance check listed for this phase.
5. Finish with a short report: what you built, how to run it, each acceptance check (pass/fail, with output for failures), and any manual steps the team must do. Then stop and wait.
