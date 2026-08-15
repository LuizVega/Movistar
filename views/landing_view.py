"""
views/landing_view.py - Pantalla Inicial Minimalista Estilo Apple (Movistar Perú)
Presenta una interfaz limpia con dos botones centrales ('Cliente' y 'Trabajador')
y soporte para Modo Claro y Modo Oscuro.
"""

import streamlit as st
from components.chat_elements import get_theme_colors


def render_landing_view():
    """Renderiza la pantalla principal minimalista estilo Apple con dos botones centrales."""
    theme = get_theme_colors()
    is_dark = st.session_state.get("theme_mode", "light") == "dark"

    # Botón sutil en la esquina superior derecha para alternar tema
    col_t1, col_t2 = st.columns([6.5, 0.5])
    with col_t2:
        theme_icon = "🌙" if not is_dark else "☀️"
        if st.button(theme_icon, key="btn_toggle_theme_landing", help="Modo Claro / Oscuro"):
            st.session_state.theme_mode = "dark" if not is_dark else "light"
            st.rerun()

    # Inyectar estilos minimalistas Apple
    st.markdown(f"""
    <style>
        .landing-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 65vh;
            text-align: center;
            padding: 10px;
        }}
        .apple-logo-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 68px;
            height: 68px;
            border-radius: 20px;
            background: linear-gradient(135deg, #019df4 0%, #00639c 100%);
            color: white;
            font-size: 36px;
            font-weight: 900;
            margin-bottom: 20px;
            box-shadow: 0 10px 25px rgba(1, 157, 244, 0.25);
        }}
        .apple-hero-title {{
            font-size: 38px;
            font-weight: 800;
            color: {theme['text_primary']};
            letter-spacing: -0.03em;
            line-height: 1.15;
            margin-bottom: 8px;
        }}
        .apple-hero-subtitle {{
            font-size: 17px;
            font-weight: 400;
            color: {theme['text_secondary']};
            margin-bottom: 40px;
            max-width: 500px;
            line-height: 1.5;
        }}
        .apple-card {{
            background: {theme['bg_card']};
            border: 1px solid {theme['border']};
            border-radius: 24px;
            padding: 30px 26px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
            text-align: center;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .card-icon-circle {{
            width: 52px;
            height: 52px;
            border-radius: 16px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            margin-bottom: 14px;
        }}
        .card-title {{
            font-size: 21px;
            font-weight: 700;
            color: {theme['text_primary']};
            margin-bottom: 6px;
        }}
        .card-desc {{
            font-size: 13.5px;
            color: {theme['text_secondary']};
            line-height: 1.45;
            margin-bottom: 20px;
        }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="landing-container">
        <div class="apple-logo-badge">M</div>
        <h1 class="apple-hero-title">Yara AI · Movistar Perú</h1>
        <p class="apple-hero-subtitle">Copiloto Inteligente de Facturación y Plataforma CRM. Selecciona tu perfil de acceso para comenzar.</p>
    </div>
    """, unsafe_allow_html=True)

    # Dos Botones / Tarjetas Centrales
    col_left, col_btn1, col_space, col_btn2, col_right = st.columns([1.5, 3.5, 0.5, 3.5, 1.5])

    with col_btn1:
        st.markdown(f"""
        <div class="apple-card">
            <div>
                <div class="card-icon-circle" style="background: rgba(1, 157, 244, 0.12); color: #019df4;">💬</div>
                <div class="card-title">Cliente</div>
                <div class="card-desc">Accede al chat directo con Yara AI para consultar tu recibo, desgloses y soluciones de facturación.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if st.button("👤 Ingresar como Cliente", key="btn_enter_client", type="primary", use_container_width=True):
            st.session_state.view_mode = "cliente"
            st.session_state.user_role = "cliente"
            st.rerun()

    with col_btn2:
        st.markdown(f"""
        <div class="apple-card">
            <div>
                <div class="card-icon-circle" style="background: rgba(92, 182, 21, 0.12); color: #5cb615;">👔</div>
                <div class="card-title">Trabajador</div>
                <div class="card-desc">Bandeja de atención CRM en tiempo real, gestión de casos derivados por la IA y resolución de reclamos.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if st.button("👔 Ingresar como Trabajador", key="btn_enter_worker", type="secondary", use_container_width=True):
            st.session_state.view_mode = "trabajador"
            st.session_state.user_role = "trabajador"
            st.rerun()
