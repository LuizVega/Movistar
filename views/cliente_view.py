"""
views/cliente_view.py - Vista Modo Cliente con Chat Puro (Diseño Minimalista Apple + Movistar)
Permite selección de perfil de cliente, modo claro/oscuro y chat interactivo fluido con Yara AI.
"""

import streamlit as st
from state_manager import (
    CLIENTES_CATALOGO,
    add_chat_message,
    reset_chat,
    switch_active_client,
    get_active_client_data
)
from services.gemini_service import get_gemini_response
from components.chat_elements import (
    render_analysis_markers,
    render_chat_action_elements,
    format_text_to_html,
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

    # Selector de Cliente / Perfil Activo con Memoria Conversacional Persistente
    with col_nav_user:
        opciones_usuarios = {
            cid: f"{data['nombre']} ({cid} - {data.get('escenario_tag', data.get('servicio'))})"
            for cid, data in CLIENTES_CATALOGO.items()
        }
        current_id = st.session_state.get("active_client_id", "CLI004")
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
            switch_active_client(selected_user)
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

    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

    # 2. Canvas Central de Chat
    cliente = get_active_client_data()
    nombre_pila = cliente.get("nombre", "Cliente").split()[0]
    mod_fac = cliente.get("modalidad_facturacion", "Renta Adelantada")
    prod_b2c = cliente.get("tipo_producto_b2c", cliente.get("servicio", "B2C"))
    esc_tag = cliente.get("escenario_tag", "Facturación")

    # Banner informativo de Demostración Hackathon
    badge_mod_bg = "#e0f2fe" if mod_fac == "Renta Adelantada" else "#fef3c7"
    badge_mod_fg = "#0284c7" if mod_fac == "Renta Adelantada" else "#b45309"

    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; background: {theme['bg_card_header']}; border: 1px solid {theme['border']}; border-radius: 12px; padding: 6px 14px; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: {theme['text_primary']};">
            <span style="font-weight: 700;">🎯 Demo:</span>
            <span style="background: {badge_mod_bg}; color: {badge_mod_fg}; font-weight: 700; padding: 2px 8px; border-radius: 6px; font-size: 11px;">{mod_fac}</span>
            <span style="font-weight: 600; color: {theme['text_secondary']};">| {prod_b2c}</span>
        </div>
        <span style="background: #eef2ff; color: #4338ca; font-weight: 700; font-size: 11px; padding: 2px 8px; border-radius: 6px;">
            {esc_tag}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Barra de razonamiento de Yara AI (Consultar -> Comprender -> Explicar)
    render_analysis_markers()

    # Si el chat está vacío al inicio, mostrar mensaje de bienvenida limpio estilo Apple y mini-dashboard
    if not st.session_state.chat_history:
        st.markdown(f"""
        <div style="text-align: center; margin: 20px auto 10px auto; max-width: 480px; padding: 6px 20px;">
            <img src="{YARA_AVATAR_URL}" style="width: 52px; height: 52px; border-radius: 50%; object-fit: cover; margin-bottom: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);" alt="Yara AI"/>
            <h3 style="margin: 0 0 4px 0; font-size: 21px; font-weight: 700; color: {theme['text_primary']};">¡Hola {nombre_pila}! Soy Yara AI</h3>
            <p style="font-size: 13px; color: {theme['text_secondary']}; line-height: 1.4; margin: 0 0 10px 0;">
                Tu copiloto de facturación. Aquí tienes el estado actual de tu cuenta:
            </p>
        </div>
        """, unsafe_allow_html=True)
        from components.chat_elements import render_client_dashboard_card
        render_client_dashboard_card(cliente)




    # Renderizado de Mensajes con estilo exacto de la captura
    for msg_idx, msg in enumerate(st.session_state.chat_history):
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        formatted_html = format_text_to_html(content)

        if role == "user":
            # Burbuja de Usuario (Azul Movistar #00639c, redondeado, alineado a la derecha)
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; margin-bottom: 14px;">
                <div style="background: #00639c; color: #ffffff; border-radius: 18px 18px 2px 18px; padding: 12px 20px; font-size: 15px; font-weight: 500; max-width: 80%; box-shadow: 0 2px 8px rgba(0,99,156,0.18); line-height: 1.45;">
                    {formatted_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Burbuja de Asistente (Avatar circular + caja limpia con negritas renderizadas correctamente)
            st.markdown(f"""
            <div style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 14px;">
                <img src="{YARA_AVATAR_URL}" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover; margin-top: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.1);" alt="Yara AI"/>
                <div style="background: {theme['bg_card']}; color: {theme['text_primary']}; border: 1px solid {theme['border']}; border-radius: 18px 18px 18px 2px; padding: 14px 20px; font-size: 15px; line-height: 1.55; max-width: 85%; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
                    {formatted_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Elementos de acción interactiva si el agente los recomendó
            render_chat_action_elements(msg, msg_idx, cliente)

    # 3. Input de Chat Fijo en la parte inferior
    if prompt := st.chat_input("Escribe tu consulta aquí (ej: '¿por qué subió mi recibo?', 'quiero cambiar de plan')..."):
        # 1. Guardar mensaje del usuario
        add_chat_message("user", prompt)
        
        # 2. Consultar al motor Gemini / Yara AI
        gemini_res = get_gemini_response(
            chat_history=st.session_state.chat_history,
            user_message=prompt,
            client_context=cliente
        )
        
        # 3. Guardar respuesta del asistente
        add_chat_message(
            role="assistant",
            content=gemini_res["response_text"],
            metadata={"action_payload": gemini_res.get("action_payload")}
        )
        st.rerun()
