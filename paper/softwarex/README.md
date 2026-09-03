# SoftwareX submission workspace

This directory contains the prepared Original Software Publication package for
SeraEdit 1.0.0.

- `manuscript/`: Markdown authority, SoftwareX v4 `elsarticle` source, bibliography,
  line-numbered DOCX and compiled, visually checked PDF.
- `figures/`: Mermaid source plus validated SVG, PNG and PDF architecture exports.
- `submission/`: cover letter, highlights, declarations and data/code statement.
- `dependency_licenses.*`: generated direct-dependency inventory.
- `release/`: deterministic source and manuscript archives with SHA-256 manifests.
- `package_verification.json`: machine-readable draft/submission readiness report.
- `VERIFICATION_REPORT.md`: commands, environment, results and limitations.
- `../../docs/softwarex/REVIEWER_GUIDE.md`: ten-minute offline reviewer path and
  evidence mapping to the SoftwareX reviewer questions.
- `../../docs/softwarex/HUMAN_REVIEW_PROTOCOL.md`: immutable 120-task review and
  conditional aesthetic-calibration protocol implemented by the local desktop UI.

Regenerate in this order:

```powershell
.\.venv\Scripts\python.exe scripts\generate_dependency_license_report.py
.\.venv\Scripts\python.exe scripts\run_reviewer_demo.py
.\.venv\Scripts\python.exe scripts\generate_softwarex_docx.py
.\.venv\Scripts\python.exe scripts\verify_softwarex_package.py --profile draft
.\.venv\Scripts\python.exe scripts\export_softwarex_package.py --preserve-existing-source
```

`--profile submission` must return exit code 0 before any journal upload. Public DOI
`10.5281/zenodo.22128976` identifies the immutable Zenodo copy of the SeraEdit 1.0.0
source release. Identity, rights confirmation, public repository visibility, and the
`v1.0.0` release metadata are complete.

The manuscript was submitted to SoftwareX on 28 August 2026 with manuscript number
`SOFTX-D-26-01135`. Its last recorded journal status is **Under Review**, confirmed
3 September 2026. The status is dated because Editorial Manager may change it without
changing the archived software release.
