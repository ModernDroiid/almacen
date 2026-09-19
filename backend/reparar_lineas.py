from pathlib import Path

src = Path(r"..\frontend\js\app.js.backup")
dst = Path(r"..\frontend\js\app.js.reparado2")

s = src.read_text(encoding="utf-8-sig")

def puntuacion(texto):
    malos = ["Ã", "Â", "â", "ð", "œ", "ž", "™", " "]
    return sum(texto.count(x) for x in malos)

lineas = s.splitlines(keepends=True)
resultado = []

reparadas = 0

for linea in lineas:
    actual = linea

    for _ in range(4):
        mejor = actual
        mejor_score = puntuacion(actual)

        for enc in ("cp1252", "latin1"):
            try:
                candidato = actual.encode(enc).decode("utf-8")
                score = puntuacion(candidato)

                if score < mejor_score:
                    mejor = candidato
                    mejor_score = score
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

        if mejor == actual:
            break

        actual = mejor
        reparadas += 1

    resultado.append(actual)

reparado = "".join(resultado)

dst.write_text(reparado, encoding="utf-8-sig")

print("================================")
print("REPARACIÓN TERMINADA")
print("================================")
print("Líneas procesadas:", len(lineas))
print("Cambios realizados:", reparadas)
print()
print("ANTES")
print("Ã:", s.count("Ã"))
print("Â:", s.count("Â"))
print("â:", s.count("â"))
print()
print("DESPUÉS")
print("Ã:", reparado.count("Ã"))
print("Â:", reparado.count("Â"))
print("â:", reparado.count("â"))
print()
print("Archivo creado:")
print(dst)