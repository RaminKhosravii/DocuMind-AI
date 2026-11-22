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

regular_font = BASE_DIR / "assets" / "fonts" / "Vazirmatn-Regular.woff2"
bold_font = BASE_DIR / "assets" / "fonts" / "Vazirmatn-Bold.woff2"

regular_base64 = base64.b64encode(regular_font.read_bytes()).decode()
bold_base64 = base64.b64encode(bold_font.read_bytes()).decode()

st.markdown(f"""
<style>
@font-face {{
    font-family: 'Vazirmatn';
    src: url(data:font/woff2;base64,{regular_base64}) format('woff2');
    font-weight: 400;
}}

@font-face {{
    font-family: 'Vazirmatn';
    src: url(data:font/woff2;base64,{bold_base64}) format('woff2');
    font-weight: 700;
}}

html, body, [data-testid="stApp"] {{
    font-family: 'Vazirmatn', sans-serif !important;
    font-size: 16px;
    direction: rtl !important;
    text-align: right !important;
}}

[data-testid="stAppViewContainer"],
[data-testid="stSidebar"],
[data-testid="stMain"] {{
    direction: rtl !important;
}}

[data-testid="stMarkdownContainer"],
[data-testid="stWidgetLabel"],
[data-testid="stExpander"],
[data-testid="stFileUploader"],
[data-testid="stChatMessage"] {{
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Vazirmatn', sans-serif !important;
}}

.stTextInput input,
.stTextArea textarea,
.stButton button,
[data-testid="stChatInput"] textarea {{
    font-family: 'Vazirmatn', sans-serif !important;
    font-size: 16px !important;
    direction: rtl !important;
    text-align: right !important;
}}

h1, h2, h3 {{
    font-family: 'Vazirmatn', sans-serif !important;
}}

h1 {{ font-size: 30px !important; font-weight: 700 !important; }}
h2 {{ font-size: 25px !important; font-weight: 700 !important; }}
h3 {{ font-size: 21px !important; font-weight: 700 !important; }}

</style>
""", unsafe_allow_html=True)

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".rtf": "application/rtf",
    ".log": "text/plain",
}

SUGGESTIONS = [
    "خلاصه این متن چیست؟",
    "نکات اصلی را فهرست کن",
    "این سند درباره چیست؟",
]

initialize_database()

if "user" not in st.session_state:
    st.session_state.user = None


def logout():
    st.session_state.clear()


def format_size(size):
    size = size or 0

    if size < 1024:
        return f"{size} بایت"

    if size < 1024 * 1024:
        return f"{size / 1024:.1f} کیلوبایت"

    return f"{size / (1024 * 1024):.1f} مگابایت"


def document_label(document):
    kind = (document["file_type"] or "").lstrip(".") or "فایل"
    return (
        f"{document['filename']}  ·  {kind}  ·  "
        f"{format_size(document['file_size'])}"
    )


def render_sources(sources):
    if not sources:
        return

    with st.expander(f"منابع پاسخ ({len(sources)})"):
        for source in sources:
            st.markdown(f"**{source['label']}**")
            st.write(source["text"])


