"""
views/cliente_view.py - Vista Interactiva del Modo Cliente
Incluye selector de cliente por DNI/Teléfono, KPIs de facturación, desglose diff_engine,
módulo comercial interactivo (fraccionamiento vs. Movistar Total) y chat conversacional agéntico.
"""

import streamlit as st
from state_manager import (
    CLIENTES_CATALOGO,
    add_chat_message,
    escalate_case_to_human,
    get_active_client_data
)
from services.agent_service import consultar_recibo, evaluar_upgrade_movistar_total, process_user_message


def render_cliente_view():
    # 1. Selector Inicial de Cliente por DNI / Teléfono / Nombre
    st.markdown("### 👤 Portal de Autoservicio y Facturación")
    
    opciones_display = {
        cid: f"{data['nombre']} (ID: {cid} | Tel: {data['telefono']} | DNI: 4789{cid[-4:]})"
        for cid, data in CLIENTES_CATALOGO.items()
    }

    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        current_id = st.session_state.get("active_client_id", "CLI001")
        idx_default = list(opciones_display.keys()).index(current_id) if current_id in opciones_display else 0
        
        selected_id = st.selectbox(
            "Seleccionar Cliente Activo (Buscar por Nombre / DNI / Teléfono):",
            options=list(opciones_display.keys()),
            format_func=lambda x: opciones_display[x],
            index=idx_default,
            key="select_cliente_view_box"
        )

        if selected_id != st.session_state.active_client_id:
            st.session_state.active_client_id = selected_id
            st.rerun()

    with col_sel2:
        st.write("")
        st.write("")
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.rerun()

    cliente = get_active_client_data()
    cid = cliente["id"]
    periodo = cliente["periodo"]

    # Ejecutar herramientas del servicio agéntico
    recibo_info = consultar_recibo(cid, periodo)
    nbo_info = evaluar_upgrade_movistar_total(cid)

    # 2. Header Corporativo de Cliente
    st.markdown(f"""
    <div class="movistar-header">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
            <div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 26px; font-weight: 800;">Hola, {cliente['nombre']}</span>
                    <span class="badge-green">● {cliente['estado_linea']}</span>
                </div>
                <div style="font-size: 13px; color: #cbd5e1; margin-top: 4px;">
                    Servicio: <strong>{cliente['servicio']}</strong> | Teléfono: <strong>{cliente['telefono']}</strong> | ID: <code style="color: #ff6a00;">{cid}</code>
                </div>
            </div>
            <div style="background: rgba(255,255,255,0.12); padding: 10px 18px; border-radius: 12px; text-align: right; border: 1px solid rgba(255,255,255,0.2);">
                <div style="font-size: 11px; color: #cbd5e1; text-transform: uppercase; font-weight: 600;">Total a Pagar (Julio 2026)</div>
                <div style="font-size: 24px; font-weight: 900; color: #ffffff;">S/ {cliente['recibo_actual']:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. KPIs Financieros
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #005cff;">
            <div style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase;">Recibo Actual</div>
            <div style="font-size: 22px; font-weight: 800; color: #0a2540; margin: 4px 0;">S/ {cliente['recibo_actual']:.2f}</div>
            <div style="font-size: 11px; color: #64748b;">Periodo: {periodo}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col2:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase;">Recibo Anterior</div>
            <div style="font-size: 22px; font-weight: 800; color: #334155; margin: 4px 0;">S/ {cliente['recibo_anterior']:.2f}</div>
            <div style="font-size: 11px; color: #64748b;">Periodo: 2026-06</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col3:
        var = recibo_info.get("variacion", {}) or {"monto": 0.0, "porcentaje": 0.0}
        monto_var = var.get("monto", 0.0)
        pct_var = var.get("porcentaje", 0.0)
        signo = "+" if monto_var > 0 else ""
        color_var = "#ff6a00" if monto_var > 0 else "#00a650"
        
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {color_var};">
            <div style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase;">Variación Auditada</div>
            <div style="font-size: 22px; font-weight: 800; color: {color_var}; margin: 4px 0;">
                {signo}S/ {monto_var:.2f} <span style="font-size: 12px; background: #fff3eb; padding: 2px 6px; border-radius: 8px;">{signo}{pct_var:.2f}%</span>
            </div>
            <div style="font-size: 11px; color: #64748b;">Motor: diff_engine.py</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col4:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase;">Estado de Cobranza</div>
            <div style="font-size: 20px; font-weight: 800; color: #00a650; margin: 4px 0;">Al Día</div>
            <div style="font-size: 11px; color: #00a650; font-weight: 600;">✓ Sin bloqueo ni morosidad</div>
        </div>
        """, unsafe_allow_html=True)

    # 4. Auditoría Explicativa
    with st.expander("🔍 **Auditoría de Conceptos y Causas de Variación (AI Telco)**", expanded=True):
        conceptos = recibo_info.get("conceptos_adicionales", [])
        if not conceptos:
            st.info("✅ **Facturación Regular**: No se registraron cobros extraordinarios ni variaciones en este ciclo.")
        else:
            st.markdown(f"**Conceptos detectados en el ciclo de {periodo}:**")
            for c in conceptos:
                tipo_badge = f"<span class='badge-orange'>{c.get('tipo', 'cargo_adicional')}</span>"
                st.markdown(f"""
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #0a2540; font-size: 14px;">{c.get('concepto')}</strong>
                        <div style="margin-top: 4px;">{tipo_badge}</div>
                    </div>
                    <div style="font-size: 16px; font-weight: 800; color: #ff6a00;">
                        +S/ {c.get('monto', 0.0):.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # 5. Módulo Comercial (Fraccionamiento vs. Movistar Total)
    st.markdown("### 💡 Soluciones Comerciales y Beneficios Disponibles")
    tab1, tab2 = st.tabs(["💳 **Opción A: Fraccionamiento de Deuda (0% Intereses)**", "🚀 **Opción B: Upgrade a Movistar Total (Ahorro 50%)**"])

    with tab1:
        st.markdown("#### Plan de Alivio Financiero sin Intereses")
        st.write("Difiere el pago de tu recibo actual en cuotas mensuales directas (TCEA 0.0%):")
        
        col_c1, col_c2, col_c3 = st.columns(3)
        total_recibo = cliente["recibo_actual"]

        with col_c1:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center; border: 2px solid #005cff; background: #f0f7ff;">
                <span class="badge-blue">3 Meses</span>
                <div style="font-size: 22px; font-weight: 900; color: #0a2540; margin-top: 8px;">S/ {(total_recibo/3):.2f} / mes</div>
                <div style="font-size: 11px; color: #64748b;">3 cuotas fijas (0% Int.)</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Solicitar 3 Cuotas", key="btn_3c_view", use_container_width=True):
                st.success(f"🎉 ¡Fraccionamiento aprobado! Pagarás 3 cuotas fijas de S/ {(total_recibo/3):.2f} a partir de Agosto 2026.")

        with col_c2:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <span class="badge-blue">6 Meses</span>
                <div style="font-size: 22px; font-weight: 900; color: #0a2540; margin-top: 8px;">S/ {(total_recibo/6):.2f} / mes</div>
                <div style="font-size: 11px; color: #64748b;">6 cuotas fijas (0% Int.)</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Solicitar 6 Cuotas", key="btn_6c_view", use_container_width=True):
                st.success(f"🎉 ¡Fraccionamiento aprobado! Pagarás 6 cuotas fijas de S/ {(total_recibo/6):.2f} a partir de Agosto 2026.")

        with col_c3:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <span class="badge-blue">12 Meses</span>
                <div style="font-size: 22px; font-weight: 900; color: #0a2540; margin-top: 8px;">S/ {(total_recibo/12):.2f} / mes</div>
                <div style="font-size: 11px; color: #64748b;">12 cuotas fijas (0% Int.)</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Solicitar 12 Cuotas", key="btn_12c_view", use_container_width=True):
                st.success(f"🎉 ¡Fraccionamiento aprobado! Pagarás 12 cuotas fijas de S/ {(total_recibo/12):.2f} a partir de Agosto 2026.")

    with tab2:
        if nbo_info.get("encontrado") and nbo_info.get("es_elegible_mt"):
            of = nbo_info["oferta_recomendada"]
            ben = nbo_info["beneficio_economico"]

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0a2540 0%, #0d3b66 60%, #ff6a00 100%); border-radius: 16px; padding: 20px; color: white; margin-bottom: 16px;">
                <span class="badge-orange" style="background: #ff6a00; color: white; border: none;">⭐ RECOMENDACIÓN ÓPTIMA NBO</span>
                <h3 style="color: white; margin-top: 8px; font-size: 22px; font-weight: 800;">{of.get('nombre_oferta')}</h3>
                <p style="font-size: 13px; color: #cbd5e1;">{of.get('descripcion')}</p>
                <div style="display: flex; gap: 20px; margin-top: 12px; flex-wrap: wrap;">
                    <div style="background: rgba(255,255,255,0.12); padding: 8px 16px; border-radius: 10px;">
                        <span style="font-size: 11px; color: #cbd5e1;">Velocidad Fibra</span>
                        <div style="font-size: 18px; font-weight: 800;">{of.get('velocidad_mbps')} Mbps</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.12); padding: 8px 16px; border-radius: 10px;">
                        <span style="font-size: 11px; color: #cbd5e1;">Gigas Móviles</span>
                        <div style="font-size: 18px; font-weight: 800;">{of.get('gigas_datos')} GB Full</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.12); padding: 8px 16px; border-radius: 10px;">
                        <span style="font-size: 11px; color: #cbd5e1;">Ahorro Mensual</span>
                        <div style="font-size: 18px; font-weight: 800; color: #ffeb3b;">S/ {ben.get('ahorro_mensual_soles'):.2f} ({ben.get('ahorro_porcentaje'):.1f}%)</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.12); padding: 8px 16px; border-radius: 10px;">
                        <span style="font-size: 11px; color: #cbd5e1;">Precio Promocional</span>
                        <div style="font-size: 18px; font-weight: 900; color: #ffffff;">S/ {of.get('precio_promocional'):.2f} / mes</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_b1, col_b2 = st.columns([3, 1])
            with col_b1:
                st.markdown(f"**Canal de contacto sugerido:** `{nbo_info.get('canal_mas_usado')}` | **Ahorro Anual Estimado:** `S/ {ben.get('ahorro_anual_estimado_soles'):.2f}`")
            with col_b2:
                if st.button("🚀 Migrar a Movistar Total", type="primary", key="btn_mt_migracion_view", use_container_width=True):
                    st.balloons()
                    st.success(f"🎉 ¡Solicitud enviada para {of.get('nombre_oferta')}! Te contactaremos al canal {nbo_info.get('canal_mas_usado')}.")
        else:
            st.info("ℹ️ Tu plan actual se encuentra optimizado o ya cuentas con el beneficio convergente Movistar Total.")

    st.markdown("---")

    # 6. Chat Conversacional Agéntico y Botón de Acción Rápida (Asesor Humano)
    st.markdown("### 💬 Asistente Digital Movistar (Chat en Vivo)")
    
    col_chat_title, col_human_btn = st.columns([2.5, 1.5])
    with col_chat_title:
        st.caption("Pregúntame sobre el desglose de tu recibo, motivos de cobro o solicita un asesor humano.")
    with col_human_btn:
        if st.button("🚨 Hablar con un asesor humano", key="btn_hablar_asesor_humano", type="secondary", use_container_width=True):
            ticket_id = escalate_case_to_human(
                client_id=cid,
                client_name=cliente["nombre"],
                reason=f"Cliente solicita atención humana directa para revisión de su recibo {periodo}."
            )
            add_chat_message("assistant", f"🔔 **He transferido tu caso a un asesor humano.** Tu ticket de atención es **`{ticket_id}`**.")
            st.warning(f"¡Caso derivado con éxito! Se generó el ticket **{ticket_id}** en la cola de atención CRM.")

    # Renderizar historial de mensajes
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Entrada de texto del usuario
    if prompt := st.chat_input("Escribe tu consulta aquí (ej: ¿Por qué subió mi recibo? / Quiero Movistar Total)..."):
        # 1. Guardar y mostrar mensaje del usuario
        add_chat_message("user", prompt)
        
        # 2. Procesar con el motor agéntico (Tool Calling & 0% Alucinaciones)
        respuesta_bot = process_user_message(client_id=cid, user_query=prompt)
        add_chat_message("assistant", respuesta_bot)
        st.rerun()
