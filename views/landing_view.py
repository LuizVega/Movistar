"""
views/landing_view.py - Pantalla Inicial Minimalista Estilo Apple (Movistar Perú)
Presenta una interfaz limpia con dos botones centrales ('Cliente' y 'Trabajador')
para una selección de perfil rápida, elegante y sin fricciones.
"""

import streamlit as st


def render_landing_view():
    """Renderiza la pantalla principal minimalista estilo Apple con dos botones centrales."""
    
    # Inyectar estilos minimalistas Apple
    st.markdown("""
    <style>
        .landing-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 75vh;
            text-align: center;
            padding: 20px;
        }
        .apple-logo-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 72px;
            height: 72px;
            border-radius: 20px;
            background: linear-gradient(135deg, #019df4 0%, #00639c 100%);
            color: white;
            font-size: 38px;
            font-weight: 900;
            margin-bottom: 24px;
            box-shadow: 0 12px 30px rgba(1, 157, 244, 0.25);
        }
        .apple-hero-title {
            font-size: 40px;
            font-weight: 800;
            color: #1d1d1f;
            letter-spacing: -0.03em;
            line-height: 1.15;
            margin-bottom: 10px;
        }
        .apple-hero-subtitle {
            font-size: 18px;
            font-weight: 400;
            color: #86868b;
            margin-bottom: 48px;
            max-width: 500px;
            line-height: 1.5;
        }
        .apple-card {
            background: #ffffff;
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 24px;
            padding: 32px 28px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            text-align: center;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .apple-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08);
            border-color: rgba(1, 157, 244, 0.3);
        }
        .card-icon-circle {
            width: 56px;
            height: 56px;
            border-radius: 16px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            margin-bottom: 16px;
        }
        .card-title {
            font-size: 22px;
            font-weight: 700;
            color: #1d1d1f;
            margin-bottom: 8px;
        }
        .card-desc {
            font-size: 14px;
            color: #86868b;
            line-height: 1.5;
            margin-bottom: 24px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="landing-container">
        <div class="apple-logo-badge">M</div>
        <h1 class="apple-hero-title">Yara AI · Movistar Perú</h1>
        <p class="apple-hero-subtitle">Copiloto Inteligente de Facturación y Plataforma CRM. Selecciona tu modo de acceso para continuar.</p>
    </div>
    """, unsafe_allow_html=True)

    # Dos Botones / Tarjetas Centrales
    col_left, col_btn1, col_space, col_btn2, col_right = st.columns([1.5, 3.5, 0.5, 3.5, 1.5])

    with col_btn1:
        st.markdown("""
        <div class="apple-card">
            <div>
                <div class="card-icon-circle" style="background: #e8f4fd; color: #019df4;">💬</div>
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
        st.markdown("""
        <div class="apple-card">
            <div>
                <div class="card-icon-circle" style="background: #eaf8ea; color: #5cb615;">👔</div>
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
