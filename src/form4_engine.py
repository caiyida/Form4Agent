from form_loader import load_form4
from word_helper import find_placeholders, remove_agent_marks, replace_placeholder


def fill_form(
    form_data,
    output_file,
    include_agent_marks=True,
):

    document = load_form4()

    # Drive generation from the template so omitted optional values become blank
    # and can never survive as unresolved placeholders.
    for key in find_placeholders(document):
        replace_placeholder(
            document,
            key,
            form_data.get(key, "")
        )

    unresolved = find_placeholders(document)
    if unresolved:
        fields = ", ".join(sorted(unresolved))
        raise ValueError(f"Unresolved template placeholders: {fields}")

    if not include_agent_marks:
        removed = remove_agent_marks(document)
        if removed != 8:
            raise ValueError(
                "The review document could not safely remove all agent marks."
            )

    document.save(output_file)
