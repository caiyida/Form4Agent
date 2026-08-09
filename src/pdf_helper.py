import fitz
from pathlib import Path


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