import sqlite3

# Bikin database baru
conn = sqlite3.connect('chatbot.db')
cursor = conn.cursor()

# Bikin tabel pertanyaan
cursor.execute('''
    CREATE TABLE IF NOT EXISTS pertanyaan_baru (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pertanyaan TEXT,
        waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()

print("Database & tabel berhasil dibuat.")

