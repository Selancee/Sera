# SoftwareX reviewer guide

This guide maps the SoftwareX reviewer form to the smallest concrete SeraEdit evidence.

## Ten-minute path

1. Follow `INSTALLATION.md` to create the Python environment.
2. Run the offline product demonstration:

   ```powershell
   .\.venv\Scripts\python.exe scripts\run_reviewer_demo.py
   ```

3. Confirm `6/6 passed`, an empty `failures.csv`, and five files under
   `artifacts/softwarex_reviewer_demo/host_outputs/`.
4. Open one resulting MusicXML file in MuseScore when a visual host check is desired.
5. Inspect `reviewer_demo_report.json`; it records that generation was local/offline and
   did not receive Gold patches.

## Reviewer-question map

| Reviewer concern | Direct evidence |
| --- | --- |
| Does the software run as described? | `scripts/run_reviewer_demo.py`; packaged smoke in `VERIFICATION_REPORT.md` |
| Can the described behavior be reproduced? | `demo/README.md`; `REPRODUCIBILITY.md`; resumable raw/metric outputs |
| Is source/executable behavior tested? | 408 Python tests, 120 frontend tests, GitHub Actions workflow, Windows package smoke |
| Is the architecture understandable? | manuscript Figure 1; `docs/architecture/`; typed `ScorePatch` schema |
| Are code and data documented? | `API_REFERENCE.md`, `USER_MANUAL.md`, benchmark card and schema files |
| Is the environment specified? | `INSTALLATION.md`, lock files, experiment manifests and dependency hashes |
| Is there an appropriate license? | root MIT `LICENSE`; benchmark CC0-1.0 `benchmark/LICENSE` |
| Are limitations explicit? | manuscript Sections 3-5 and `REPRODUCIBILITY.md` evidence boundaries |

## Full verification path

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend test -- --run
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe scripts\validate_benchmark.py --split core --write-report
.\.venv\Scripts\python.exe scripts\verify_softwarex_package.py --profile draft
```

The frozen publication evidence is stored in the four allowlisted
`experiments/softwarex_*` directories. The 360-case fixture is explicitly non-formal;
the 720-run product replay is deterministic acceptance evidence, not remote-model
accuracy. The 120-task human review used one pseudonymous reviewer for both passes and
therefore does not establish inter-rater reliability.

## Host and security boundary

SeraEdit never overwrites the score currently open in the notation host. It produces a
separate reviewed MusicXML revision, which the user may inspect and save. API keys are
not needed for this reviewer path and are never included in the repository or evidence.
