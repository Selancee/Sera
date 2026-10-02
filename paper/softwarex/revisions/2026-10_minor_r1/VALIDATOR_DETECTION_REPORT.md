# Validator detection study — 2026-10-02

Frozen post-fix producer: `230dbf7aeb0638121c9defa274a8a656f4192ac9` (clean working tree).
Evidence: `experiments/softwarex_validator_detection_200_v1/`.

## Design and results

20 existing synthetic source scores; nine constructed invalid patches and one canonical-valid control per score: 180 mutations + 20 controls. No LLM or Gold patch generated these cases. Each label has a construction-based explanation, and each saved case includes its full patch and transaction result.

| Mutation | Expected code | Pre-fix targeted detections | Post-fix targeted detections |
|---|---|---:|---:|
| duration_overflow | E07 or E08 | 20/20 | 20/20 |
| missing_event | E06 | 20/20 | 20/20 |
| missing_schema | E04 | 20/20 | 20/20 |
| orphan_slur | E10 | 20/20 | 20/20 |
| orphan_tie | E09 | 20/20 | 20/20 |
| preserve_pitch_violation | E12 | 20/20 | 20/20 |
| protected_edit | E11 | 20/20 | 20/20 |
| stale_source | E05 | 20/20 | 20/20 |
| wrong_dynamic_semantics | E15 | 0/20 | 20/20 |

Duration mutations produced E07 in eight cases and E08 (voice collision) in twelve; both detect the intended timing fault. All 180 invalid patches were rejected after the fix. All 183 rejections (including three controls) returned the original fingerprint. Caller-owned score objects remained unchanged in all 200 cases; there were no exceptions.

The pre-fix wrong-dynamic cases had **0/20 targeted semantic detections**. Three happened to be rejected by the XML round-trip checker for a different reason. Thus generic rejection (3/20) must not be misreported as semantic detection. The new `dynamic_equals` check detects 20/20 on the same cases: this is regression evidence after diagnosis.

## Controls and limitations

The pipeline accepted 17/20 canonical-valid controls and rejected 3/20 (15%). The rejected controls use scores 006, 012 and 018: changing a principal note dynamic changes a grace-note dynamic on XML round-trip, producing E14. This is an export/representation limitation. The round-trip checker correctly sees a mismatch, so 15% is the end-to-end rejection rate for canonical-valid edits, not an isolated checker false-positive estimate.

Pilot v1 also selected individual chord members; five of those controls could not preserve per-note dynamics in the exported representation. Pilot v2 excludes chord/simultaneous-onset anchors by construction. Pilot summaries and full v2 pre-fix evidence remain preserved; no unfavorable final cases were removed.

These constructed faults do not estimate real-model error frequencies, validate arbitrary instruction semantics, or establish generalization. Each family has only 20 cases derived from the same score set. The source-binding and structural checks can reject a patch independently of the intended injected fault; the table therefore requires the designated code, not merely any rejection.

The test is intentionally narrow: other recognized effect names that are not semantically checked are not certified. Input parsing, additional notation families and adversarial compositions would require further studies.

## Reproduction

```powershell
.\.venv\Scripts\python.exe scripts/run_validator_detection_study.py --output artifacts/validator_detection_new_run
```

Use a new output directory; the script refuses to overwrite evidence. The saved summary includes source SHA-256 hashes and a hash of the full case file.
