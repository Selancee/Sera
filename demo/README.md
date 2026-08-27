# SoftwareX reviewer demo

This is the shortest auditable path through SeraEdit. It is offline, needs no API key,
does not open a browser, and does not use Gold patches to generate edits.

From the repository root after installing `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe scripts\run_reviewer_demo.py
```

The six default tasks cover transposition, dynamics, global key, structural meter,
staff-local voice movement and safe refusal. The command runs the same local generator,
transaction, protected-scope validation and source-preserving MusicXML export/re-import
used by the product. It writes resumable evidence to:

```text
artifacts/softwarex_reviewer_demo/
├── reviewer_demo_report.json
├── manifest.json
├── runs.jsonl
├── metrics.csv
├── failures.csv
├── raw_outputs/
└── host_outputs/
```

Expected console result:

```text
SoftwareX reviewer demo: 6/6 passed; host MusicXML outputs=5; report=...
```

`conflict_001` is expected to refuse and therefore produces no host MusicXML. The other
five outputs can be opened in MuseScore or another MusicXML-compatible notation host.

This demonstration is software verification, not remote-LLM performance or an aesthetic
study. See `docs/softwarex/REPRODUCIBILITY.md` for the full evidence classes and commands.
