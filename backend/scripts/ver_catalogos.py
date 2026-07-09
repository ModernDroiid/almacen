from database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute('SELECT * FROM modelos')
print("MODELOS:", cursor.fetchall())

cursor.execute('SELECT * FROM marcas')
print("MARCAS:", cursor.fetchall())

conn.close()