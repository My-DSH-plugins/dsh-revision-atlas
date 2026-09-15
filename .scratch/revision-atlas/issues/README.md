# Tickets — revision-atlas

Tracer-bullet tickets, worked blockers-first (extractor → everything else).

| # | Ticket | Blocked by | Blocks |
|---|---|---|---|
| [0001](0001-extractor.md) | Extractor: inventory + link graph + closure | — | 0002 |
| [0002](0002-structure-plan.md) | Structure plan + Gate 1 | 0001 | 0003, 0004 |
| [0003](0003-leaf-plan.md) | Leaf plan + Gate 2 | 0002 | 0005, 0006 |
| [0004](0004-renderer.md) | Renderer (module map) | 0002 | 0007 |
| [0005](0005-leaf-generator.md) | Leaf generator | 0003 | 0006, 0007 |
| [0006](0006-notebook-generator.md) | Notebook generator | 0003, 0005 | 0007 |
| [0007](0007-verifier.md) | Verifier + coverage report | 0004, 0005, 0006 | — |

Open decisions that gate a specific ticket are noted in that ticket's file. The
two that gate later work: **flip implementation** (0006) and the **diagram-kind
classifier** (0005, §15).
