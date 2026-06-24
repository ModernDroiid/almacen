from database import get_connection

conn = get_connection()
conn.execute('ALTER TABLE detalle_entradas ADD COLUMN unidad TEXT')
conn.execute('ALTER TABLE detalle_salidas ADD COLUMN unidad TEXT')
conn.commit()
conn.close()
print('Listo')