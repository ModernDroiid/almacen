BEGIN;

-- ============================================================
-- 1. Agregar equipo_id a detalle_salidas
-- ============================================================

ALTER TABLE detalle_salidas
ADD COLUMN IF NOT EXISTS equipo_id INTEGER;

-- ============================================================
-- 2. Relación con equipos
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_detalle_salidas_equipo'
    ) THEN

        ALTER TABLE detalle_salidas
        ADD CONSTRAINT fk_detalle_salidas_equipo
        FOREIGN KEY (equipo_id)
        REFERENCES equipos(id)
        ON DELETE RESTRICT;

    END IF;
END
$$;

-- ============================================================
-- 3. Un mismo equipo no puede aparecer dos veces
--    dentro de la misma salida
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS
idx_detalle_salidas_salida_equipo
ON detalle_salidas (
    salida_id,
    equipo_id
)
WHERE equipo_id IS NOT NULL;

COMMIT;