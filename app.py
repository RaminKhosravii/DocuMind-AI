import streamlit as st

from pathlib import Path
import base64

from security import sanitize_filename, validate_upload

from file_processor import extract_text, get_file_type
from ai_engine import (
    CHAT_MODEL,
    retrieve_from_documents,
    stream_answer,
)
from database import (
    initialize_database,
    create_user,
    authenticate_user,
    add_document,
    get_documents,
    get_document,
    get_document_contents,
    count_readable_documents,
    delete_document,
    search_documents,
)

BASE_DIR = Path(__file__).resolve().parent
APP_ICON = BASE_DIR / "assets" / "documind.png"

st.set_page_config(
    page_title="DocuMind AI",
    page_icon=str(APP_ICON) if APP_ICON.is_file() else "🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

