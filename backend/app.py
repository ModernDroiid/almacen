from flask import Flask, send_from_directory
from flask_cors import CORS
from database import inicializar_db
from routes.productos import productos_bp
from routes.entradas import entradas_bp
from routes.salidas import salidas_bp
from routes.devoluciones import devoluciones_bp
from routes.catalogos import catalogos_bp
from routes.pdf_entradas import pdf_entradas_bp
from routes.pdf_salidas import pdf_salidas_bp
from routes.pdf_devoluciones import pdf_devoluciones_bp
from routes.auth import auth_bp
import os

app = Flask(__name__)
CORS(app)

app.register_blueprint(productos_bp,        url_prefix='/api/productos')
app.register_blueprint(entradas_bp,         url_prefix='/api/entradas')
app.register_blueprint(salidas_bp,          url_prefix='/api/salidas')
app.register_blueprint(devoluciones_bp,     url_prefix='/api/devoluciones')
app.register_blueprint(catalogos_bp,        url_prefix='/api/catalogos')
app.register_blueprint(pdf_entradas_bp,     url_prefix='/api/pdf')
app.register_blueprint(pdf_salidas_bp,      url_prefix='/api/pdf')
app.register_blueprint(pdf_devoluciones_bp, url_prefix='/api/pdf')
app.register_blueprint(auth_bp,             url_prefix='/api/auth')

# ── Sirve el frontend desde Flask ───────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)

inicializar_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)