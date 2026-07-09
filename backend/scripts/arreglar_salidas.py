from database import get_connection

conn = get_connection()
cursor = conn.cursor()

# Vemos qué columnas tiene la tabla salidas actualmente
cursor.execute("PRAGMA table_info(salidas)")
columnas = [c[1] for c in cursor.fetchall()]
print("Columnas actuales en salidas:", columnas)

# Si falta 'obra', la agregamos
if 'obra' not in columnas:
    conn.execute('ALTER TABLE salidas ADD COLUMN obra TEXT')
    print("Columna 'obra' agregada")

if 'destino' not in columnas:
    conn.execute('ALTER TABLE salidas ADD COLUMN destino TEXT')
    print("Columna 'destino' agregada")

if 'numero_documento' not in columnas:
    conn.execute('ALTER TABLE salidas ADD COLUMN numero_documento TEXT')
    print("Columna 'numero_documento' agregada")

if 'observaciones' not in columnas:
    conn.execute('ALTER TABLE salidas ADD COLUMN observaciones TEXT')
    print("Columna 'observaciones' agregada")

conn.commit()

# Verificamos de nuevo
cursor.execute("PRAGMA table_info(salidas)")
columnas = [c[1] for c in cursor.fetchall()]
print("Columnas finales:", columnas)

# Lo mismo para detalle_salidas
cursor.execute("PRAGMA table_info(detalle_salidas)")
columnas_d = [c[1] for c in cursor.fetchall()]
print("Columnas en detalle_salidas:", columnas_d)

if 'modelo' not in columnas_d:
    conn.execute('ALTER TABLE detalle_salidas ADD COLUMN modelo TEXT')
    print("Columna 'modelo' agregada a detalle_salidas")

if 'marca' not in columnas_d:
    conn.execute('ALTER TABLE detalle_salidas ADD COLUMN marca TEXT')
    print("Columna 'marca' agregada a detalle_salidas")

if 'serial' not in columnas_d:
    conn.execute('ALTER TABLE detalle_salidas ADD COLUMN serial TEXT')
    print("Columna 'serial' agregada a detalle_salidas")

conn.commit()
conn.close()
print("Listo")