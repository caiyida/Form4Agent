from docx import Document
from config import FORM4_TEMPLATE


def load_form4():
    return Document(FORM4_TEMPLATE)
