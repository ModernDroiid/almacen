from database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(entradas)")
columnas = [c[1] for c in cursor.fetchall()]
print("Columnas actuales en entradas:", columnas)

if 'destino' not in columnas:
    conn.execute('ALTER TABLE entradas ADD COLUMN destino TEXT')
    print("Columna 'destino' agregada")

if 'numero_documento' not in columnas:
    conn.execute('ALTER TABLE entradas ADD COLUMN numero_documento TEXT')
    print("Columna 'numero_documento' agregada")

if 'observaciones' not in columnas:
    conn.execute('ALTER TABLE entradas ADD COLUMN observaciones TEXT')
    print("Columna 'observaciones' agregada")

conn.commit()

cursor.execute("PRAGMA table_info(entradas)")
print("Columnas finales:", [c[1] for c in cursor.fetchall()])

cursor.execute("PRAGMA table_info(detalle_entradas)")
columnas_d = [c[1] for c in cursor.fetchall()]
print("Columnas en detalle_entradas:", columnas_d)

if 'modelo' not in columnas_d:
    conn.execute('ALTER TABLE detalle_entradas ADD COLUMN modelo TEXT')
if 'marca' not in columnas_d:
    conn.execute('ALTER TABLE detalle_entradas ADD COLUMN marca TEXT')
if 'serial' not in columnas_d:
    conn.execute('ALTER TABLE detalle_entradas ADD COLUMN serial TEXT')
if 'unidad' not in columnas_d:
    conn.execute('ALTER TABLE detalle_entradas ADD COLUMN unidad TEXT')

conn.commit()
conn.close()
print("Listo")