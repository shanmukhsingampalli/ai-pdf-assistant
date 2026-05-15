from pathlib import Path
import time
import os

import streamlit as st
from dotenv import load_dotenv

from data_loader import load_and_chunk_pdf
from vector_db import index_chunks, query_vector_db
from sentence_transformers import SentenceTransformer
from vector_db import query_vector_db

load_dotenv()

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI PDF RAG",
    page_icon="🚀",
    layout="wide",
)

# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* =========================================================
BACKGROUND
========================================================= */

.stApp {
    background:
        radial-gradient(circle at top, rgba(0,102,255,0.35) 0%, transparent 40%),
        radial-gradient(circle at center, rgba(0,50,120,0.25) 0%, transparent 45%),
        linear-gradient(180deg, #020617 0%, #030712 100%);
    color: #e5e7eb;
}

/* Hide Streamlit UI */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* =========================================================
MAIN CONTAINER
========================================================= */

.main-container {
    max-width: 1200px;
    margin: auto;
    padding-top: 60px;
}

/* =========================================================
BADGE
========================================================= */

.hero-badge {
    width: fit-content;
    margin: auto;
    margin-bottom: 25px;
    padding: 10px 22px;
    border-radius: 999px;
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.25);
    color: #60a5fa;
    font-weight: 600;
    font-size: 15px;
    backdrop-filter: blur(10px);
}

/* =========================================================
TITLE
========================================================= */

.hero-title {
    text-align: center;
    font-size: 82px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -3px;
    margin-bottom: 22px;
    color: #f8fafc;
}

