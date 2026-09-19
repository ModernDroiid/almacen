from pathlib import Path

p = Path(r"..\frontend\js\app.js.backup")
s = p.read_text(encoding="utf-8-sig")

print("--- COMPROBACIÓN ---")

for palabra in [
    "acciÃ³n",
    "histÃ³ricos",
    "â€”",
    "âœ“",
    "Â¿"
]:
    print(repr(palabra), "->", palabra in s)