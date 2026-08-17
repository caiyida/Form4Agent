import re


PLACEHOLDER_PATTERN = re.compile(r"{{\s*([A-Za-z0-9_]+)\s*}}")
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
WORD_DRAWING = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing"


def iter_paragraphs(parent):

    if hasattr(parent, "paragraphs"):
        for paragraph in parent.paragraphs:
            yield paragraph

    if hasattr(parent, "tables"):
        for table in parent.tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from iter_paragraphs(cell)


def iter_document_paragraphs(document):
    """Yield paragraphs in the body, tables, headers, and footers."""

    yield from iter_paragraphs(document)

    for section in document.sections:
        yield from iter_paragraphs(section.header)
        yield from iter_paragraphs(section.footer)


def _text_nodes(paragraph):
    """Return text nodes without rewriting their containing run XML."""

    return paragraph._p.xpath(".//w:t")


def _set_text(node, value):
    node.text = value
    if value[:1].isspace() or value[-1:].isspace():
        node.set(XML_SPACE, "preserve")
    else:
        node.attrib.pop(XML_SPACE, None)


def _replace_in_nodes(nodes, placeholder, value):
    """Replace text spanning one or more nodes while preserving other XML."""

    original_texts = [node.text or "" for node in nodes]
    full_text = "".join(original_texts)
    matches = []
    start = 0

    while True:
        match_start = full_text.find(placeholder, start)
        if match_start == -1:
            break
        matches.append((match_start, match_start + len(placeholder)))
        start = match_start + len(placeholder)

    if not matches:
        return 0

    def current_boundaries():
        result = []
        position = 0
        for node in nodes:
            text = node.text or ""
            result.append((position, position + len(text)))
            position += len(text)
        return result

    boundaries = current_boundaries()

    # Work from right to left. Earlier character offsets remain valid even when a
    # later replacement changes the length of a text node.
    for match_start, match_end in reversed(matches):
        affected = [
            index
            for index, (node_start, node_end) in enumerate(boundaries)
            if node_start < match_end and node_end > match_start
        ]
        if not affected:
            continue

        first_index = affected[0]
        last_index = affected[-1]
        first_start, _ = boundaries[first_index]
        _, last_end = boundaries[last_index]
        first_text = nodes[first_index].text or ""
        last_text = nodes[last_index].text or ""
        prefix = first_text[: match_start - first_start]
        suffix_length = last_end - match_end
        suffix = last_text[-suffix_length:] if suffix_length else ""

        _set_text(nodes[first_index], prefix + value + suffix)
        for index in affected[1:]:
            _set_text(nodes[index], "")
        boundaries = current_boundaries()

    return len(matches)


def find_placeholders(document):
    """Return placeholder keys found anywhere supported by the generator."""

    placeholders = set()
    for paragraph in iter_document_paragraphs(document):
        text = "".join(node.text or "" for node in _text_nodes(paragraph))
        placeholders.update(PLACEHOLDER_PATTERN.findall(text))
    return placeholders


def replace_placeholder(document, key, value):

    placeholder = "{{" + key + "}}"

    if value is None:
        value = ""

    value = str(value)

    replacements = 0
    for paragraph in iter_document_paragraphs(document):
        replacements += _replace_in_nodes(_text_nodes(paragraph), placeholder, value)

    return replacements


def remove_agent_marks(document):
    """Remove only the salesperson signature/initial drawings from a copy."""

    drawings = document.element.xpath(
        './/w:drawing[.//wp:docPr[@descr="signature" or @descr="initials"]]'
    )
    for drawing in drawings:
        if drawing.tag != WORD_DRAWING:
            continue
        drawing.getparent().remove(drawing)
    return len(drawings)
