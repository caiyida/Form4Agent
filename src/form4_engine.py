from form_loader import load_form4
from word_helper import replace_placeholder


def fill_form(
    form_data,
    output_file
):

    document = load_form4()

    for key, value in form_data.items():

        if value in ("", None):
            continue

        replace_placeholder(
            document,
            key,
            value
        )

    document.save(output_file)