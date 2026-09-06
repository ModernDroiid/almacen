-- ============================================================
-- CUANDO UN EQUIPO SALE:
-- DISPONIBLE -> INSTALADO
-- ============================================================

CREATE OR REPLACE FUNCTION actualizar_equipo_al_salir()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN

    IF NEW.equipo_id IS NOT NULL THEN

        UPDATE equipos
        SET
            estado = 'INSTALADO',
            observaciones =
                CASE
                    WHEN COALESCE(observaciones, '') = ''
                    THEN 'Salida de almacén'
                    ELSE observaciones || ' | Salida de almacén'
                END
        WHERE id = NEW.equipo_id;

    END IF;

    RETURN NEW;
END;
$$;


DROP TRIGGER IF EXISTS trigger_actualizar_equipo_salida
ON detalle_salidas;


CREATE TRIGGER trigger_actualizar_equipo_salida
AFTER INSERT ON detalle_salidas
FOR EACH ROW
EXECUTE FUNCTION actualizar_equipo_al_salir();


-- ============================================================
-- AL ANULAR UNA SALIDA:
-- el equipo vuelve a DISPONIBLE solamente si no existe
-- otra salida ACTIVA para ese mismo equipo.
-- ============================================================

CREATE OR REPLACE FUNCTION revertir_equipos_salida_anulada()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN

    IF OLD.estado = 'ACTIVA'
       AND NEW.estado = 'ANULADA' THEN

        UPDATE equipos e
        SET
            estado = 'DISPONIBLE',
            observaciones =
                CASE
                    WHEN COALESCE(e.observaciones, '') = ''
                    THEN 'Salida anulada'
                    ELSE e.observaciones || ' | Salida anulada'
                END
        FROM detalle_salidas d
        WHERE d.salida_id = NEW.id
          AND d.equipo_id = e.id

          -- No tocar el equipo si actualmente
          -- pertenece a otra salida activa.
          AND NOT EXISTS (
              SELECT 1
              FROM detalle_salidas d2
              INNER JOIN salidas s2
                  ON s2.id = d2.salida_id
              WHERE d2.equipo_id = e.id
                AND d2.salida_id <> NEW.id
                AND s2.estado = 'ACTIVA'
          );

    END IF;

    RETURN NEW;
END;
$$;


DROP TRIGGER IF EXISTS trigger_revertir_equipos_salida
ON salidas;


CREATE TRIGGER trigger_revertir_equipos_salida
AFTER UPDATE OF estado ON salidas
FOR EACH ROW
EXECUTE FUNCTION revertir_equipos_salida_anulada();