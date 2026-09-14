# Link-following and content coverage are enforced by a machine-checked invariant, not by the generator

---
Status: accepted
---

Course markdown cross-links sidecars (for/against pairs, per-domain stress
tests, collapsible catalogs), and a formatting-only notes skill proved it
silently drops exactly that content — 12 collapsibles and 5 for/against
sidecars vanished because nothing required coverage. We decided the atlas must
enforce coverage with a machine-checked invariant, not a prompt: (1) a
deterministic inventory that closes over every corpus file; (2) a
human-reviewed spec whose leaves carry a checklist of the source items that
must survive; (3) a generator fed that checklist under an exhaustiveness bar;
and (4) a verifier that re-parses each artifact and reports coverage, failing
under threshold. The reason is that a model obeys whichever contract it is
given — "100% accuracy" is only achievable when the constraint is a script, and
the one thing that must never happen is a silent omission.

**Consequences**: every corpus file is classified exactly once and an
unclassified file fails the build; a leaf without a verified checklist is
`needs-review`, never silently shipped; the price is a spec file to maintain
and a verifier to write, in exchange for "no silent failures" being checkable
rather than hoped for.
