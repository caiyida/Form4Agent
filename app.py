import streamlit as st
from pathlib import Path
import shutil
import sys

# 可以 import src
sys.path.append("src")

from json_builder import build_form_data
from form4_engine import fill_form
from validator import validate
from config import OUTPUT_DIR

st.set_page_config(
    page_title="Form4 AI",
    page_icon="📄",
)

st.title("📄 Form4 AI")

uploaded_files = st.file_uploader(
    "Upload Documents",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True
)

if uploaded_files:

    input_dir = Path("input")
    input_dir.mkdir(exist_ok=True)

    # 清空旧文件
    for file in input_dir.iterdir():
        if file.is_file():
            file.unlink()

    # 保存所有上传文件
    for uploaded_file in uploaded_files:

        save_path = input_dir / uploaded_file.name

        with open(save_path, "wb") as f:
            shutil.copyfileobj(uploaded_file, f)

    st.success(f"{len(uploaded_files)} file(s) uploaded.")

if st.button("Generate Form4"):

    with st.spinner("Generating..."):

        form_data = build_form_data()

        missing = validate(form_data)

        if missing:

            st.error("Missing required fields.")

            for field in missing:
                st.write(field)

        else:
            output_file = OUTPUT_DIR / "Test.docx"

            fill_form(
                form_data,
                output_file
            )

            st.success("Form generated successfully!")

            with open(output_file, "rb") as file:

                st.download_button(
                    label="📥 Download Form4",
                    data=file,
                    file_name="Form4.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )