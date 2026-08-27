# SoftwareX submission checklist

## Prepared locally

- [x] Original Software Publication Sections 1-5 follow SoftwareX v4 structure.
- [x] Main text is below 3000 words; abstract is approximately 100 words.
- [x] Six keywords or fewer and one manuscript figure.
- [x] Mandatory C1-C9 code metadata and optional S1-S8 executable metadata included.
- [x] MIT root license and CC0 benchmark license present.
- [x] Direct dependency/license inventory and third-party notices present.
- [x] Installation, user, API and reproducibility documentation present.
- [x] CFF and CodeMeta citation metadata present.
- [x] Architecture source and SVG/PNG/PDF exports validated and visually inspected.
- [x] 120-task automatic benchmark validation passed.
- [x] Local immutable benchmark-review UI, export, host inspection and calibration gate tested.
- [x] Human benchmark review frozen: 120/120 current primary decisions, 30/30
      stratified repeat checks, zero stale records and a hashed JSON/CSV audit trail.
- [x] Ordinary product build hides the research-review workspace; source reviewers can
      explicitly enable it with `VITE_SERA_ENABLE_RESEARCH_REVIEW=true`.
- [x] 360-case offline verification and evidence drift checks passed.
- [x] Python/frontend regression, frontend build and Windows package smoke passed.
- [x] Line-numbered DOCX with embedded figure and metadata tables generated.
- [x] Deterministic source/manuscript ZIP archives and SHA-256 manifests generated.
- [x] Cover letter, highlights, CRediT, competing-interest, AI-use and availability drafts prepared.

## Must be completed by the author before upload

- [x] Supply the support email; author, affiliation, ORCID and funding metadata are filled.
- [x] Confirm the drafted sole-author CRediT roles and competing-interest statement.
- [x] Confirm every contributor/copyright owner authorizes the MIT code release and
      the benchmark owner authorizes the CC0 dedication.
- [x] Make `https://github.com/Selancee/Sera` publicly readable and inspect it logged out.
- [x] Review the release diff; exclude private/user-owned files; commit with authorization.
- [x] Create immutable release tag `v1.0.0` and publish checksummed release assets.
- [x] Create a Zenodo software deposit for the exact `v1.0.0` source archive, upload it,
      reserve DOI `10.5281/zenodo.22128976`, and insert the DOI/URL.
- [x] Replace C2/C3/S2/S3 and repository citation with immutable release URLs and the
      reserved Zenodo DOI.
- [ ] Publish Zenodo record `22128976`, then mark `archive_status: published` and
      `archive_published: true` in `docs/softwarex/publication.yml`.
- [x] Compile and visually inspect the LaTeX PDF; final template conformity must still
      be confirmed against the current official downloadable template before upload.
- [ ] Run `scripts/verify_softwarex_package.py --profile submission` and require exit 0.
- [ ] Inspect both final ZIPs and their SHA-256 hashes.
- [ ] Confirm all authors approve the exact manuscript and understand the current APC.
- [ ] Upload through Editorial Manager manually; do not delegate account/identity actions.
