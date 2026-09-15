# 0006 — Notebook generator

- **Blocked by:** 0003, 0005
- **Blocks:** 0007
- **Status:** blocked on the flip decision

## Goal

Per-leaf paged notebook with a flip interaction and shared assets (vendored
handwriting font + template + flip JS) per §9. Vendored look, no runtime skill
coupling.

## Acceptance

- notebook has N pages sized by the checklist; flip works offline and on touch
- pages are HTML fragments with real text (the verifier can parse them)
- shared assets are cached once per module

## Open decision (blocks this ticket)

- **Flip implementation**: StPageFlip (verify license + maintenance) vs hand-rolled
  CSS 3D. Choose before starting this ticket.
