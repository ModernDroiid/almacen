from pathlib import Path

archivo = Path(r"..\frontend\js\app.js.reparado2")

texto = archivo.read_text(encoding="utf-8-sig")

reemplazos = {
    "âš ï¸": "⚠️",
    "âœ“": "✓",
    "ðŸ—‘ï¸": "🗑️",
    "â†©ï¸": "↩️",
}

for malo, bueno in reemplazos.items():
    texto = texto.replace(malo, bueno)

archivo.write_text(texto, encoding="utf-8")

print("Reparación específica realizada.")
print("â =", texto.count("â"))
print("Ã =", texto.count("Ã"))
print("ð =", texto.count("ð"))