"""
views/cliente_view.py - Vista Modo Cliente con Chat Puro (Diseño Oficial Stitch)
Enfocada 100% en la experiencia conversacional limpia con Yara AI.
Incluye botón superior izquierdo para cambio fluido de vista y botón 'Nuevo Chat'.
"""

import streamlit as st
from state_manager import (
    CLIENTES_CATALOGO,
    add_chat_message,
    reset_chat,
    get_active_client_data
)
from services.gemini_service import get_gemini_response
from components.chat_elements import (
    render_analysis_markers,
    render_chat_action_elements,
    YARA_AVATAR_URL
)


def render_cliente_view():
    """Renderiza la vista pura de chat para el cliente con diseño Stitch."""
    
    # 1. Barra de Navegación Superior: Botón de cambio de vista arriba a la izquierda y 'Nuevo Chat' a la derecha
    col_nav_left, col_nav_center, col_nav_right = st.columns([2.5, 3.5, 2.0])

    with col_nav_left:
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("👔 Trabajador", key="btn_switch_to_worker_top", use_container_width=True):
                st.session_state.view_mode = "trabajador"
                st.session_state.user_role = "trabajador"
                st.rerun()
        with c_btn2:
            if st.button("🏠 Inicio", key="btn_switch_to_landing_top_client", use_container_width=True):
                st.session_state.view_mode = "landing"
                st.rerun()

    with col_nav_center:
        st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 10px; padding-top: 4px;">
            <img src="{YARA_AVATAR_URL}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;" alt="Yara AI"/>
            <span style="font-size: 17px; font-weight: 800; color: #00639c;">Yara AI</span>
            <span style="font-size: 12px; color: #6f7883; font-weight: 600;">| Copiloto de Facturación</span>
        </div>
        """, unsafe_allow_html=True)

    with col_nav_right:
        if st.button("➕ Nuevo Chat", key="btn_new_chat_client", type="secondary", use_container_width=True):
            reset_chat()
            st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # 2. Canvas de Chat Centrado (Estilo Stitch)
    cliente = get_active_client_data()

    # Marcadores de análisis de Yara AI (Consultar -> Comprender -> Explicar)
    render_analysis_markers()

    # Contenedor de Mensajes
    for msg_idx, msg in enumerate(st.session_state.chat_history):
        role = msg.get("role", "assistant")
        
        if role == "user":
            with st.chat_message("user"):
                st.markdown(f"""
                <div style="background: #00639c; color: #ffffff; border-radius: 16px 16px 2px 16px; padding: 12px 18px; font-size: 15px; font-weight: 500; display: inline-block; max-width: 85%; box-shadow: 0 2px 6px rgba(0,99,156,0.15);">
                    {msg["content"]}
                </div>
                """, unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar=YARA_AVATAR_URL):
                st.markdown(f"""
                <div style="background: #f5f3f3; color: #1b1c1c; border-radius: 16px 16px 16px 2px; padding: 14px 18px; font-size: 15px; line-height: 1.5; border: 1px solid #bec7d3; max-width: 85%; box-shadow: 0 1px 4px rgba(0,0,0,0.03);">
                    {msg["content"]}
                </div>
                """, unsafe_allow_html=True)
                # Renderizar Bento Card y Botones Interactivos
                render_chat_action_elements(msg, msg_idx, cliente)

    # 3. Entrada de Chat (Fixed Bottom)
    if prompt := st.chat_input("Escribe un mensaje o pregunta sobre tu recibo (ej: '¿por qué subió mi recibo?', 'quiero fraccionar')..."):
        # 1. Guardar mensaje del usuario
        add_chat_message("user", prompt)
        
        # 2. Procesar con el cliente Gemini / Yara AI
        gemini_res = get_gemini_response(
            chat_history=st.session_state.chat_history,
            user_message=prompt,
            client_context=cliente
        )
        
        # 3. Guardar respuesta del asistente con metadata de acción interactiva
        add_chat_message(
            role="assistant",
            content=gemini_res["response_text"],
            metadata={"action_payload": gemini_res.get("action_payload")}
        )
        st.rerun()
