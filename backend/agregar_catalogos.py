from database import get_connection

conn = get_connection()
conn.executescript('''
    CREATE TABLE IF NOT EXISTS marcas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS modelos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL
    );
''')
conn.commit()
conn.close()
print('Listo')