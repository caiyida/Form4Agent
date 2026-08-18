from io import BytesIO
from pathlib import Path
import sys

import streamlit as st


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from form_rules import default_commission  # noqa: E402
from json_builder import empty_form_data, form_data_from_identities  # noqa: E402
from validator import normalized_form_data, validate  # noqa: E402


MAX_FILES = 8
MAX_FILE_MB = 50
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
EDITABLE_DETAIL_FIELDS = (
    "agreement_date",
    "lease_term",
    "commission_term",
    "renew_commission",
    "additional_term",
)


def initialize_state():
    defaults = {
        "details": empty_form_data(),
        "review_docx": None,
        "review_pdf": None,
        "final_pdf": None,
        "result_summary": None,
        "uploader_version": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def clear_private_data():
    for key in ("review_docx", "review_pdf", "final_pdf", "result_summary"):
        st.session_state[key] = None
    st.session_state.details = empty_form_data()
    st.session_state.manual_property_address = ""
    st.session_state.uploader_version += 1


def generate_review(form_data):
    from form4_engine import fill_form
    from pdf_helper import DocumentConversionError, docx_to_pdf_bytes

    output = BytesIO()
    fill_form(form_data, output, include_agent_marks=False)
    docx = output.getvalue()
    try:
        pdf = docx_to_pdf_bytes(docx)
    except DocumentConversionError:
        pdf = None
    return docx, pdf


@st.cache_data(max_entries=1, show_spinner=False)
def verified_mark_placements():
    from pdf_helper import TEMPLATE_PATH, docx_to_pdf_bytes, locate_template_marks

    reference_pdf = docx_to_pdf_bytes(TEMPLATE_PATH.read_bytes())
    return locate_template_marks(reference_pdf)


st.set_page_config(
    page_title="Form4Agent",
    page_icon=":material/description:",
    layout="centered",
)
initialize_state()

st.title("Form4Agent")
st.caption("Upload files. The app will prepare a customer form or complete a signed Form 4.")

uploaded_files = st.file_uploader(
    "Documents",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True,
    key=f"smart_upload_{st.session_state.uploader_version}",
    help="Upload tenant IDs and an address screenshot, or one customer-signed Form 4.",
    max_upload_size=MAX_FILE_MB,
)

if uploaded_files:
    total_size = sum(file.size for file in uploaded_files) / (1024 * 1024)
    st.caption(
        f":material/check_circle: {len(uploaded_files)} file(s) ready · "
        f"{total_size:.1f} MB"
    )

manual_address = st.text_input(
    "Property address",
    placeholder="Leave blank if the address is visible in an uploaded file",
    key="manual_property_address",
)

with st.container(horizontal=True, vertical_alignment="bottom"):
    generate_clicked = st.button(
        "Generate Form 4",
        type="primary",
        icon=":material/description:",
        disabled=not uploaded_files,
    )
    with st.popover("Edit details", icon=":material/edit:"):
        st.caption("These defaults are used when preparing the customer version.")
        with st.form("edit_details", border=False):
            details = st.session_state.details
            agreement_date = st.text_input("Agreement date", details["agreement_date"])
            lease_term = st.number_input(
                "Lease term (months)",
                min_value=1,
                step=1,
                value=int(details["lease_term"] or 12),
            )
            automatic_commission = default_commission(lease_term)
            commission_term = st.text_input(
                "Commission (months of rent)",
                details["commission_term"] or automatic_commission,
                help=f"Automatic value for this lease: {automatic_commission}",
            )
            renew_commission = st.text_input(
                "Renewal commission", details["renew_commission"] or "0.5"
            )
            additional_term = st.text_area(
                "Additional terms", details["additional_term"]
            )
            save_details = st.form_submit_button("Save details", type="primary")
        if save_details:
            previous_auto = default_commission(details["lease_term"] or 12)
            saved_commission = commission_term.strip()
            if details["commission_term"] == previous_auto and saved_commission == previous_auto:
                saved_commission = default_commission(lease_term)
            st.session_state.details.update(
                agreement_date=agreement_date.strip(),
                lease_term=str(lease_term),
                commission_term=saved_commission,
                renew_commission=renew_commission.strip(),
                additional_term=additional_term.strip(),
            )
            st.toast("Details saved", icon=":material/check_circle:")

if st.session_state.result_summary:
    st.caption(st.session_state.result_summary)

if generate_clicked:
    st.session_state.review_docx = None
    st.session_state.review_pdf = None
    st.session_state.final_pdf = None

    if len(uploaded_files) > MAX_FILES:
        st.error(f"Upload no more than {MAX_FILES} files.")
    elif any(file.size > MAX_FILE_BYTES for file in uploaded_files):
        st.error(f"Each file must be {MAX_FILE_MB} MB or smaller.")
    else:
        try:
            from document_reader import DocumentExtractionError
            from json_builder import analyze_uploaded_documents
            from pdf_helper import (
                DocumentConversionError,
                signed_upload_to_pdf,
                stamp_agent_marks,
            )

            uploads = [(file.name, file.getvalue()) for file in uploaded_files]
            with st.status("Reading uploaded files…", expanded=False) as status:
                analysis = analyze_uploaded_documents(uploads)
                if analysis["is_form4"]:
                    signed_pdf = signed_upload_to_pdf(uploads)
                    st.session_state.final_pdf = stamp_agent_marks(
                        signed_pdf,
                        placements=verified_mark_placements(),
                    )
                    st.session_state.result_summary = "Signature added"
                    status.update(label="Signature added", state="complete")
                else:
                    address = manual_address.strip() or analysis["property_address"]
                    if not address:
                        status.update(label="Property address needed", state="error")
                        st.warning(
                            "Property address was not found. Enter it below the upload box, "
                            "then select Generate Form 4 again."
                        )
                    else:
                        form_data = form_data_from_identities(analysis["identities"])
                        form_data.update(
                            {
                                key: st.session_state.details[key]
                                for key in EDITABLE_DETAIL_FIELDS
                            }
                        )
                        form_data["property_address"] = address
                        form_data = normalized_form_data(form_data)
                        missing = validate(form_data)
                        if missing:
                            raise ValueError(
                                "No usable tenant name and identity number were found. "
                                "Upload a clearer passport, NRIC, or FIN."
                            )
                        review_docx, review_pdf = generate_review(form_data)
                        st.session_state.review_docx = review_docx
                        st.session_state.review_pdf = review_pdf
                        st.session_state.result_summary = (
                            f"Prepared Form 4 for {len(analysis['identities'])} tenant(s)."
                        )
                        status.update(label="Customer Form 4 ready", state="complete")
        except (DocumentExtractionError, DocumentConversionError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("The files could not be processed safely. Check them and try again.")

if st.session_state.review_docx:
    with st.container(border=True):
        st.subheader("Ready for customer signature")
        st.caption("Your signature and all seven initials have been removed.")
        if st.session_state.review_pdf:
            st.download_button(
                "Download customer PDF",
                st.session_state.review_pdf,
                "Form4-for-customer.pdf",
                "application/pdf",
                type="primary",
                icon=":material/download:",
            )
        else:
            st.warning("PDF conversion is unavailable here. Use the Word version.")
        st.download_button(
            "Download Word version",
            st.session_state.review_docx,
            "Form4-for-customer.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            icon=":material/download:",
        )
        st.caption("On mobile, download the PDF and share it through WeChat or WhatsApp.")

if st.session_state.final_pdf:
    with st.container(border=True):
        st.success("Signature added", icon=":material/check_circle:")
        st.download_button(
            "Download final signed PDF",
            st.session_state.final_pdf,
            "Form4-final-signed.pdf",
            "application/pdf",
            type="primary",
            icon=":material/download:",
        )

if any(
    st.session_state[key]
    for key in ("review_docx", "final_pdf", "result_summary")
):
    st.button(
        "Clear private session data",
        on_click=clear_private_data,
        icon=":material/delete:",
    )
