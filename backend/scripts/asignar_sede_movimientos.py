from database import get_connection
conn = get_connection()
for tabla in ['entradas', 'salidas', 'devoluciones']:
    conn.execute(f'UPDATE {tabla} SET sede_id = 1 WHERE sede_id IS NULL')
conn.commit()
conn.close()
print('Listo')