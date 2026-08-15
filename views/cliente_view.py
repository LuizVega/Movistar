"""
views/cliente_view.py - Vista Modo Cliente con Chat Puro (Diseño Minimalista Apple + Movistar)
Permite selección de perfil de cliente, modo claro/oscuro y chat interactivo fluido con Yara AI.
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
    YARA_AVATAR_URL,
    get_theme_colors
)


def render_cliente_view():
    """Renderiza la vista pura de chat con estilo minimalista Apple, selector de usuario y modo claro/oscuro."""
    theme = get_theme_colors()
    is_dark = st.session_state.get("theme_mode", "light") == "dark"

    # 1. Barra de Navegación Superior
    col_nav_left, col_nav_user, col_nav_right = st.columns([1.8, 3.2, 2.0])

    with col_nav_left:
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("👔 Asesor", key="btn_to_worker_top", use_container_width=True):
                st.session_state.view_mode = "trabajador"
                st.session_state.user_role = "trabajador"
                st.rerun()
        with btn_c2:
            if st.button("🏠 Inicio", key="btn_to_home_top", use_container_width=True):
                st.session_state.view_mode = "landing"
                st.rerun()

    # Selector de Cliente / Perfil Activo
    with col_nav_user:
        opciones_usuarios = {
            cid: f"{data['nombre']} ({cid} - {data['servicio']})"
            for cid, data in CLIENTES_CATALOGO.items()
        }
        current_id = st.session_state.get("active_client_id", "CLI001")
        idx_cur = list(opciones_usuarios.keys()).index(current_id) if current_id in opciones_usuarios else 0

        selected_user = st.selectbox(
            "👤 Usuario Activo:",
            options=list(opciones_usuarios.keys()),
            format_func=lambda x: opciones_usuarios[x],
            index=idx_cur,
            key="sel_active_client_dropdown",
            label_visibility="collapsed"
        )
        if selected_user != st.session_state.active_client_id:
            st.session_state.active_client_id = selected_user
            reset_chat()
            st.rerun()

    with col_nav_right:
        col_th, col_nc = st.columns([1.0, 1.4])
        with col_th:
            theme_label = "🌙" if not is_dark else "☀️"
            if st.button(theme_label, key="btn_toggle_theme_client", help="Alternar Modo Claro / Oscuro", use_container_width=True):
                st.session_state.theme_mode = "dark" if not is_dark else "light"
                st.rerun()
        with col_nc:
            if st.button("➕ Nuevo", key="btn_new_chat_top", type="secondary", use_container_width=True):
                reset_chat()
                st.rerun()

    # Expander sutil para configuración opcional de API Key de Gemini
    with st.expander("⚙️ Configuración de IA (Opcional - Google Gemini Live)", expanded=False):
        st.caption("Por defecto, Yara AI opera con su motor semántico neuronal determinista (0% alucinaciones). Puedes conectar tu API Key de Gemini:")
        custom_key = st.text_input(
            "Google Gemini API Key:",
            value=st.session_state.get("gemini_api_key", ""),
            type="password",
            placeholder="Pega aquí tu API Key de Gemini...",
            key="input_custom_gemini_key"
        )
        if custom_key != st.session_state.get("gemini_api_key"):
            st.session_state.gemini_api_key = custom_key.strip()
            st.success("API Key guardada para esta sesión.")

    # 2. Canvas Central de Chat
    cliente = get_active_client_data()

    # Barra de razonamiento de Yara AI (Consultar -> Comprender -> Explicar)
    render_analysis_markers()

    # Renderizado de Mensajes con estilo exacto de la captura
    for msg_idx, msg in enumerate(st.session_state.chat_history):
        role = msg.get("role", "assistant")
        content = msg.get("content", "")

        if role == "user":
            # Burbuja de Usuario (Estilo captura: azul Movistar #00639c, borde redondeado, alineada a la derecha)
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; margin-bottom: 14px;">
                <div style="background: #00639c; color: #ffffff; border-radius: 18px 18px 2px 18px; padding: 12px 20px; font-size: 15px; font-weight: 500; max-width: 80%; box-shadow: 0 2px 8px rgba(0,99,156,0.18); line-height: 1.45;">
                    {content}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Burbuja de Asistente (Estilo captura: avatar circular a la izquierda + caja blanca/gris con borde sutil)
            st.markdown(f"""
            <div style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 14px;">
                <img src="{YARA_AVATAR_URL}" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover; margin-top: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.1);" alt="Yara AI"/>
                <div style="background: {theme['bg_card']}; color: {theme['text_primary']}; border: 1px solid {theme['border']}; border-radius: 18px 18px 18px 2px; padding: 14px 20px; font-size: 15px; line-height: 1.5; max-width: 85%; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
                    {content}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Elementos de acción interactiva si existen en la respuesta
            render_chat_action_elements(msg, msg_idx, cliente)

    # 3. Input de Chat Fijo en la parte inferior
    if prompt := st.chat_input("Escribe tu consulta aquí (ej: '¿por qué subió mi recibo?', 'quiero cambiar de plan')..."):
        # 1. Guardar mensaje del usuario
        add_chat_message("user", prompt)
        
        # 2. Consultar al motor Gemini / Yara AI
        gemini_res = get_gemini_response(
            chat_history=st.session_state.chat_history,
            user_message=prompt,
            client_context=cliente,
            api_key_override=st.session_state.get("gemini_api_key")
        )
        
        # 3. Guardar respuesta del asistente
        add_chat_message(
            role="assistant",
            content=gemini_res["response_text"],
            metadata={"action_payload": gemini_res.get("action_payload")}
        )
        st.rerun()
