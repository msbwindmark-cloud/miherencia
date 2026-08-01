#!/bin/bash
# ============================================
# LIMPIEZA SEGURA DE PYTHONANYWHERE
# Ejecutar paso a paso en la consola bash
# ============================================

# --- PASO 1: Ver cuánto espacio ocupas ---
echo "=== DIAGNÓSTICO INICIAL ==="
du -sh ~/.virtualenvs/* ~/proyectoafmgde/ ~/.cache/ ~/.local/ 2>/dev/null

# --- PASO 2: Ver qué hay en .local/ (solo lectura, no borra nada) ---
echo "=== CONTENIDO DE .local ==="
du -sh ~/.local/lib/* ~/.local/share/* 2>/dev/null | sort -rh

# --- PASO 3: Verificar que tu app usa el venv y NO .local ---
echo "=== VERIFICAR ORIGEN DE DJANGO ==="
source ~/.virtualenvs/venv/bin/activate
python -c "import django; print(django.__file__)"
# Debe mostrar: /home/USUARIO/.virtualenvs/venv/lib/...

# --- PASO 4: Limpiar pip cache (~60 MB) ---
echo "=== LIMPIANDO PIP CACHE ==="
rm -rf ~/.cache/pip
pip cache purge 2>/dev/null

# --- PASO 5: Limpiar paquetes huérfanos de .local (~130 MB) ---
echo "=== LIMPIANDO .local/lib (paquetes fuera del venv) ==="
rm -rf ~/.local/lib
rm -rf ~/.local/share/virtualenv

# --- PASO 6: Limpiar cachés del sistema ---
echo "=== LIMPIANDO CACHES ==="
rm -rf ~/.cache/matplotlib
rm -rf ~/.cache/jedi

# --- PASO 7: Limpiar archivos innecesarios del proyecto ---
echo "=== LIMPIANDO ARCHIVOS DEL PROYECTO ==="
cd ~/proyectoafmgde

# Documentos Word e imágenes (no afectan la app)
rm -f *.docx *.png

# Copias de la base de datos (solo conservar db.sqlite3)
rm -f "db - copia"*.sqlite3 db.sqlite3_copia db_copia_*.sqlite3

# Scripts auxiliares de desarrollo
rm -f extraer.py limpiar.py seed_*.py probar_login_agq*.py

# Archivos .pyc y __pycache__ (se regeneran solos)
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Archivos temporales
rm -rf tmp/* tmp_pdf_preview/*

# --- PASO 8: Verificar resultado ---
echo "=== RESULTADO FINAL ==="
du -sh ~/.virtualenvs/* ~/proyectoafmgde/ ~/.cache/ ~/.local/ 2>/dev/null
