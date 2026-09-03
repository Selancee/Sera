# SoftwareX Editorial Manager fill-in sheet

Verified against the live SoftwareX Guide for Authors and Editorial Manager entry on
28 August 2026. This began as the preparation sheet for the submission recorded below;
the retained field values remain the auditable record of what was prepared for upload.

## Recorded submission

- Journal: SoftwareX
- Manuscript number: `SOFTX-D-26-01135`
- Submitted: 28 August 2026
- Last confirmed status: **Under Review** on 3 September 2026

## Official entry points

- Journal: https://www.sciencedirect.com/journal/softwarex
- Guide for authors: https://www.sciencedirect.com/journal/softwarex/publish/guide-for-authors
- Editorial Manager: https://www.editorialmanager.com/softx/default.aspx

## Submission identity

- Article type: Original Software Publication
- Title: SeraEdit: Reliable Language-Guided MusicXML Editing through Structured Score Patches
- Author: Yuan Gao
- Corresponding author: Yuan Gao
- Email: selanceg@gmail.com
- ORCID: 0009-0005-0394-3623
- Affiliation: Zhejiang Conservatory of Music
- Postal address: No. 1 Zheyin Road, Zhuantang Street, Xihu District, Hangzhou,
  Zhejiang Province, China 310024

## Abstract

SeraEdit is local-first research software for reliable language-guided editing of
symbolic scores. Rather than asking a language model to rewrite an entire MusicXML
document, it represents a request as a versioned ScorePatch bound to stable event
identifiers, target and protected scopes, and a source fingerprint. Layered validators
check schema, score structure, duration, notation relations, protected content, and
MusicXML round-trip fidelity inside an atomic transaction. A desktop interface and
MuseScore bridge expose proposals, diffs, rejection reasons, and undo without silently
overwriting the host score. The release includes 20 synthetic scores, 120 editing
tasks, three evaluation conditions, resumable experiment tooling, and offline fixtures
for reproducible software verification.

## Keywords

MusicXML; symbolic music; score editing; structured patches; validation; research software

## Repository and archive

- Repository: https://github.com/Selancee/Sera
- Tagged release: https://github.com/Selancee/Sera/releases/tag/v1.0.0
- Zenodo version DOI: https://doi.org/10.5281/zenodo.22128976
- Zenodo concept DOI: https://doi.org/10.5281/zenodo.22128975
- Software license: MIT
- Synthetic benchmark license: CC0-1.0

## Declarations

- Funding: This research did not receive any specific grant from funding agencies in
  the public, commercial, or not-for-profit sectors.
- Competing interests: no known competing financial interests or personal relationships.
- Originality: the manuscript is original and is not under consideration elsewhere.
- CRediT: Yuan Gao — Conceptualization, Methodology, Software, Validation,
  Investigation, Data curation, Writing – original draft, Writing – review & editing,
  Visualization.
- Generative AI disclosure: use the exact text in `GENERATIVE_AI_DISCLOSURE.docx` and
  retain the matching disclosure section already placed before the manuscript references.

## Recommended upload order

Use the Word route because the current main DOCX is editable, single-column, and embeds
the manuscript figure.

1. Main manuscript: `../manuscript/seraedit_softwarex.docx`
2. Figure source if requested: `../figures/figure1_architecture.pdf`
3. Highlights: `HIGHLIGHTS.txt`
4. Cover letter: `COVER_LETTER.docx`
5. Declaration of interest: `DECLARATION_OF_INTEREST.docx`
6. CRediT statement: `CREDIT_AUTHOR_STATEMENT.docx`
7. Generative AI disclosure if requested separately: `GENERATIVE_AI_DISCLOSURE.docx`
8. Data and code availability: `DATA_AND_CODE_AVAILABILITY.docx`

The PDF is a review copy, not the editable Word source. Upload the release/source ZIP
only if Editorial Manager provides an explicit software, supplementary-material, or
source-code category; the public GitHub release and Zenodo DOI remain the canonical
software deposits.

All upload DOCX files are rebuilt with hidden creator, last-editor, generation-tool,
creation/modification timestamps and local filesystem paths removed. The PDF source
sets authoring-tool and timestamp metadata to empty. Visible author identity and the
required generative-AI disclosure remain intentionally present for single-anonymized
review and publication ethics.

## Live guide limits checked

- Single anonymized review; author identity remains in the manuscript.
- Main text maximum: 4000 words, using the journal-specific template.
- Figures maximum: 6.
- Abstract maximum: 250 words.
- Keywords: 1-7.
- Highlights: 3-5 bullets, each no more than 85 characters including spaces.
- Word source: editable `.doc` or `.docx`, single column, with figures embedded.

## Author-controlled final checks

- Sign in with the matching Elsevier account or ORCID and confirm the profile email.
- Confirm the exact article-type label shown by Editorial Manager.
- Review the current open-access APC and identify the payer before final submission.
- Check every system-generated declaration and the assembled reviewer PDF.
- Approve the exact manuscript and click the final submission control only after review.
