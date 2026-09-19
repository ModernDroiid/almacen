# ============================================================
# borrar_pruebas.py
#
# Borra todos los datos de PRUEBA para empezar de cero:
#   productos, entradas, salidas, devoluciones, traslados,
#   modelos, marcas.
#
# "Puntos" no es una tabla propia (se arma a partir de las
# salidas/devoluciones), así que se limpia solo al borrar esas.
#
# NO toca: sedes, usuarios, unidades — eso se queda igual.
#
# Con CASCADE, Postgres borra en automático todo lo que dependa
# de estas tablas (detalle_entradas, detalle_salidas,
# detalle_devoluciones, detalle_traslados, equipos, inventario),
# sin que tengamos que acordarnos del orden exacto.
#
# RESTART IDENTITY reinicia los contadores de ID, así que el
# próximo producto/entrada/salida/etc. que crees empezará
# de nuevo desde el 1.
#
# ¡OJO! Esto NO se puede deshacer. Úsalo solo en tu base de
# pruebas local.
# ============================================================

from database import get_connection

TABLAS = [
    "marcas",
    "modelos",
    "productos",
    "entradas",
    "salidas",
    "devoluciones",
    "traslados",
]


def borrar_datos_de_prueba():

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute(f"""
                TRUNCATE TABLE
                    {', '.join(TABLAS)}
                RESTART IDENTITY CASCADE
            """)

        conn.commit()

        print("Listo: se borraron todos los datos de prueba.")
        print("Sedes, usuarios y unidades quedaron intactos.")

    except Exception as e:

        conn.rollback()
        print(f"Algo salió mal, no se borró nada: {e}")

    finally:

        conn.close()


if __name__ == "__main__":

    respuesta = input(
        "Esto va a BORRAR productos, entradas, salidas, "
        "devoluciones, traslados, modelos y marcas. "
        "No se puede deshacer.\n"
        "¿Seguro que quieres continuar? (escribe 'si' para confirmar): "
    )

    if respuesta.strip().lower() == "si":
        borrar_datos_de_prueba()
    else:
        print("Cancelado, no se borró nada.")