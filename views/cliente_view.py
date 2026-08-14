"""
views/cliente_view.py - Vista Modo Cliente con Diseño Oficial de Stitch (Yara AI Billing Copilot)
Incorpora la paleta de colores de Movistar (#00639c, #019df4, #5cb615, #faf9f9),
marcadores de análisis (Consultar -> Comprender -> Explicar), tarjeta Bento de desglose y chat interactivo.
"""

import streamlit as st
from state_manager import (
    CLIENTES_CATALOGO,
    add_chat_message,
    get_active_client_data
)
from services.agent_service import (
    consultar_recibo,
    evaluar_upgrade_movistar_total
)
from services.escalation_service import (
    escalar_a_humano,
    cliente_tiene_ticket_pendiente
)
from services.gemini_service import get_gemini_response
from components.chat_elements import (
    render_analysis_markers,
    render_chat_action_elements,
    YARA_AVATAR_URL
)


def render_cliente_view():
    # 1. Cabecera Oficial Stitch (Yara AI - Copiloto de Facturación)
    st.markdown(f"""
    <div style="background: #ffffff; border: 1px solid #bec7d3; border-radius: 16px; padding: 16px 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
        <div style="display: flex; align-items: center; gap: 14px;">
            <img src="{YARA_AVATAR_URL}" style="width: 46px; height: 46px; border-radius: 50%; object-fit: cover; box-shadow: 0 2px 6px rgba(0,0,0,0.15);" alt="Yara AI"/>
            <div>
                <div style="font-size: 22px; font-weight: 800; color: #00639c; line-height: 1.2;">Yara AI</div>
                <div style="font-size: 13px; font-weight: 700; color: #3f4852; text-transform: uppercase; letter-spacing: 0.05em;">Copiloto de Facturación · Movistar Perú</div>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="background: #e3e2e2; color: #1b1c1c; font-size: 12px; font-weight: 700; padding: 5px 12px; border-radius: 9999px;">
                💡 0% Alucinación
            </span>
            <span style="background: #8efd49; color: #092100; font-size: 12px; font-weight: 800; padding: 5px 12px; border-radius: 9999px;">
                ● Sistema Activo
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Selector de Cliente
    opciones_display = {
        cid: f"{data['nombre']} (ID: {cid} | Tel: {data['telefono']} | Plan: {data['servicio']})"
        for cid, data in CLIENTES_CATALOGO.items()
    }

    col_sel1, col_sel2 = st.columns([3.2, 0.8])
    with col_sel1:
        current_id = st.session_state.get("active_client_id", "CLI001")
        idx_default = list(opciones_display.keys()).index(current_id) if current_id in opciones_display else 0
        
        selected_id = st.selectbox(
            "Seleccionar Cuenta de Cliente:",
            options=list(opciones_display.keys()),
            format_func=lambda x: opciones_display[x],
            index=idx_default,
            key="select_cliente_stitch_box"
        )

        if selected_id != st.session_state.active_client_id:
            st.session_state.active_client_id = selected_id
            st.rerun()

    with col_sel2:
        st.write("")
        st.write("")
        if st.button("🔄 Actualizar", use_container_width=True):
            st.rerun()

    cliente = get_active_client_data()
    cid = cliente["id"]
    periodo = cliente["periodo"]

    # Alerta si hay ticket pendiente escalado
    ticket_activo = cliente_tiene_ticket_pendiente(cid)
    if ticket_activo:
        st.markdown(f"""
        <div style="background: #fff7ed; border-left: 5px solid #ff6a00; border-radius: 12px; padding: 12px 18px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="color: #9a3412;">🎫 CASO TRANSFERIDO A ASESOR HUMANO</strong>
                <div style="font-size: 13px; color: #c2410c; margin-top: 2px;">
                    Ticket: <strong><code>{ticket_activo['ticket_id']}</code></strong> · Estado: <strong>{ticket_activo['status']}</strong>
                </div>
            </div>
            <span style="background: #ff6a00; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 800;">EN ATENCIÓN</span>
        </div>
        """, unsafe_allow_html=True)

    # 3. KPIs Resumen de Cuenta
    recibo_info = consultar_recibo(cid, periodo)
    var = recibo_info.get("variacion", {}) or {"monto": 0.0, "porcentaje": 0.0}
    monto_var = var.get("monto", 0.0)
    pct_var = var.get("porcentaje", 0.0)
    signo = "+" if monto_var > 0 else ""
    color_var = "#ba1a1a" if monto_var > 0 else "#2f6c00"

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #bec7d3; border-radius: 12px; padding: 14px 18px; border-left: 4px solid #00639c;">
            <div style="font-size: 11px; font-weight: 700; color: #3f4852; text-transform: uppercase;">Total a Pagar (Julio)</div>
            <div style="font-size: 24px; font-weight: 800; color: #00639c; margin: 4px 0;">S/ {cliente['recibo_actual']:.2f}</div>
            <div style="font-size: 12px; color: #6f7883;">Servicio: {cliente['servicio']}</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #bec7d3; border-radius: 12px; padding: 14px 18px;">
            <div style="font-size: 11px; font-weight: 700; color: #3f4852; text-transform: uppercase;">Mes Anterior (Junio)</div>
            <div style="font-size: 24px; font-weight: 800; color: #1b1c1c; margin: 4px 0;">S/ {cliente['recibo_anterior']:.2f}</div>
            <div style="font-size: 12px; color: #6f7883;">Periodo 2026-06</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #bec7d3; border-radius: 12px; padding: 14px 18px; border-left: 4px solid {color_var};">
            <div style="font-size: 11px; font-weight: 700; color: #3f4852; text-transform: uppercase;">Variación Neta</div>
            <div style="font-size: 24px; font-weight: 800; color: {color_var}; margin: 4px 0;">{signo}S/ {monto_var:.2f} <span style="font-size: 13px; font-weight: 600;">({signo}{pct_var:.1f}%)</span></div>
            <div style="font-size: 12px; color: #6f7883;">Auditado por Yara AI</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 4. Canvas Conversacional de Yara AI
    st.markdown("### 💬 Conversación con Yara AI")
    
    # Barra de marcadores de análisis (Stitch Design: Consultar -> Comprender -> Explicar)
    render_analysis_markers()

    # Renderizar historial de mensajes
    for msg_idx, msg in enumerate(st.session_state.chat_history):
        role = msg["role"]
        
        if role == "user":
            with st.chat_message("user"):
                st.markdown(f"""
                <div style="background: #00639c; color: #ffffff; border-radius: 16px 16px 2px 16px; padding: 12px 16px; font-size: 15px; font-weight: 500; display: inline-block;">
                    {msg["content"]}
                </div>
                """, unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar=YARA_AVATAR_URL):
                st.markdown(msg["content"])
                # Renderizar Bento Card y Botones Interactivos de Stitch
                render_chat_action_elements(msg, msg_idx, cliente)

    # Entrada de texto del usuario
    if prompt := st.chat_input("Escribe un mensaje o pregunta sobre tu recibo (ej: '¿por qué subió mi recibo?', 'quiero cambiar de plan')..."):
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
