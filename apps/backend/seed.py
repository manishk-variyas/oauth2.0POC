import psycopg2
from datetime import datetime

# Connect to notes database
conn = psycopg2.connect(
    host="localhost", port=5432, database="notes", user="notes", password="notes123"
)

cursor = conn.cursor()

# Seed data with real Keycloak user IDs
notes_data = [
    # Admin user notes (ef998ffa-ae23-4630-a812-ec108f4279bf)
    (
        "Welcome to Notes App",
        "This is your first note! You can create, edit and delete notes.",
        "ef998ffa-ae23-4630-a812-ec108f4279bf",
        False,
    ),
    (
        "Project Ideas",
        "1. Build a TODO app\n2. Add Markdown support\n3. Implement sharing",
        "ef998ffa-ae23-4630-a812-ec108f4279bf",
        False,
    ),
    (
        "Public Note - For Everyone",
        "This note is visible to all users!",
        "ef998ffa-ae23-4630-a812-ec108f4279bf",
        True,
    ),
    # Test user notes (7a093aea-06ce-45ef-b514-168e98ba5285)
    (
        "My Shopping List",
        "Milk\nBread\nEggs\nButter\nCheese",
        "7a093aea-06ce-45ef-b514-168e98ba5285",
        False,
    ),
    (
        "Meeting Notes",
        "Discussed the quarterly targets.\n- Sales: +20%\n- Support: Improve response time",
        "7a093aea-06ce-45ef-b514-168e98ba5285",
        False,
    ),
    (
        "Public Ideas",
        "Let's make the app open source!",
        "7a093aea-06ce-45ef-b514-168e98ba5285",
        True,
    ),
]

# Insert notes
for title, content, user_id, is_public in notes_data:
    cursor.execute(
        """
        INSERT INTO notes (title, content, user_id, is_public, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """,
        (title, content, user_id, is_public, datetime.now(), datetime.now()),
    )

conn.commit()
print(f"Inserted {len(notes_data)} notes")

# Verify
cursor.execute("SELECT COUNT(*) FROM notes")
print(f"Total notes in database: {cursor.fetchone()[0]}")

cursor.close()
conn.close()
