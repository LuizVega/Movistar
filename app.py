"""
app.py - Portal Integrado Movistar (Asistente Digital & CRM)
Soporta ejecución dual directa con `streamlit run app.py` o `python app.py`.
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
    print("Iniciando Asistente Digital Movistar con Streamlit...")
    print("============================================================")
    try:
        # Ejecutar streamlit run app.py
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])
    except KeyboardInterrupt:
        print("\nAplicación detenida.")
    sys.exit(0)


# =========================================================
# LÓGICA PRINCIPAL DE STREAMLIT (CUANDO SE EJECUTA STREAMLIT)
# =========================================================

import streamlit as st
from state_manager import init_session_state, CLIENTES_CATALOGO
from views.cliente_view import render_cliente_view
from views.trabajador_view import render_trabajador_view

# 1. Configuración de página
st.set_page_config(
    page_title="Movistar | Asistente Digital & CRM",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inyectar estilos corporativos Movistar
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    :root {
        --movistar-navy: #0a2540;
        --movistar-blue: #005cff;
        --movistar-orange: #ff6a00;
        --movistar-green: #00a650;
    }

    .movistar-header {
        background: linear-gradient(135deg, #0a2540 0%, #0d3b66 60%, #005cff 100%);
        border-radius: 16px;
        padding: 24px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(10, 37, 64, 0.15);
    }

    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(10, 37, 64, 0.04);
        margin-bottom: 12px;
    }

    .badge-orange {
        background-color: #fff3eb;
        color: #ff6a00;
        border: 1px solid rgba(255, 106, 0, 0.3);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }

    .badge-blue {
        background-color: #e8f1ff;
        color: #005cff;
        border: 1px solid rgba(0, 92, 255, 0.3);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }

    .badge-green {
        background-color: #e6f7ee;
        color: #00a650;
        border: 1px solid rgba(0, 166, 80, 0.3);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
    }

    .badge-red {
        background-color: #fee2e2;
        color: #dc2626;
        border: 1px solid rgba(220, 38, 38, 0.3);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# 3. Inicializar estado global
init_session_state()

# 4. Barra Lateral (Sidebar)
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
        <div style="background-color: #005cff; color: white; width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 24px;">M</div>
        <div>
            <div style="font-weight: 800; font-size: 18px; color: #0a2540;">Movistar</div>
            <div style="font-size: 11px; color: #64748b; font-weight: 600;">PORTAL INTEGRADO</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔄 Selector de Perfil")
    
    rol_seleccionado = st.radio(
        label="Seleccione el modo de operación:",
        options=["👤 Modo Cliente", "👔 Modo Trabajador / Asesor"],
        index=0 if st.session_state.user_role == "cliente" else 1,
        key="radio_role_selector_main"
    )

    nuevo_rol = "cliente" if "Cliente" in rol_seleccionado else "trabajador"
    if st.session_state.user_role != nuevo_rol:
        st.session_state.user_role = nuevo_rol
        st.rerun()

    st.markdown("---")

    if st.session_state.user_role == "cliente":
        st.markdown("#### 🔍 Cliente Seleccionado")
        current_client = CLIENTES_CATALOGO.get(st.session_state.active_client_id, CLIENTES_CATALOGO["CLI001"])
        st.markdown(f"**Nombre:** {current_client['nombre']}")
        st.markdown(f"**ID:** `{current_client['id']}`")
        st.markdown(f"**Teléfono:** {current_client['telefono']}")
        st.markdown(f"**Plan:** {current_client['servicio']}")
        st.caption("ℹ️ Puedes cambiar de cliente en el selector superior de la vista principal.")
    else:
        st.markdown("#### 📊 Estado de la Cola CRM")
        tickets = st.session_state.get("escalated_tickets", [])
        pendientes = sum(1 for t in tickets if t["status"] == "PENDIENTE")
        en_atencion = sum(1 for t in tickets if t["status"] == "EN_ATENCION")
        resueltos = sum(1 for t in tickets if t["status"] == "RESUELTO")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pendientes", f"🚨 {pendientes}")
        with col2:
            st.metric("En Atención", f"⏳ {en_atencion}")
        st.metric("Resueltos", f"✅ {resueltos}")
        st.caption("📌 Casos transferidos desde el Asistente Digital con contexto completo.")

    st.markdown("---")
    st.markdown("<div style='font-size: 11px; color: #94a3b8; text-align: center;'>Hackathon AI Telecom Challenge<br>Movistar & U. de Lima · 2026</div>", unsafe_allow_html=True)

# 5. Enrutamiento de Vistas
if st.session_state.user_role == "cliente":
    render_cliente_view()
else:
    render_trabajador_view()
