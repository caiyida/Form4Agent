from io import BytesIO
from pathlib import Path
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


def locate_template_marks(reference_pdf):
    """Locate mark rectangles in a LibreOffice-rendered source-of-truth template."""

    with fitz.open(stream=reference_pdf, filetype="pdf") as document:
        if document.page_count < 7:
            raise DocumentConversionError(
                "The server rendered an incomplete Form 4 reference."
            )

        placements = []
        page_rectangles = []
        for page in document:
            page_rectangles.append(
                [
                    fitz.Rect(info["bbox"])
                    for info in page.get_image_info()
                    if fitz.Rect(info["bbox"]).height > 0
                ]
            )

        # Initials are the small image at the top-right of every template page.
        # Select by page and location so unrelated images with a similar aspect
        # ratio cannot create false extra matches.
        selected_initials = []
        for page_number in range(7):
            page = document[page_number]
            candidates = []
            for rectangle in page_rectangles[page_number]:
                ratio = rectangle.width / rectangle.height
                center_x = (rectangle.x0 + rectangle.x1) / (2 * page.rect.width)
                center_y = (rectangle.y0 + rectangle.y1) / (2 * page.rect.height)
                if 1.6 <= ratio <= 2.5 and center_x >= 0.65 and center_y <= 0.2:
                    score = abs(ratio - 2.07) + abs(center_x - 0.866) + abs(
                        center_y - 0.069
                    )
                    candidates.append((score, rectangle))
            if not candidates:
                raise DocumentConversionError(
                    "The server could not locate all seven template initials."
                )
            rectangle = min(candidates, key=lambda item: item[0])[1]
            selected_initials.append((page_number, rectangle))
            placements.append(("initials", page_number, rectangle))

        # The salesperson signature is on template page five. Its placed shape
        # is wider than an initial; exclude the already-selected top-right mark.
        signature_page_number = 4
        signature_page = document[signature_page_number]
        initial_rectangle = selected_initials[signature_page_number][1]
        signature_candidates = []
        for rectangle in page_rectangles[signature_page_number]:
            if rectangle == initial_rectangle:
                continue
            ratio = rectangle.width / rectangle.height
            relative_width = rectangle.width / signature_page.rect.width
            relative_height = rectangle.height / signature_page.rect.height
            if 2.3 <= ratio <= 3.2 and 0.08 <= relative_width <= 0.3 and 0.02 <= relative_height <= 0.12:
                score = abs(ratio - 2.61) + abs(relative_width - 0.148)
                signature_candidates.append((score, rectangle))
        if not signature_candidates:
            raise DocumentConversionError(
                "The server could not locate the template signature position."
            )
        signature_rectangle = min(signature_candidates, key=lambda item: item[0])[1]
        placements.append(("signature", signature_page_number, signature_rectangle))
        return placements


def stamp_agent_marks(content, placements=None):
    """Apply verified template signature/initial positions to a customer PDF."""

    if placements is None:
        reference = docx_to_pdf_bytes(TEMPLATE_PATH.read_bytes())
        placements = locate_template_marks(reference)
    images = _template_mark_images()

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("The signed Form 4 could not be opened.") from exc
    try:
        for description, page_number, reference_rectangle in placements:
            if page_number >= document.page_count:
                raise ValueError(
                    "The uploaded Form 4 is missing a page required for signature placement."
                )
            page = document[page_number]
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
