from ai_engine import (
    split_into_chunks,
    retrieve_relevant_chunks,
    ask_ai
)

context = """
DocuMind AI یک نرم‌افزار مدیریت اسناد است.
این نرم‌افزار با زبان پایتون توسعه داده شده است.

هدف اصلی پروژه، جست‌وجو و تحلیل فایل‌ها به صورت آفلاین است.

این نرم‌افزار از فرمت‌های PDF، DOCX، XLSX و PPTX پشتیبانی می‌کند.

هوش مصنوعی پروژه با استفاده از مدل Gemma اجرا می‌شود.
"""

question = "DocuMind AI از چه فرمت‌هایی پشتیبانی می‌کند؟"

print("تعداد بخش‌های ایجاد شده:")
print(len(split_into_chunks(context)))

print("\nبخش‌های مرتبط با سؤال:")
chunks = retrieve_relevant_chunks(question, context)

for index, chunk in chunks:
    print(f"\nبخش {index + 1}:")
    print(chunk)

print("\nدر حال دریافت پاسخ از هوش مصنوعی...")

answer = ask_ai(question, context)

print("\nپاسخ نهایی:")
print(answer)