@echo off
title Occidente - Almacen (servidor local)

rem ============================================================
rem Este archivo va en la carpeta raiz del proyecto (almacen\),
rem al mismo nivel que las carpetas "backend" y "frontend".
rem Doble clic aqui en vez de abrir una terminal manualmente.
rem ============================================================

cd /d "%~dp0backend"

rem Si usas un entorno virtual (venv), descomenta la siguiente
rem linea y ajusta la ruta a tu carpeta del entorno:
rem call venv\Scripts\activate.bat

echo Iniciando el servidor de Almacen...
echo No cierres esta ventana mientras estes usando la app.
echo Para apagar el servidor, cierra esta ventana o presiona Ctrl+C.
echo.

python app.py

echo.
echo El servidor se detuvo (o hubo un error arriba).
pause
