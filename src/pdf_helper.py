from io import BytesIO
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import pymupdf as fitz
from PIL import Image, ImageOps


class DocumentConversionError(RuntimeError):
    pass


A4 = (595, 842)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "Form4_Template.docx"


def pdf_to_image_bytes(content: bytes, max_pages=10):
    """Render a PDF in memory and return PNG page images."""

    if not content:
        raise ValueError("The PDF is empty.")

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("The PDF could not be opened.") from exc

    try:
        if document.page_count > max_pages:
            raise ValueError(f"PDFs are limited to {max_pages} pages.")
        return [page.get_pixmap(dpi=200).tobytes("png") for page in document]
    finally:
        document.close()


def pdf_first_page_image_bytes(content: bytes):
    """Render only the first PDF page for fast upload classification."""

    if not content:
        raise ValueError("The PDF is empty.")
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("The PDF could not be opened.") from exc
    try:
        if document.page_count < 1:
            raise ValueError("The PDF has no readable pages.")
        return document[0].get_pixmap(dpi=150).tobytes("png")
    finally:
        document.close()


def pdf_to_images(pdf_path, output_dir="temp"):

    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(exist_ok=True)

    doc = fitz.open(pdf_path)

    images = []

    for i, page in enumerate(doc):

        pix = page.get_pixmap(dpi=300)

        image_path = output_dir / f"{pdf_path.stem}_{i + 1}.png"

        pix.save(image_path)

        images.append(image_path)

    return images


def docx_to_pdf_bytes(content):
    """Convert DOCX bytes with LibreOffice without retaining customer files."""

    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if not executable:
        raise DocumentConversionError(
            "PDF conversion is unavailable on this server. Download the Word "
            "version instead."
        )
    if not content:
        raise DocumentConversionError("The Word document is empty.")

    with TemporaryDirectory(prefix="form4agent-") as temp_dir:
        directory = Path(temp_dir)
        source = directory / "review.docx"
        source.write_bytes(content)
        try:
            result = subprocess.run(
                [
                    executable,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(directory),
                    str(source),
                ],
                capture_output=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DocumentConversionError("PDF conversion failed safely.") from exc

        output = directory / "review.pdf"
        if result.returncode or not output.exists():
            raise DocumentConversionError("PDF conversion failed safely.")
        return output.read_bytes()


def images_to_pdf_bytes(images, max_pages=10):
    """Turn ordered image uploads into an A4 PDF, preserving each whole page."""

    if not images:
        raise ValueError("Upload at least one page image.")
    if len(images) > max_pages:
        raise ValueError(f"Image sets are limited to {max_pages} pages.")

    output = fitz.open()
    try:
        for content in images:
            try:
                with Image.open(BytesIO(content)) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    rendered = BytesIO()
                    image.save(rendered, "JPEG", quality=92)
                    width, height = image.size
            except Exception as exc:
                raise ValueError("One of the page images could not be opened.") from exc

            page = output.new_page(width=A4[0], height=A4[1])
            scale = min(A4[0] / width, A4[1] / height)
            rendered_width, rendered_height = width * scale, height * scale
            x = (A4[0] - rendered_width) / 2
            y = (A4[1] - rendered_height) / 2
            page.insert_image(
                fitz.Rect(x, y, x + rendered_width, y + rendered_height),
                stream=rendered.getvalue(),
            )
        return output.tobytes(garbage=4, deflate=True)
    finally:
        output.close()


def signed_upload_to_pdf(files, expected_pages=None):
    """Normalize a complete signed PDF or ordered page images and inspect it."""

    if not files:
        raise ValueError("Upload the complete customer-signed document.")
    suffixes = [Path(name).suffix.lower() for name, _ in files]
    if suffixes == [".pdf"]:
        content = files[0][1]
    elif all(suffix in {".jpg", ".jpeg", ".png"} for suffix in suffixes):
        content = images_to_pdf_bytes([item[1] for item in files])
    else:
        raise ValueError("Upload one PDF or an ordered set of page images.")

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("The signed document could not be opened.") from exc
    try:
        if expected_pages is not None and document.page_count != expected_pages:
            raise ValueError(
                f"The complete Form 4 must have {expected_pages} pages; this file "
                f"has {document.page_count}."
            )
    finally:
        document.close()
    return content


def _template_mark_images():
    """Read the signature assets by drawing description, not media filename."""

    from lxml import etree

    namespaces = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    }
    with ZipFile(TEMPLATE_PATH) as archive:
        document = etree.fromstring(archive.read("word/document.xml"))
        relationships = etree.fromstring(
            archive.read("word/_rels/document.xml.rels")
        )
        targets = {item.get("Id"): item.get("Target") for item in relationships}
        images = {}
        for description in ("initials", "signature"):
            relationship_ids = document.xpath(
                f'//wp:anchor[wp:docPr[@descr="{description}"]]//a:blip/@r:embed',
                namespaces=namespaces,
            )
            if not relationship_ids:
                raise DocumentConversionError(f"Template {description} image is missing.")
            images[description] = archive.read(
                str(Path("word") / targets[relationship_ids[0]])
            )
    return images


