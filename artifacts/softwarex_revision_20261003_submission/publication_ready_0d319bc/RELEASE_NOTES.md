# SeraEdit SoftwareX R1: scoped and validated MusicXML editing

This release preserves the original v1.0.0 deposit and supplies the SoftwareX minor-revision source and research-evidence snapshot. It repairs fixture reproducibility and archive completeness, adds the saved DeepSeek three-condition demonstration and a 200-case constructed-error study, and documents the native MuseScore saved-score bridge with screenshots and XML receipts.

The recorded demonstration reports strict editing success of 72/110 for Full Rewrite, 65/110 for Patch Only and 63/110 for Sera Full. Sera Full yields zero measured non-target changes among 73 output scores while erroneously refusing 34 executable requests. These results show a protection/completion tradeoff on a development benchmark; they do not establish overall superiority or held-out generalization. The 720-run rule-based replay is regression evidence on the same benchmark.

## Exact snapshot and validation

- Revision head: `0d319bc381cfc21687adaeff06dcb1f7797b8f18`.
- [Passing hosted CI](https://github.com/Selancee/Sera/actions/runs/37096317165): 447 Python tests from an isolated source ZIP, 133 frontend tests across 74 files, production build, 14 saved-live-evidence checks, and 4,359 source-file hashes.
- CI checkout: `a8535862f537ac91ea1331b94a29202908a3ca84`, a GitHub synthetic PR merge with the same tree as the revision head (`fb25ef220e28652f257c083f6f6473381e88ce48`). Main was not merged.
- Source and manuscript ZIP contents are unchanged from the CI artifacts; only the asset filenames identify this release. Internal archive version 1.0.0 is the historical software version; `softwarex-r1-20261003` identifies this separately archived revision.
- The manuscript snapshot captures the tested R1 preparation stage. Permanent-link fields and submission status in those documents are historical, not a claim that this is the final journal submission. Final submission documents will be prepared after archive publication.
- Fixed-seed melody integration tests provide bounded regression coverage; arbitrary-seed generation quality is not established.

## Contents and use

The source ZIP contains the application, evaluation code, frozen raw model outputs, benchmark and revision evidence. Follow its source-installation and offline reproducibility instructions. The companion manuscript snapshot has 95 verified files. The verification ZIP contains hosted-run metadata, JUnit results and replay reports. SHA256SUMS.txt records asset digests.

This is a source and evidence update. No new desktop installer is included. The original [v1.0.0 release](https://github.com/Selancee/Sera/releases/tag/v1.0.0) and [Zenodo 1.0.0 deposit](https://doi.org/10.5281/zenodo.22128976) remain the historical baseline.

Author: Yuan Gao, Zhejiang Conservatory of Music. ORCID: https://orcid.org/0009-0005-0394-3623. Code: MIT; synthetic benchmark: CC0-1.0; dependencies retain their own licenses. File-level SPDX sidecars preserve frozen producer bytes.
