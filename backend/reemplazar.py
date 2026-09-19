from pathlib import Path

p = Path(r"..\frontend\js\app.js.reparado2")

s = p.read_text(encoding="utf-8")

s = s.replace("`âš ï¸ No se puede eliminar", "`\\u26A0\\uFE0F No se puede eliminar")
s = s.replace("`â†©ï¸ Devoluciones:", "`\\u21A9\\uFE0F Devoluciones:")

p.write_text(s, encoding="utf-8")

print("Cambios realizados.")