def show_auth_page():
    st.title("DocuMind AI")
    st.subheader("دستیار هوشمند اسناد")
    st.write("برای استفاده از برنامه وارد حساب خودت شو.")

    login_tab, register_tab = st.tabs(["ورود", "ثبت‌نام"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("نام کاربری", key="login_username")
            password = st.text_input(
                "رمز عبور",
                type="password",
                key="login_password",
            )
            submitted = st.form_submit_button(
                "ورود به حساب",
                type="primary",
                icon=":material/login:",
            )

            if submitted:
                user = authenticate_user(username, password)

                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("نام کاربری یا رمز عبور اشتباه است.")

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input(
                "نام کاربری جدید",
                key="register_username",
            )
            new_password = st.text_input(
                "رمز عبور جدید (حداقل ۱۲ کاراکتر)",
                type="password",
                key="register_password",
            )
            confirm_password = st.text_input(
                "تکرار رمز عبور",
                type="password",
                key="confirm_password",
            )
            submitted = st.form_submit_button(
                "ساخت حساب",
                type="primary",
                icon=":material/person_add:",
            )

            if submitted:
                if new_password != confirm_password:
                    st.error("رمز عبور و تکرار آن یکسان نیستند.")
                else:
                    success, message = create_user(new_username, new_password)

                    if success:
                        user = authenticate_user(new_username, new_password)

                        if user:
                            st.session_state.user = user
                            st.rerun()
                        else:
                            st.success(message)
                    else:
                        st.error(message)


def show_library(user_id):
    st.header("اسناد")
    st.caption(
        "استخراج متن: PDF، DOCX، XLSX، PPTX، TXT، MD، CSV، RTF و LOG. "
        "بقیه فایل‌ها ذخیره می‌شوند ولی متنشان خوانده نمی‌شود."
    )

    if "uploader_nonce" not in st.session_state:
        st.session_state.uploader_nonce = 0

    uploaded_files = st.file_uploader(
        "فایل‌های موردنظرت را انتخاب کن",
        type=None,
        accept_multiple_files=True,
        max_upload_size=25,
        key=f"uploader_{st.session_state.uploader_nonce}",
    )

    if st.button(
        "ذخیره اسناد",
        type="primary",
        icon=":material/save:",
    ):
        if not uploaded_files:
            st.warning("ابتدا حداقل یک فایل انتخاب کن.")
        else:
            saved_count = 0
            warnings = []

            for uploaded_file in uploaded_files:
                try:
                    file_bytes = uploaded_file.getvalue()
                    file_name, file_size = validate_upload(uploaded_file.name, file_bytes)

                    try:
                        content, page_count = extract_text(file_name, file_bytes)
                    except ValueError as error:
                        content = ""
                        page_count = 0
                        warnings.append(str(error))

                    add_document(
                        filename=file_name,
                        content=content,
                        page_count=page_count,
                        user_id=user_id,
                        file_data=file_bytes,
                        file_type=get_file_type(file_name),
                        file_size=file_size,
                    )
                    saved_count += 1

                except Exception as error:
                    warnings.append(
                        f"خطا در ذخیره فایل {uploaded_file.name}: {error}"
                    )

            if saved_count:
                st.session_state.notice = f"{saved_count} فایل با موفقیت ذخیره شد."
                st.session_state.notice_warn = warnings
                st.session_state.uploader_nonce += 1
                st.rerun()
            elif warnings:
                for warning in warnings:
                    st.error(warning)

    documents = get_documents(user_id)
    total_size = sum((document["file_size"] or 0) for document in documents)

    with st.container(horizontal=True):
        st.metric("تعداد اسناد", len(documents))
        st.metric("حجم کل", format_size(total_size))

    search_query = st.text_input(
        "جست‌وجو در اسناد",
        placeholder="نام فایل یا عبارتی از متن سند را وارد کن",
    )

    if search_query.strip():
        visible = search_documents(search_query.strip(), user_id)
    else:
        visible = documents

    if not visible:
        if search_query.strip():
            st.info("سندی با این عبارت پیدا نشد.")
        else:
            st.info("هنوز سندی به این حساب اضافه نشده است.")

    for document in visible:
        expander = st.expander(
    document_label(document),
    on_change="rerun",
    key=f"document_expander_{document['id']}"
    )   

        if expander.open:
            with expander:
                if document["page_count"]:
                    st.write(f"تعداد صفحات: {document['page_count']}")

                st.write(f"تاریخ ثبت: {document['created_at']}")

                full_document = get_document(document["id"], user_id)

                if not full_document:
                    st.warning("این سند دیگر در دسترس نیست.")
                    continue

                file_data = full_document["file_data"]
                content = full_document["content"] or ""

                if file_data and full_document["file_type"] == ".pdf":
                    st.pdf(
                        bytes(file_data),
                        height=480,
                        alt=full_document["filename"],
                    )

                if content.strip():
                    st.text_area(
                        "متن استخراج‌شده",
                        value=content,
                        height=250,
                        disabled=True,
                        key=f"document_{document['id']}",
                    )
                else:
                    st.info("متنی از این فایل استخراج نشده است.")

                if file_data:
                    st.download_button(
                        label="دانلود فایل اصلی",
                        data=bytes(file_data),
                        file_name=full_document["filename"],
                        mime=MIME_TYPES.get(
                            full_document["file_type"],
                            "application/octet-stream",
                        ),
                        key=f"download_{document['id']}",
                        on_click="ignore",
                        icon=":material/download:",
                    )

                if st.button(
                    "حذف سند",
                    key=f"delete_{document['id']}",
                    icon=":material/delete:",
                ):
                    delete_document(document["id"], user_id)
                    st.session_state.notice = "سند حذف شد."
                    st.rerun()


def show_chat(user_id):
    documents = get_documents(user_id)

    with st.container(horizontal=True, vertical_alignment="center"):
        st.header("پرسش از اسناد")

        if st.session_state.get("chat_messages") and st.button(
            "پاک کردن گفتگو",
            icon=":material/delete_sweep:",
        ):
            st.session_state.chat_messages = []
            st.session_state.pop("suggestion_pills", None)
            st.rerun()

    st.caption(
    f"پاسخ‌ها با مدل محلی {CHAT_MODEL} و فقط از متن اسناد ساخته می‌شوند.")

    if not documents:
        st.info("ابتدا از زبانه اسناد یک فایل اضافه کن.")
        return

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    if len(documents) == 1:
        mode = "این سند"
        selected_id = documents[0]["id"]
        st.caption(f"گفتگو با {documents[0]['filename']}")
    else:
        mode = st.segmented_control(
            "محدوده پاسخ",
            options=["این سند", "همه اسناد"],
            default="این سند",
            required=True,
            key="ai_scope_mode",
        )
        selected_id = None

        if mode == "این سند":
            ids = [document["id"] for document in documents]

            if st.session_state.get("ai_document_id") not in ids:
                st.session_state["ai_document_id"] = ids[0]

            selected_id = st.selectbox(
                "سند",
                options=ids,
                format_func=lambda doc_id: next(
                    document["filename"]
                    for document in documents
                    if document["id"] == doc_id
                ),
                key="ai_document_id",
            )
        else:
            st.caption("پاسخ از متن همه اسناد این حساب جمع می‌شود.")

    scope_key = f"{mode}:{selected_id if mode == 'این سند' else 'all'}"

    if st.session_state.get("chat_scope") != scope_key:
        st.session_state.chat_scope = scope_key
        st.session_state.chat_messages = []
        st.session_state.pop("suggestion_pills", None)

    readable = count_readable_documents(
        user_id,
        selected_id if mode == "این سند" else None,
    )

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            render_sources(message.get("sources"))

    prompt = None

    if readable == 0:
        st.warning("متن قابل پردازشی در سندهای انتخاب‌شده وجود ندارد.")
    elif not st.session_state.chat_messages:
        suggestions = st.empty()
        selected = suggestions.pills(
            "پیشنهاد سؤال",
            SUGGESTIONS,
            label_visibility="collapsed",
            key="suggestion_pills",
        )

        if selected:
            prompt = selected
            suggestions.empty()

    typed = st.chat_input(
        "سؤالت را درباره اسناد بنویس",
        submit_mode="stop",
        disabled=readable == 0,
    )

    if typed:
        prompt = typed

    if not prompt:
        return

    history = list(st.session_state.chat_messages)
    st.session_state.chat_messages.append({
        "role": "user",
        "content": prompt,
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("در حال جست‌وجوی سند") as status:
            contents = get_document_contents(
                user_id,
                selected_id if mode == "این سند" else None,
            )
            chunks = retrieve_from_documents(
                prompt,
                contents,
                top_k=6 if mode == "همه اسناد" else 5,
            )
            status.update(
                label=f"{len(chunks)} بخش مرتبط پیدا شد",
                state="complete",
            )

        if not chunks:
            answer = "بخش مرتبطی با سؤال شما در سند پیدا نشد."
            st.markdown(answer)
            sources = []
        else:
            answer = st.write_stream(
                stream_answer(prompt, chunks, history)
            )

            if not str(answer).strip():
                answer = "پاسخی از مدل دریافت نشد."
                st.markdown(answer)

            sources = [
                {
                    "label": (
                        f"{source} — بخش {index + 1}"
                        if source
                        else f"بخش {index + 1}"
                    ),
                    "text": text,
                }
                for source, index, text in chunks
            ]
            render_sources(sources)

    st.session_state.chat_messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })


def show_dashboard():
    user = st.session_state.user
    user_id = user["id"]

    with st.sidebar:
        st.title("DocuMind AI")
        st.write(f"کاربر: {user['username']}")
        st.button(
            "خروج از حساب",
            on_click=logout,
            icon=":material/logout:",
        )
        st.divider()
        st.caption("نسخه ۱.۰")
        st.caption(f"مدل: {CHAT_MODEL}")

    notice = st.session_state.pop("notice", None)
    warnings = st.session_state.pop("notice_warn", None)

    if notice:
        st.success(notice)

    for warning in warnings or []:
        st.warning(warning)

    library_tab, chat_tab = st.tabs(
        [
            ":material/folder: اسناد",
            ":material/chat: گفتگو",
        ],
        on_change="rerun",
    )

    if library_tab.open:
        show_library(user_id)

    if chat_tab.open:
        show_chat(user_id)


if st.session_state.user is None:
    show_auth_page()
else:
    show_dashboard()
