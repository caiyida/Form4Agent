from docx import Document
from config import FORM4_TEMPLATE


def load_form4():
    print("Loading template...")

    document = Document(FORM4_TEMPLATE)

    print("Template opened!")

    return document