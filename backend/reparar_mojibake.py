from pathlib import Path

src = Path(r"..\frontend\js\app.js.backup")
dst = Path(r"..\frontend\js\app.js.reparado")

s = src.read_text(encoding="utf-8-sig")

def reparar(texto):
    actual = texto

    for _ in range(5):
        try:
            nuevo = actual.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break

        # Solo aceptamos la conversión si realmente mejora
        malos_actual = sum(actual.count(x) for x in ["Ã", "Â", "â"])
        malos_nuevo = sum(nuevo.count(x) for x in ["Ã", "Â", "â"])

        if malos_nuevo < malos_actual:
            actual = nuevo
        else:
            break

    return actual


print("Analizando backup...")
print("ANTES")
print("Ã:", s.count("Ã"))
print("Â:", s.count("Â"))
print("â:", s.count("â"))

reparado = reparar(s)

dst.write_text(reparado, encoding="utf-8")

print()
print("DESPUÉS")
print("Ã:", reparado.count("Ã"))
print("Â:", reparado.count("Â"))
print("â:", reparado.count("â"))

print()
print("Archivo creado:")
print(dst)