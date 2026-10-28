from database import get_connection, initialize_database

initialize_database()

with get_connection() as connection:
    users = connection.execute("""
        SELECT id, username
        FROM users
        ORDER BY id
    """).fetchall()

    if not users:
        print("هنوز هیچ حساب کاربری ساخته نشده است.")
    else:
        print("\nحساب‌های موجود:\n")

        for user in users:
            print(f"ID: {user['id']} | Username: {user['username']}")

        print("\nشناسه حسابی را وارد کن که باید اسناد قدیمی به آن منتقل شوند.")
        selected_id = input("User ID: ").strip()

        if not selected_id.isdigit():
            print("شناسه واردشده معتبر نیست.")
        else:
            selected_id = int(selected_id)

            selected_user = connection.execute("""
                SELECT id, username
                FROM users
                WHERE id = ?
            """, (selected_id,)).fetchone()

            if selected_user is None:
                print("حساب کاربری پیدا نشد.")
            else:
                result = connection.execute("""
                    UPDATE documents
                    SET user_id = ?
                    WHERE user_id IS NULL
                """, (selected_id,))

                print(
                    f"\nتعداد اسناد منتقل‌شده به حساب "
                    f"{selected_user['username']}: {result.rowcount}"
                )