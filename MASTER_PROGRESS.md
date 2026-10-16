# Master progress — 2026-10-16

Delivery update: 453240f and d3e45a8 are verified remote commits for dispatcher
and its nine tests. No longer blocked on delivery: browser upload works.
Further local increment: immutable bounded task inputs, late-binding rejection;
11 dispatcher tests pass. Latest full regression: 232 run, 225 passed, 7 skipped.

Final regression: 230 run, 223 pass, 7 skips. Push BLOCKED by missing Git
HTTPS authentication. Local commit fb8d494; PR #1 has not received this increment.
Git bundle preserves changes. No new cloud tests or migrations.

Remote starting point verified: feature/expert-engines at 5b54b79; PR #1.
Local and remote tracked trees matched before development; their histories were
merged without changing source files. Main and migrations 001–005 unchanged.

| Task | Status | Remaining acceptance |
|---|---|---|
| 1 Data/research | PARTIAL | Dispatcher added locally; actual validator binding tested. Collection-to-evidence persistence, all other handler bindings, hosted execution and live acceptance remain. |
| 2 Prediction | PARTIAL | Existing models preserved; multi-season acceptance and separately validated calibration remain. |
| 3 Review | PARTIAL | Existing deterministic review preserved; independent ablation remains. |
| 4 Portfolio/learning | PARTIAL | Existing preview/journal preserved; new policy and full settlement scope remain. |
| 5 Automation/dashboard | PARTIAL | Local dispatcher only; dashboard and disabled daily workflow not implemented in this increment. |
| 6 Pilot/learning/radar | NOT_STARTED | Pilot remains off; JWT and live odds gates open; radar not implemented. |

Role detail remains in EXPERT_PROGRESS.md. This increment changes roles 01 and
03 only. All other role claims remain as previously documented, not FULL by
virtue of having registry entries.

Dispatcher guarantees: transactional output/completion, immutable results,
dependency outputs, role-filtered leases, sanitized retry errors, cancellation,
expired-worker fencing. Handlers must be pure or independently idempotent;
lease fencing does not undo external side effects or stop a running process.
SQLite is a trusted-process boundary, not hosted authorization.

Tests: full suite at seven dispatcher tests: 228 run, 221 pass, 7 skip.
After adding two more boundary tests: dispatcher 9/9 pass. A final full run
is required before claiming 230-test full regression acceptance.
No fresh native/PGlite/hosted run claimed by this increment.

Next: durable immutable input envelopes; collection job linkage; actual
model/review handler bindings; live source-policy revalidation. Then proceed
through tasks 2–6 without enabling deployment or pilot.
