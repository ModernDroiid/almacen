from database import get_connection

conn = get_connection()
try:
    conn.execute('ALTER TABLE productos ADD COLUMN sede_id INTEGER REFERENCES sedes(id)')
    print('Columna sede_id agregada a productos')
except Exception as e:
    print(f'productos: {e}')

# Asignamos todos los productos existentes a la Sede Principal (id=1)
conn.execute('UPDATE productos SET sede_id = 1 WHERE sede_id IS NULL')
conn.commit()
conn.close()
print('Listo')