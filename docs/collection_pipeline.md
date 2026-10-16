# Source queue → expert dispatcher (local research integration)

**Status:** PARTIAL / local acceptance only. This is **not** a hosted scheduler, licensed live lineup service, or a production prediction system.

## Use

```python
from experts.collection_pipeline import CollectionPipeline

pipeline = CollectionPipeline(runtime)
source_job_id = pipeline.request(fixture, "openfootball", {"league": "de.1", "season": "2025-26"}, as_of)
# An independently scheduled, policy/quotas guarded v2 source worker executes:
# runtime.queue.work_one(fetcher=..., clock=...)
# Only AFTER the above worker completes and saves a snapshot:
expert_task_id = pipeline.bind(fixture, source_job_id, exact_native_match_id, as_of)
# One worker assigned the 'source_hunter' role can execute the verified task:
status = pipeline.dispatcher.work_one("worker-id", "source_hunter")
```

The worker's output is stored in `expert_task_outputs` as append-only output and is **fixture metadata only**. It includes a snapshot SHA, native match id and observed time. **Neither a parsed fixture nor a source snapshot proves lineup news publication, kickoff time if the provider gave date only, or odds.** The workflow reports those as `not_proven`. Models must not run merely because this task returned `ready`.

`Queue.enqueue(..., cycle=YYYY-MM-DD)` creates distinct jobs on successive dates while maintaining same-day idempotency. Existing legacy callers without `cycle` continue to use the original job IDs. A new local table `v2_job_snapshots` links cached collection jobs to the original immutable snapshot, preserving observation time, bytes, quota ledger and provenance without copying the snapshot. This is **SQLite local schema only**; no Supabase migration has been applied.

The source worker now checks its lease **inside a write transaction** before saving raw source bytes, normalized results, cached links or marking a task done. Expired or superseded workers cannot publish results after losing their lease. Network requests may already have been charged to the existing request ledger; lease fencing cannot cancel an in-flight HTTP operation.

Sources must currently have verified status, a nonempty license, an HTTPS terms URL, a completed `reviewed_at` date and an unexpired review window. All requested provider permissions are still subject to independent rights verification; a code-level policy flag is not a legal authorization by itself.

## Executable validation

```bash
python -m unittest tests_phase2.test_queue tests_experts.test_collection_pipeline tests_experts.test_source_bridge -q
python -m unittest discover -s tests_experts -q
python -m unittest discover -s tests_foundation -q
```

The fake HTTP integration tests never make live network requests. True hosted Auth/JWT/RLS, external data access, scheduler/workers, independent review ablation, ongoing learning, and the disabled virtual pilot remain outstanding.