.hero-title span {
    background: linear-gradient(90deg, #3b82f6, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* =========================================================
SUBTITLE
========================================================= */

.hero-subtitle {
    text-align: center;
    font-size: 24px;
    color: #94a3b8;
    max-width: 850px;
    margin: auto;
    line-height: 1.7;
    margin-bottom: 45px;
}

/* =========================================================
SEARCH BOX
========================================================= */

.hero-search-box {
    max-width: 1100px;
    margin: auto;
    margin-bottom: 60px;
    padding: 30px;
    border-radius: 30px;
    background: rgba(10,15,30,0.75);
    border: 1px solid rgba(255,255,255,0.06);
    backdrop-filter: blur(14px);

    box-shadow:
        0 0 50px rgba(0,119,255,0.12),
        inset 0 0 40px rgba(255,255,255,0.02);
}

.search-placeholder {
    color: #64748b;
    font-size: 22px;
    padding-left: 10px;
}

/* =========================================================
GLASS CARD
========================================================= */

.glass-card {
    background: rgba(9,14,30,0.72);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 32px;
    padding: 40px;
    margin-bottom: 40px;
    backdrop-filter: blur(18px);

    box-shadow:
        0 0 40px rgba(0,119,255,0.10),
        inset 0 0 30px rgba(255,255,255,0.015);
}

/* =========================================================
SECTION TITLE
========================================================= */

.section-title {
    font-size: 42px;
    font-weight: 750;
    color: #f8fafc;
    margin-bottom: 35px;
}

/* =========================================================
INPUTS
========================================================= */

.stTextInput input,
.stNumberInput input {

    background: rgba(15,23,42,0.85) !important;
    color: #f8fafc !important;

    border: 1px solid rgba(255,255,255,0.08) !important;

    border-radius: 18px !important;

    padding: 18px !important;

    font-size: 17px !important;
}

/* =========================================================
FILE UPLOADER
========================================================= */

[data-testid="stFileUploader"] {

    background: rgba(8,15,35,0.85);

    border: 1px solid rgba(59,130,246,0.22);

    border-radius: 26px;

    padding: 28px;

    backdrop-filter: blur(14px);

    box-shadow:
        0 0 30px rgba(37,99,235,0.10),
        inset 0 0 20px rgba(255,255,255,0.015);
}

[data-testid="stFileUploader"] section {

    background: rgba(15,23,42,0.92) !important;

    border: 1px dashed rgba(96,165,250,0.28) !important;

    border-radius: 20px !important;

    padding: 22px !important;

    transition: 0.3s ease;
}

[data-testid="stFileUploader"] section:hover {

    border: 1px dashed rgba(96,165,250,0.55) !important;

    background: rgba(20,30,55,0.95) !important;
}

[data-testid="stFileUploader"] button {

    background: linear-gradient(90deg, #2563eb, #3b82f6) !important;

    color: white !important;

    border: none !important;

    border-radius: 14px !important;

    padding: 10px 22px !important;

    font-weight: 600 !important;

    font-size: 15px !important;

    transition: 0.3s ease !important;

    box-shadow: 0 0 18px rgba(59,130,246,0.28);
}

[data-testid="stFileUploader"] button:hover {

    transform: translateY(-1px);

    box-shadow:
        0 0 24px rgba(59,130,246,0.5),
        0 0 50px rgba(59,130,246,0.18);
}

[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] label {

    color: #cbd5e1 !important;
}

[data-testid="stFileUploaderFile"] {

    background: rgba(30,41,59,0.85) !important;

    border-radius: 14px !important;

    border: 1px solid rgba(255,255,255,0.06) !important;
}

/* =========================================================
BUTTONS
========================================================= */

.stButton > button,
.stFormSubmitButton > button {

    background: linear-gradient(90deg, #2563eb, #3b82f6);

    color: white;

    border: none;

    border-radius: 18px;

    padding: 14px 34px;

    font-size: 17px;

    font-weight: 650;

    transition: all 0.3s ease;

    box-shadow: 0 0 20px rgba(59,130,246,0.25);
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {

    transform: translateY(-2px);

    box-shadow:
        0 0 30px rgba(59,130,246,0.45),
        0 0 60px rgba(59,130,246,0.18);
}

/* =========================================================
ANSWER BOX
========================================================= */

.answer-box {

    background: rgba(15,23,42,0.7);

    border: 1px solid rgba(255,255,255,0.06);

    border-radius: 24px;

    padding: 30px;

    margin-top: 30px;

    color: #e2e8f0;
}

/* =========================================================
SCROLLBAR
========================================================= */

::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-thumb {
    background: #1e40af;
    border-radius: 20px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# SAVE PDF
# =========================================================

def save_uploaded_pdf(file) -> Path:

    uploads_dir = Path("uploads")

    uploads_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = uploads_dir / file.name

    file_bytes = file.getbuffer()

    file_path.write_bytes(file_bytes)

    return file_path

# =========================================================
# HERO SECTION
# =========================================================

st.markdown("""
<div class="main-container">

<div class="hero-badge">
    ⚡ AI Powered RAG Agent
</div>

<div class="hero-title">
Ask. Retrieve. <span>Generate.</span>
</div>

<div class="hero-subtitle">
Next generation Retrieval-Augmented Generation system for intelligent PDF understanding.
</div>

<div class="hero-search-box">
    <div class="search-placeholder">
        🚀 Upload PDFs and start chatting with your documents...
    </div>
</div>

</div>
""", unsafe_allow_html=True)

# =========================================================
# PDF INGEST UI
# =========================================================

st.markdown('<div class="glass-card">', unsafe_allow_html=True)

st.markdown(
    '<div class="section-title">📄 Upload PDF to Ingest</div>',
    unsafe_allow_html=True
)

uploaded = st.file_uploader(
    "Choose a PDF",
    type=["pdf"],
    accept_multiple_files=False,
)

if uploaded is not None:

    try:

        with st.spinner("Processing PDF..."):

            path = save_uploaded_pdf(uploaded)

            chunks = load_and_chunk_pdf(str(path))

            embedding_model = SentenceTransformer(
                "BAAI/bge-small-en-v1.5"
            )

            index_chunks(
                chunks,
                embedding_model
            )

            time.sleep(1)

            st.success(
                f"PDF successfully ingested: {path.name}"
            )

            st.caption(
                "Your document is now ready for AI querying."
            )

    except Exception as e:

        st.error(f"Upload failed: {str(e)}")

st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# QUERY UI
# =========================================================

st.markdown('<div class="glass-card">', unsafe_allow_html=True)

st.markdown(
    '<div class="section-title">🤖 Ask Questions About Your PDFs</div>',
    unsafe_allow_html=True
)

with st.form("rag_query_form"):

    question = st.text_input(
        "Your question"
    )

    top_k = st.number_input(
        "How many chunks to retrieve",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
    )

    submitted = st.form_submit_button(
        "Ask AI"
    )

    if submitted and question.strip():

        try:

            with st.spinner(
                "Generating AI response..."
            ):

                result = query_vector_db(
                    question.strip(),
                    int(top_k)
                )

                answer = result.get(
                    "answer",
                    ""
                )

                sources = result.get(
                    "sources",
                    []
                )

            st.markdown(
                '<div class="answer-box">',
                unsafe_allow_html=True
            )

            st.subheader("✨ AI Answer")

            st.write(
                answer if answer else "No answer generated."
            )

            if sources:

                st.markdown("### 📚 Sources")

                for s in sources:
                    st.write(f"- {s}")

            st.markdown(
                '</div>',
                unsafe_allow_html=True
            )

        except Exception as e:

            st.error(f"Question request failed: {str(e)}")

st.markdown('</div>', unsafe_allow_html=True)