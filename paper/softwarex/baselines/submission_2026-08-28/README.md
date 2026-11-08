# SoftwareX submission baseline — 28 August 2026

Manuscript: `SOFTX-D-26-01135`, SeraEdit: Reliable Language-Guided MusicXML Editing
through Structured Score Patches. Frozen on 2 October 2026 before minor-revision work.

`files/` retains 25 unmodified, byte-preserving copies from the submission-ready
commit `a21acbea13d5a23f4aec9a438102e3dd25b8a5e4` (28 August 2026): manuscript sources,
DOCX/PDF, bibliography, figures, declarations and submission evidence. The current
pre-revision manuscript sources and binaries match that commit exactly. The manifest
records original Git blob IDs, SHA-256, byte counts and each source path.
The baseline file paths disable Git text conversion in `.gitattributes`, so Windows
`core.autocrlf=true` cannot change their bytes on a future checkout.

These are repository submission-ready files. The original files actually uploaded
to Editorial Manager and its assembled submission PDF have not yet been read in this
revision session; portal verification remains pending. Do not label this copy as an
independently verified copy of the Editorial Manager upload.

The software baseline is separately fixed at `v1.0.0`, commit
`b23afcf08c26c46625fc3f24d82882495de9348f`. The pre-revision checkout is
`a0702ec910691eaad2d4da43377ed831b531657d`; it includes later UI/branding fixes and
is not the software version deposited with the original paper.

The ignored local directory `artifacts/softwarex_revision_20261002/baseline_archives/`
retains both source snapshots, the original local archives/checksums, and a freshly
downloaded public manuscript archive. Its digest matches the GitHub Release asset:
`f3cdf06e2210aa7d9e37511067f5e7bed4e7cdea5b5b236457ba412b578d3444`.
The local pre-revision manuscript ZIP instead hashes to
`19468783babeb110dadb6694df7be2ac48762138830f3ff4fc43ddc48cc747b3`.
Both ZIPs pass CRC validation. The public archive predates final DOI insertion and
the manuscript's generative-AI declaration; it is not interchangeable with the
28 August submission-ready manuscript. The local source ZIP matches the public
source asset (`7ae6a9ab20c29279fb04872fee8fa549d4f6a361dba571821c38c608c4b4e0e6`).

Run these read-only checks from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\verify_softwarex_revision_baseline.py
.\.venv\Scripts\python.exe scripts\verify_softwarex_revision_baseline.py --include-local-archives
```

The second command requires this machine's ignored archive copies. Missing or
changed files fail with exit code 1; the checker never rebuilds or repairs a baseline.
Revision prose belongs in `../../revisions/2026-10_minor_r1/`, not in `files/`.
