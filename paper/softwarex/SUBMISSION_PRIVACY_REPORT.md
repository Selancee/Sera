# SoftwareX submission privacy report

## Scope

This report covers the files prepared for direct journal upload:

- `manuscript/seraedit_softwarex.docx`;
- `manuscript/seraedit_softwarex.pdf`;
- `submission/COVER_LETTER.docx`;
- `submission/DECLARATION_OF_INTEREST.docx`;
- `submission/CREDIT_AUTHOR_STATEMENT.docx`;
- `submission/GENERATIVE_AI_DISCLOSURE.docx`;
- `submission/DATA_AND_CODE_AVAILABILITY.docx`.

## Automated privacy controls

`scripts/submission_metadata.py` removes DOCX core creator, description,
last-modifier and date fields; removes extended application/version/company/manager
fields; enables Word's personal-information and date-removal flags; and normalizes ZIP
entry timestamps. The audit rejects comments, custom properties, people records,
authoring-tool traces, local absolute paths and remaining private metadata.

The PDF audit rejects non-empty author, creator, producer, creation-date and
modification-date metadata, plus local paths and known document-generation tool tokens.
The strict SoftwareX verifier fails if any upload file violates these controls.

## Visible information intentionally retained

SoftwareX uses author-visible submission materials rather than an anonymized manuscript.
The following publication information remains visible because it is required and was
confirmed by the corresponding author:

- Yuan Gao;
- Zhejiang Conservatory of Music;
- `selanceg@gmail.com`;
- ORCID `0009-0005-0394-3623`;
- public GitHub and Zenodo release links;
- funding, competing-interest, CRediT and data/code availability statements.

The generative-AI disclosure is also intentionally retained. Removing it would create a
submission-policy problem rather than improve privacy.

## Result

All seven upload files pass the automated submission privacy gate. No API key, local
Windows username, local absolute project path, hidden comment, custom property or
Python document-generation signature is present in the audited submission files.
