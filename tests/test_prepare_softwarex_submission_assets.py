from pathlib import Path

from docx import Document

from scripts.prepare_softwarex_submission_assets import markdown_blocks, render_markdown_to_docx


def test_markdown_blocks_preserve_headings_paragraphs_and_bullets():
    blocks = markdown_blocks("# Title\n\nA wrapped\nparagraph.\n\n- One\n")
    assert blocks == [
        ("heading1", "Title"),
        ("paragraph", "A wrapped paragraph."),
        ("bullet", "One"),
    ]


def test_render_markdown_to_docx_creates_editable_document(tmp_path: Path):
    source = tmp_path / "statement.md"
    target = tmp_path / "statement.docx"
    source.write_text("# Statement\n\nEditable submission text.\n", encoding="utf-8")

    render_markdown_to_docx(source, target)

    document = Document(target)
    assert target.is_file()
    assert [paragraph.text for paragraph in document.paragraphs if paragraph.text] == [
        "Statement",
        "Editable submission text.",
    ]
