
from ai_engine import (
    get_embeddings,
    retrieve_relevant_chunks,
    ask_ai
)

print("=" * 45)
print("DOCUMIND AI - ENGINE TEST")
print("=" * 45)

# 1. تست Embedding
print("\n[1] Testing semantic embeddings...")

vectors = get_embeddings([
    "مدیریت اسناد و اطلاعات",
    "هوش مصنوعی و تحلیل داده"
])

print("Embedding count:", len(vectors))
print("Vector dimensions:", len(vectors[0]))

# 2. ساخت سند آزمایشی
print("\n[2] Testing document retrieval...")

document = """
قوانین مرخصی کارکنان:

کارکنان برای استفاده از مرخصی عادی
باید حداقل سه روز قبل درخواست خود را ثبت کنند.

شروع مرخصی تنها پس از تأیید مدیر امکان‌پذیر است.

در شرایط اضطراری، کارمند باید در همان روز
موضوع را به مدیر اطلاع دهد.

مدیر مسئول بررسی درخواست‌های مرخصی است.
"""

question = """
برای مرخصی عادی چند روز زودتر باید درخواست بدهم؟
در شرایط اضطراری چه کاری باید انجام دهم؟
"""

chunks = retrieve_relevant_chunks(
    question,
    document,
    top_k=5
)

print("Retrieved chunks:", len(chunks))

for index, chunk in chunks:
    print(f"\nChunk {index + 1}:")
    print(chunk[:250])

# 3. تست تولید پاسخ
print("\n[3] Testing Qwen response...")

answer = ask_ai(
    question,
    document,
    relevant_chunks=chunks
)

print("\nAI ANSWER:")
print(answer)

print("\n" + "=" * 45)
print("TEST FINISHED")
print("=" * 45)
