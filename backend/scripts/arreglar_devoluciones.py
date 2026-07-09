from database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(devoluciones)")
columnas = [c[1] for c in cursor.fetchall()]
print("Columnas actuales en devoluciones:", columnas)

if 'salida_id' not in columnas:
    conn.execute('ALTER TABLE devoluciones ADD COLUMN salida_id INTEGER')
    print("Columna 'salida_id' agregada")

if 'origen' not in columnas:
    conn.execute('ALTER TABLE devoluciones ADD COLUMN origen TEXT')
    print("Columna 'origen' agregada")

if 'destino' not in columnas:
    conn.execute('ALTER TABLE devoluciones ADD COLUMN destino TEXT')
    print("Columna 'destino' agregada")

if 'numero_documento' not in columnas:
    conn.execute('ALTER TABLE devoluciones ADD COLUMN numero_documento TEXT')
    print("Columna 'numero_documento' agregada")

if 'motivo' not in columnas:
    conn.execute('ALTER TABLE devoluciones ADD COLUMN motivo TEXT')
    print("Columna 'motivo' agregada")

if 'observaciones' not in columnas:
    conn.execute('ALTER TABLE devoluciones ADD COLUMN observaciones TEXT')
    print("Columna 'observaciones' agregada")

conn.commit()

cursor.execute("PRAGMA table_info(devoluciones)")
print("Columnas finales:", [c[1] for c in cursor.fetchall()])

cursor.execute("PRAGMA table_info(detalle_devoluciones)")
columnas_d = [c[1] for c in cursor.fetchall()]
print("Columnas en detalle_devoluciones:", columnas_d)

if 'modelo' not in columnas_d:
    conn.execute('ALTER TABLE detalle_devoluciones ADD COLUMN modelo TEXT')
if 'marca' not in columnas_d:
    conn.execute('ALTER TABLE detalle_devoluciones ADD COLUMN marca TEXT')
if 'serial' not in columnas_d:
    conn.execute('ALTER TABLE detalle_devoluciones ADD COLUMN serial TEXT')
if 'unidad' not in columnas_d:
    conn.execute('ALTER TABLE detalle_devoluciones ADD COLUMN unidad TEXT')

conn.commit()
conn.close()
print("Listo")