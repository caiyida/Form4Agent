from docx.table import Table
from docx.text.paragraph import Paragraph


def iter_paragraphs(parent):

    if hasattr(parent, "paragraphs"):

        for paragraph in parent.paragraphs:
            yield paragraph

    if hasattr(parent, "tables"):

        for table in parent.tables:

            for row in table.rows:

                for cell in row.cells:

                    yield from iter_paragraphs(cell)


def replace_placeholder(document, key, value):

    placeholder = "{{" + key + "}}"

    found = False

    def replace_in_paragraph(paragraph):
        nonlocal found

        if placeholder not in paragraph.text:
            return

        # 合并整个 paragraph 的文字
        full_text = "".join(run.text for run in paragraph.runs)

        full_text = full_text.replace(
            placeholder,
            str(value)
        )

        # 清空所有 run
        for run in paragraph.runs:
            run.text = ""

        # 只写回第一个 run
        if paragraph.runs:
            paragraph.runs[0].text = full_text

        found = True

    # body
    for paragraph in iter_paragraphs(document):
        replace_in_paragraph(paragraph)

    # header / footer
    for section in document.sections:

        for paragraph in iter_paragraphs(section.header):
            replace_in_paragraph(paragraph)

        for paragraph in iter_paragraphs(section.footer):
            replace_in_paragraph(paragraph)

    if found:
        print(f"[OK] {key}")
    else:
        print(f"[Not Found] {key}")