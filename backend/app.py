from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from flask_talisman import Talisman
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt
from database import inicializar_db
from routes.productos import productos_bp
from routes.entradas import entradas_bp
from routes.salidas import salidas_bp
from routes.devoluciones import devoluciones_bp
from routes.catalogos import catalogos_bp
from routes.traslados import traslados_bp
from routes.pdf_entradas import pdf_entradas_bp
from routes.pdf_salidas import pdf_salidas_bp
from routes.pdf_devoluciones import pdf_devoluciones_bp
from routes.pdf_traslados import pdf_traslados_bp
from routes.auth import auth_bp
from routes.consolidado import consolidado_bp
from routes.pdf_consolidado import pdf_consolidado_bp
from dotenv import load_dotenv

import os
load_dotenv()

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "https://almacen-backend-ae4l.onrender.com"
])

Talisman(app, force_https=False, content_security_policy=False)

from extensions import limiter
limiter.init_app(app)

# Clave secreta para firmar los tokens JWT
# En produccion esto deberia ser una variable de entorno
jwt_secret = os.getenv('JWT_SECRET_KEY')

if not jwt_secret:
    raise RuntimeError(
        'Falta configurar JWT_SECRET_KEY'
    )

app.config['JWT_SECRET_KEY'] = jwt_secret
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 28800  # 8 horas en segundos
jwt = JWTManager(app)


# ============================================================
# RESTRICCIÓN GLOBAL PARA EL ROL "porteria"
#
# El usuario de portería solo debe poder CONSULTAR
# (método GET) las salidas y su PDF, además de las rutas
# básicas de sesión (login, /me). Este filtro se aplica una
# sola vez aquí, antes de que la petición llegue a cualquier
# blueprint, para no depender de que cada archivo de rutas
# (productos, entradas, devoluciones, traslados, catálogos,
# consolidado...) recuerde bloquearlo por su cuenta.
#
# Si en el futuro se agrega un archivo de rutas nuevo, queda
# bloqueado para portería automáticamente, sin tener que
# tocar nada aquí.
# ============================================================

@app.before_request
def restringir_rol_porteria():

    # Solo nos interesa la API. Los archivos estáticos del
    # frontend (index.html, css, js) siempre deben cargar.
    if not request.path.startswith('/api/'):
        return None

    # El preflight de CORS no lleva credenciales que revisar.
    if request.method == 'OPTIONS':
        return None

    # Si no hay token (por ejemplo, en /api/auth/login) no hay
    # nada que restringir todavía.
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        return None

    claims = get_jwt()

    if not claims or claims.get('rol') != 'porteria':
        return None

    # Rutas de sesión (login, /me, etc.) siempre accesibles.
    if request.path.startswith('/api/auth'):
        return None

    # Único permiso real de portería: CONSULTAR salidas
    # (listado y detalle) y ver/descargar su PDF.
    puede_ver_esto = (
        request.method == 'GET'
        and (
            request.path.startswith('/api/salidas')
            or request.path.startswith('/api/pdf/salida/')
        )
    )

    if puede_ver_esto:
        return None

    return jsonify({
        'error': (
            'El usuario de portería solo puede consultar '
            'las salidas'
        )
    }), 403


app.register_blueprint(productos_bp,        url_prefix='/api/productos')
app.register_blueprint(entradas_bp,         url_prefix='/api/entradas')
app.register_blueprint(salidas_bp,          url_prefix='/api/salidas')
app.register_blueprint(devoluciones_bp,     url_prefix='/api/devoluciones')
app.register_blueprint(catalogos_bp,        url_prefix='/api/catalogos')
app.register_blueprint(traslados_bp, url_prefix='/api/traslados')
app.register_blueprint(pdf_entradas_bp,     url_prefix='/api/pdf')
app.register_blueprint(pdf_salidas_bp,      url_prefix='/api/pdf')
app.register_blueprint(pdf_devoluciones_bp, url_prefix='/api/pdf')
app.register_blueprint(pdf_traslados_bp, url_prefix='/api/pdf')
app.register_blueprint(auth_bp,             url_prefix='/api/auth')
app.register_blueprint(consolidado_bp, url_prefix='/api/consolidado')
app.register_blueprint(pdf_consolidado_bp, url_prefix='/api/pdf')

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)

inicializar_db()

if __name__ == '__main__':
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, port=5000, host='0.0.0.0')