def _template_initial_placements():
    """Convert the seven protected Word anchors directly to A4 PDF points."""

    from lxml import etree

    namespaces = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    }
    with ZipFile(TEMPLATE_PATH) as archive:
        document = etree.fromstring(archive.read("word/document.xml"))

    left_margins = document.xpath("//w:sectPr/w:pgMar/@w:left", namespaces=namespaces)
    if not left_margins:
        raise DocumentConversionError("The template page margin is missing.")
    left_margin_points = int(left_margins[0]) / 20

    anchors = document.xpath(
        '//wp:anchor[wp:docPr[@descr="initials"]]', namespaces=namespaces
    )
    if len(anchors) != 7:
        raise DocumentConversionError("The template must contain seven initial anchors.")

    placements = []
    for page_number, anchor in enumerate(anchors):
        horizontal = anchor.find("wp:positionH", namespaces)
        vertical = anchor.find("wp:positionV", namespaces)
        extent = anchor.find("wp:extent", namespaces)
        if (
            horizontal is None
            or vertical is None
            or extent is None
            or horizontal.get("relativeFrom") != "column"
            or vertical.get("relativeFrom") != "page"
        ):
            raise DocumentConversionError("An initial anchor has an unsafe position.")
        x = left_margin_points + int(horizontal.findtext("wp:posOffset", namespaces=namespaces)) / 12700
        y = int(vertical.findtext("wp:posOffset", namespaces=namespaces)) / 12700
        width = int(extent.get("cx")) / 12700
        height = int(extent.get("cy")) / 12700
        placements.append(
            ("initials", page_number, fitz.Rect(x, y, x + width, y + height))
        )
    return placements


SIGNATURE_LABEL_WORDS = (
    "salesperson",
    "for",
    "and",
    "on",
    "behalf",
    "of",
    "the",
    "estate",
    "agent",
)


def _normalize_pdf_word(value):
    return re.sub(r"[^a-z]", "", value.lower())


def _find_signature_label(words):
    normalized = [(_normalize_pdf_word(word[4]), fitz.Rect(word[:4])) for word in words]
    normalized = [(text, rectangle) for text, rectangle in normalized if text]
    target = list(SIGNATURE_LABEL_WORDS)
    for start in range(len(normalized) - len(target) + 1):
        if [item[0] for item in normalized[start : start + len(target)]] == target:
            rectangle = normalized[start][1]
            for _, word_rectangle in normalized[start + 1 : start + len(target)]:
                rectangle |= word_rectangle
            return rectangle
    return None


def _signature_rectangle(document):
    """Locate the salesperson line from PDF text, with OCR for scanned pages."""

    for page in document:
        label = _find_signature_label(page.get_text("words"))
        if label is None:
            try:
                text_page = page.get_textpage_ocr(language="eng", dpi=150, full=True)
                label = _find_signature_label(
                    page.get_text("words", textpage=text_page)
                )
            except RuntimeError:
                label = None
        if label is None:
            continue

        line_candidates = []
        for drawing in page.get_drawings():
            rectangle = fitz.Rect(drawing["rect"])
            gap = label.y0 - rectangle.y1
            if (
                rectangle.width >= 100
                and rectangle.height <= 4
                and -2 <= gap <= 80
                and rectangle.x1 >= label.x0
                and rectangle.x0 <= label.x1
            ):
                line_candidates.append((abs(gap), rectangle))

        if line_candidates:
            line = min(line_candidates, key=lambda item: item[0])[1]
        else:
            # Some Word-to-PDF renderers encode the line as underscore text.
            # Derive it from the located label rather than a page-fixed position.
            line = fitz.Rect(label.x0, label.y0 - 38, label.x0 + 265, label.y0 - 2)

        signature_width = 1119505 / 12700
        signature_height = 428625 / 12700
        center_x = (line.x0 + line.x1) / 2
        bottom = line.y0 + 2
        return page.number, fitz.Rect(
            center_x - signature_width / 2,
            bottom - signature_height,
            center_x + signature_width / 2,
            bottom,
        )

    raise ValueError(
        "The salesperson signature line could not be found in this Form 4."
    )


def stamp_agent_marks(content, placements=None):
    """Apply verified template signature/initial positions to a customer PDF."""

    images = _template_mark_images()
    dynamic_placements = placements is None

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("The signed Form 4 could not be opened.") from exc
    try:
        if placements is None:
            template_initials = _template_initial_placements()
            placements = []
            for page_number in range(document.page_count):
                source = template_initials[min(page_number, len(template_initials) - 1)]
                placements.append(("initials", page_number, source[2]))
            signature_page, signature_rectangle = _signature_rectangle(document)
            placements.append(("signature", signature_page, signature_rectangle))

        for description, page_number, reference_rectangle in placements:
            if page_number >= document.page_count:
                raise ValueError(
                    "The uploaded Form 4 is missing a page required for signature placement."
                )
            page = document[page_number]
            if dynamic_placements and description == "signature":
                rectangle = reference_rectangle
            else:
                scale_x = page.rect.width / A4[0]
                scale_y = page.rect.height / A4[1]
                rectangle = fitz.Rect(
                    reference_rectangle.x0 * scale_x,
                    reference_rectangle.y0 * scale_y,
                    reference_rectangle.x1 * scale_x,
                    reference_rectangle.y1 * scale_y,
                )
            page.insert_image(rectangle, stream=images[description], overlay=True)
        return document.tobytes(garbage=4, deflate=True)
    finally:
        document.close()
