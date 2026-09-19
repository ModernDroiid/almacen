from pathlib import Path

src = Path(r"..\frontend\js\app.js.backup")
dst = Path(r"..\frontend\js\app.js.reparado")

s = src.read_text(encoding="utf-8")

print("ANTES:")
print("Ã:", s.count("Ã"))
print("Â:", s.count("Â"))
print("â:", s.count("â"))
print("├:", s.count("├"))
print("┬:", s.count("┬"))

mejor = s
score = sum(mejor.count(c) for c in "ÃÂâ├┬ï")

for i in range(6):
    cambiado = False

    for enc in ("cp1252", "latin1"):
        try:
            x = mejor.encode(enc).decode("utf-8")
            nuevo_score = sum(x.count(c) for c in "ÃÂâ├┬ï")

            if nuevo_score < score:
                mejor = x
                score = nuevo_score
                cambiado = True
                print("Paso", i + 1, "con", enc, "->", score)
                break

        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    if not cambiado:
        break

dst.write_text(mejor, encoding="utf-8")

print()
print("DESPUES:")
print("Ã:", mejor.count("Ã"))
print("Â:", mejor.count("Â"))
print("â:", mejor.count("â"))
print("├:", mejor.count("├"))
print("┬:", mejor.count("┬"))
print()
print("Archivo creado:", dst)