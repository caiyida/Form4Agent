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
        candidates = []
        for page_number, page in enumerate(document):
            for info in page.get_image_info():
                rectangle = fitz.Rect(info["bbox"])
                if rectangle.height <= 0:
                    continue
                ratio = rectangle.width / rectangle.height
                if 1.8 <= ratio <= 2.3:
                    candidates.append(("initials", page_number, rectangle))
                elif 2.35 <= ratio <= 3.0:
                    candidates.append(("signature", page_number, rectangle))

        initials = [item for item in candidates if item[0] == "initials"]
        signatures = [item for item in candidates if item[0] == "signature"]
        if len(initials) != 7 or len(signatures) != 1:
            raise DocumentConversionError(
                "The signature positions could not be verified against the template."
            )
        return candidates


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
