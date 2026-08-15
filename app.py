"""
app.py - Portal Integrado Movistar (Yara AI & CRM)
Flujo Minimalista Estilo Apple:
1. Pantalla Inicial Landing con dos botones centrales ('Cliente' y 'Trabajador').
2. Modo Cliente: Chat puro estilo Stitch con botón de cambio arriba a la izquierda y 'Nuevo Chat'.
3. Modo Trabajador: Panel de control CRM optimizado con datos en tiempo real de la IA y transcripciones.
"""

import os
import sys
import subprocess


def is_running_in_streamlit() -> bool:
    """Detecta si el script se está ejecutando bajo el contexto de Streamlit."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


# Si se ejecuta directamente con 'python app.py', lanzar automáticamente el servidor Streamlit
if not is_running_in_streamlit() and __name__ == "__main__":
    print("============================================================")
    print("Iniciando Yara AI Movistar...")
    print("============================================================")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])
    except KeyboardInterrupt:
        print("\nAplicación detenida.")
    sys.exit(0)


# =========================================================
# LÓGICA PRINCIPAL DE STREAMLIT
# =========================================================

import streamlit as st
from state_manager import init_session_state, CLIENTES_CATALOGO
from views.landing_view import render_landing_view
from views.cliente_view import render_cliente_view
from views.trabajador_view import render_trabajador_view

# 1. Configuración de página minimalista
st.set_page_config(
    page_title="Yara AI · Movistar Perú",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Inyección de Estilos Globales (Apple Minimalist + Movistar Colors)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Ocultar barra lateral en modo landing para máxima limpieza */
    [data-testid="stSidebar"] {
        border-right: 1px solid #e2e8f0;
    }
    
    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# 3. Inicializar estado global
init_session_state()

# 4. Enrutamiento Principal de Vistas
view_mode = st.session_state.get("view_mode", "landing")

if view_mode == "landing":
    render_landing_view()
elif view_mode == "cliente":
    render_cliente_view()
elif view_mode == "trabajador":
    render_trabajador_view()
else:
    render_landing_view()
