from config import FORM_DATA_FILE, OUTPUT_DIR, SAMPLE_PASSPORT_FILE
from json_builder import build_form_data
from form4_engine import fill_form
from validator import validate
from pdf_helper import convert_to_pdf


def main():

    form_data = build_form_data()

    missing = validate(form_data)

    if missing:

        print("===================================")
        print("Missing required fields:")
        for field in missing:
            print(f"- {field}")
        print("===================================")
        return

    docx_file = OUTPUT_DIR / "Test.docx"
    pdf_file = OUTPUT_DIR / "Test.pdf"

    fill_form(
        form_data,
        docx_file
    )

    convert_to_pdf(docx_file, pdf_file)

    print("PDF generated successfully.")


if __name__ == "__main__":
    main()

# from config import OUTPUT_DIR
# from src.document_reader import read_passport
# from form4_engine import fill_form


# def main():

#     form_data = read_passport()

#     fill_form(
#         form_data,
#         OUTPUT_DIR / "Test.docx"
#     )


# if __name__ == "__main__":
#     main()