import streamlit as st

st.set_page_config(
    page_title="DocuMind AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* جهت کلی برنامه */
html, body, [data-testid="stApp"] {
    direction: rtl;
    text-align: right;
}

/* فونت و ظاهر کلی */
[data-testid="stApp"] {
    background-color: #0f1018;
    color: #f3f3f7;
}

/* نوار کناری */
[data-testid="stSidebar"] {
    background-color: #171824;
    border-left: 1px solid #302b46;
}

/* عنوان‌ها و متن‌ها */
h1, h2, h3, p, label {
    text-align: right;
}

/* دکمه‌ها */
.stButton > button {
    direction: rtl;
    text-align: center;
    border-radius: 10px;
    border: 1px solid #7654d6;
    background-color: #7654d6;
    color: white;
    font-weight: 600;
    transition: 0.2s ease;
}

/* حالت قرار گرفتن ماوس روی دکمه */
.stButton > button:hover {
    background-color: #6242bb;
    border-color: #9b83ed;
    color: white;
}

/* ورودی‌های متن */
.stTextInput input,
.stTextArea textarea {
    direction: rtl;
    text-align: right;
    border-radius: 8px;
}

/* کادرهای انتخاب فایل */
[data-testid="stFileUploader"] {
    direction: rtl;
    text-align: right;
}

/* کارت‌ها و بخش‌های محتوایی */
[data-testid="stMetric"],
[data-testid="stExpander"] {
    direction: rtl;
    text-align: right;
}

/* نوار بالایی */
[data-testid="stHeader"] {
    background-color: rgba(15, 16, 24, 0.9);
}
</style>
""", unsafe_allow_html=True)


import streamlit as st
import pymupdf
from file_processor import extract_text, get_file_type
from database import add_document

from database import (
    initialize_database,
    create_user,
    authenticate_user,
    add_document,
    get_documents,
    get_document,
    delete_document,
    search_documents,
)

st.set_page_config(
    page_title="DocuMind AI",
    page_icon="📚",
    layout="wide",
)

initialize_database()

if "user" not in st.session_state:
    st.session_state.user = None


# -------------------------
# صفحه ورود و ثبت نام
# -------------------------

def show_auth_page():
    st.title("📚 DocuMind AI")
    st.subheader("دستیار هوشمند اسناد")
    st.write("برای استفاده از برنامه وارد حساب خودت شو.")

    login_tab, register_tab = st.tabs(
        ["ورود", "ثبت‌نام"]
    )

    with login_tab:
        with st.form("login_form"):
            username = st.text_input(
                "نام کاربری",
                key="login_username",
            )

            password = st.text_input(
                "رمز عبور",
                type="password",
                key="login_password",
            )

            submitted = st.form_submit_button(
                "ورود به حساب",
                type="primary",
            )

            if submitted:
                user = authenticate_user(
                    username,
                    password,
                )

                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error(
                        "نام کاربری یا رمز عبور اشتباه است."
                    )

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input(
                "نام کاربری جدید",
                key="register_username",
            )

            new_password = st.text_input(
                "رمز عبور جدید (حداقل ۸ کاراکتر)",
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
            )

            if submitted:
                if new_password != confirm_password:
                    st.error(
                        "رمز عبور و تکرار آن یکسان نیستند."
                    )
                else:
                    success, message = create_user(
                        new_username,
                        new_password,
                    )

                    if success:
                        st.success(message)
                        st.info(
                            "حساب ساخته شد؛ حالا از بخش ورود "
                            "وارد حساب خودت شو."
                        )
                    else:
                        st.error(message)


# -------------------------
# صفحه اصلی برنامه
# -------------------------

def show_dashboard():
    user = st.session_state.user
    user_id = user["id"]

    with st.sidebar:
        st.title("📚 DocuMind AI")
        st.write(f"کاربر: {user['username']}")

        if st.button("خروج از حساب"):
            st.session_state.user = None
            st.rerun()

        st.divider()
        st.caption("نسخه آزمایشی 0.3")

    st.title("مدیریت اسناد")
    st.write(
        "اسناد خودت را ذخیره کن، جست‌وجو کن "
        "و متن آن‌ها را بخوان."
    )

    # افزودن سند
    st.header("📄 افزودن سند")

    uploaded_files = st.file_uploader(
        "فایل‌های موردنظرت را انتخاب کن",
        type=None,
        accept_multiple_files=True,
        key="file_uploader",
    )

    if st.button("ذخیره اسناد", type="primary"):
        if not uploaded_files:
            st.warning("ابتدا حداقل یک فایل انتخاب کن.")
        else:
            saved_count = 0

            for uploaded_file in uploaded_files:
                try:
                    file_bytes = uploaded_file.getvalue()
                    file_name = uploaded_file.name
                    file_size = len(file_bytes)

                    try:
                        content, page_count = extract_text(
                            file_name,
                            file_bytes
                        )
                    except ValueError as error:
                        content = ""
                        page_count = 0

                        st.warning(
                            f"فایل {file_name} ذخیره می‌شود، "
                            f"اما استخراج متن ناموفق بود: {error}"
                        )

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
                    st.error(
                        f"خطا در ذخیره فایل "
                        f"{uploaded_file.name}: {error}"
                    )

            if saved_count > 0:
                st.success(
                    f"{saved_count} فایل با موفقیت ذخیره شد."
                )
                st.rerun()

    st.divider()

    # اسناد ذخیره شده
    st.header("📚 اسناد ذخیره شده")

    search_query = st.text_input(
        "🔍 جست‌وجو در اسناد",
        placeholder="نام فایل یا عبارت موردنظر را وارد کن..."
    )

    if search_query.strip():
        documents = search_documents(
            search_query.strip(),
            user_id
        )
    else:
        documents = get_documents(user_id)

    if not documents:
        st.info("هنوز سندی به این حساب اضافه نشده است.")

    for document in documents:
        with st.expander(
            f"{document['filename']} "
            f"(شناسه: {document['id']})"
        ):
            st.write(
                f"تعداد صفحات: {document['page_count']}"
            )

            st.write(
                f"تاریخ ثبت: {document['created_at']}"
            )

            full_document = get_document(
                document["id"],
                user_id
            )

            if full_document:
                st.write(
                    f"نوع فایل: {full_document['file_type'] or 'نامشخص'}"
                )

    file_size = full_document["file_size"] or 0

    st.write(
        f"حجم فایل: {file_size / 1024:.2f} KB"
    )

    st.text_area(
        "متن سند",
        value=full_document["content"] or "متنی استخراج نشده است.",
        height=250,
        key=f"document_{document['id']}"
    )

    file_data = full_document["file_data"]

    if file_data:
        st.download_button(
            label="⬇️ دانلود فایل اصلی",
            data=file_data,
            file_name=full_document["filename"],
            key=f"download_{document['id']}",
        )

        if st.button(
                "حذف سند",
                key=f"delete_{document['id']}"
            ):
                delete_document(
                    document["id"],
                    user_id
                )

                st.success("سند حذف شد.")
                st.rerun()


# -------------------------
# اجرای برنامه
# -------------------------

if st.session_state.user is None:
    show_auth_page()
else:
    show_dashboard()