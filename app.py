import streamlit as st
import pandas as pd

# from core.pipeline import check_application --> to be added when linking to backend
from utils.ui import render_header, render_footer, render_cards, render_masthead, render_nosection, render_errormessage, render_uploadinfo

render_masthead()

st.set_page_config(page_title="Grant Application Quality Checker", layout="wide")


render_header("Grant Application Quality Checker")

render_uploadinfo()

render_nosection()
render_nosection()

st.title("Upload SmartyGrants export", text_alignment="center", anchor=False)

render_nosection()


with st.form("application_checker"):

    pdf = st.file_uploader(
        "Drag and drop your files here",
        type=None,
        accept_multiple_files=True
    )

    tabletext = st.text_area(
        "Enter Asset Damage Table information here:"
    )

    submitted = st.form_submit_button("Check application")

    
if submitted:
    if not pdf or not tabletext.strip():
        render_errormessage()
    else:
        st.switch_page("pages/1_Results.py")


render_cards()

render_nosection()

render_footer()