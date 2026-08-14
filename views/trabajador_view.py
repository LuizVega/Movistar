"""
views/trabajador_view.py - Panel de Control del Empleado / Asesor CRM (Movistar)
Visualiza en tiempo real los clientes derivados por la IA, el resumen del motivo de escalamiento,
los datos de facturación del cliente y el historial completo de la conversación previa con el bot.
"""

import streamlit as st
from datetime import datetime
from state_manager import (
    CLIENTES_CATALOGO,
    update_ticket_status,
    add_chat_message
)
from diff_engine import auditar_variacion_recibo
from database import get_ficha_cliente_completa
from nbo_engine import generar_next_best_offer


def render_trabajador_view():
    # 1. Header Corporativo de Panel de Asesor
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0a2540 0%, #1e293b 100%); border-radius: 16px; padding: 20px 24px; color: white; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(10, 37, 64, 0.15);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <span class="badge-orange" style="background: #ff6a00; color: white; border: none;">PANEL DE GESTIÓN CRM · MOVISTAR PERÚ</span>
                <h2 style="color: white; font-weight: 800; font-size: 24px; margin-top: 6px; margin-bottom: 2px;">Bandeja de Atención al Cliente & Derivaciones</h2>
                <p style="color: #94a3b8; font-size: 13px; margin: 0;">Gestión de tickets escalados por el Asistente Digital con contexto completo y auditoría en tiempo real</p>
            </div>
            <div style="text-align: right; background: rgba(255,255,255,0.08); padding: 8px 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.15);">
                <div style="font-size: 11px; color: #cbd5e1; text-transform: uppercase; font-weight: 600;">Asesor Conectado</div>
                <div style="font-weight: 800; color: #ffffff; font-size: 14px;">Carlos Vega · Supervisor Senior</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tickets = st.session_state.get("escalated_tickets", [])
    total_tickets = len(tickets)
    pendientes = sum(1 for t in tickets if t["status"] == "PENDIENTE")
    en_atencion = sum(1 for t in tickets if t["status"] == "EN_ATENCION")
    resueltos = sum(1 for t in tickets if t["status"] == "RESUELTO")

    # 2. Métricas Superiores
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric("Total Tickets en Cola", f"📋 {total_tickets}")
    with m_col2:
        st.metric("Tickets Pendientes", f"🚨 {pendientes}", delta=f"{pendientes} urgentes", delta_color="inverse")
    with m_col3:
        st.metric("En Atención", f"⏳ {en_atencion}")
    with m_col4:
        st.metric("Casos Resueltos", f"✅ {resueltos}", delta="Al día")

    st.markdown("---")

    if not tickets:
        st.info("🎉 ¡Excelente! No hay tickets pendientes en la cola de atención.")
        return

    # 3. Filtros y Búsqueda de Casos
    col_filtro, col_search = st.columns([1.5, 2.5])
    with col_filtro:
        filtro_estado = st.selectbox(
            "Filtrar por Estado:",
            ["TODOS", "PENDIENTE", "EN_ATENCION", "RESUELTO"],
            key="sel_filtro_estado_trabajador"
        )
    with col_search:
        search_query = st.text_input(
            "🔍 Buscar Caso por Nombre de Cliente o ID de Ticket:",
            placeholder="Ej: Lucía Ramos / TCK-1001",
            key="input_search_ticket"
        ).strip().lower()

    # Aplicar filtros
    tickets_filtrados = [
        t for t in tickets
        if (filtro_estado == "TODOS" or t["status"] == filtro_estado) and
           (not search_query or search_query in t["ticket_id"].lower() or search_query in t["client_name"].lower() or search_query in t["client_id"].lower())
    ]

    st.caption(f"Mostrando **{len(tickets_filtrados)}** de **{total_tickets}** tickets totales")

    # 4. Layout Principal: Tabla / Lista de Casos (Izquierda) + Vista Detalle de Atención (Derecha)
    col_lista, col_detalle = st.columns([1.2, 2.2])

    with col_lista:
        st.markdown("#### 📋 Casos Asignados")
        
        for t in tickets_filtrados:
            t_id = t["ticket_id"]
            is_selected = t_id == st.session_state.get("selected_ticket_id")
            selected_style = "border-left: 5px solid #005cff; background: #f0f7ff; box-shadow: 0 4px 12px rgba(0,92,255,0.1);" if is_selected else ""
            
            badge_class = "badge-red" if t["status"] == "PENDIENTE" else ("badge-orange" if t["status"] == "EN_ATENCION" else "badge-green")
            prioridad_badge = "<span style='font-size:10px; color:#dc2626; font-weight:700;'>🔥 ALTA</span>" if t.get("priority") == "ALTA" else "<span style='font-size:10px; color:#64748b;'>MEDIA</span>"

            st.markdown(f"""
            <div class="metric-card" style="{selected_style}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #0a2540; font-size: 15px;">{t['ticket_id']}</strong>
                        <span style="margin-left: 6px;">{prioridad_badge}</span>
                    </div>
                    <span class="{badge_class}">{t['status']}</span>
                </div>
                <div style="font-size: 13px; font-weight: 700; color: #1e293b; margin-top: 4px;">
                    {t['client_name']} <span style="font-size: 11px; color: #64748b; font-weight: normal;">(ID: {t['client_id']})</span>
                </div>
                <div style="font-size: 12px; color: #475569; margin-top: 4px; line-height: 1.3;">
                    <strong>Motivo:</strong> {t['reason'][:60]}...
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 6px;">
                    🕒 {t['timestamp']} · Asignado: <strong>{t.get('assigned_agent', 'Sin Asignar')}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"🔎 Abrir Caso {t_id}", key=f"btn_open_tck_{t_id}", use_container_width=True):
                st.session_state.selected_ticket_id = t_id
                # Si estaba pendiente, pasarlo a EN_ATENCION al abrirlo
                if t["status"] == "PENDIENTE":
                    update_ticket_status(t_id, "EN_ATENCION", agent="Carlos Vega")
                st.rerun()

    with col_detalle:
        # Buscar el ticket activo seleccionado
        t_sel = next((t for t in tickets if t["ticket_id"] == st.session_state.get("selected_ticket_id")), tickets[0] if tickets else None)

        if not t_sel:
            st.info("Seleccione un ticket de la lista para inspeccionar el caso.")
            return

        t_id = t_sel["ticket_id"]
        cid = t_sel["client_id"]

        st.markdown(f"### 🔎 Expediente del Caso: **`{t_id}`**")

        # Cargar datos enriquecidos del cliente
        cliente_meta = CLIENTES_CATALOGO.get(cid, {
            "id": cid,
            "nombre": t_sel["client_name"],
            "servicio": "Plan Fibra Óptica + Móvil",
            "telefono": "987-654-321",
            "periodo": "2026-07",
            "recibo_actual": 119.90,
            "recibo_anterior": 89.90,
            "estado_linea": "Activa"
        })
        ficha = get_ficha_cliente_completa(cid)
        diff_audit = auditar_variacion_recibo(cid, cliente_meta.get("periodo", "2026-07"))
        nbo_data = generar_next_best_offer(cid)

        # -------------------------------------------------------------
        # VISTA DETALLE: 3 PANELES (Ficha Técnica, Chat, Acciones)
        # -------------------------------------------------------------
        
        tab_exp_1, tab_exp_2, tab_exp_3 = st.tabs([
            "📊 **1. Ficha Técnica & Facturación**",
            "💬 **2. Transcripción del Chat con IA**",
            "🛠️ **3. Resolución & Acciones Comerciales**"
        ])

        # PANEL 1: FICHA TÉCNICA Y FACTURACIÓN
        with tab_exp_1:
            st.markdown(f"""
            <div class="metric-card" style="border-left: 4px solid #005cff;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <div style="font-size: 18px; font-weight: 800; color: #0a2540;">{t_sel['client_name']}</div>
                        <div style="font-size: 12px; color: #64748b;">
                            ID: <code>{cid}</code> | Teléfono: <strong>{cliente_meta['telefono']}</strong> | DNI: <strong>4789{cid[-4:]}</strong>
                        </div>
                    </div>
                    <div>
                        <span class="badge-green">● {cliente_meta.get('estado_linea', 'Línea Activa')}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase;">Plan Actual</div>
                    <div style="font-size: 15px; font-weight: 800; color: #0a2540; margin: 4px 0;">{cliente_meta['servicio']}</div>
                    <div style="font-size: 11px; color: #64748b;">Antigüedad: {ficha.get('antiguedad_meses', 12)} meses</div>
                </div>
                """, unsafe_allow_html=True)

            with f_col2:
                var_monto = diff_audit.get("variacion", {}).get("monto", 0.0)
                var_pct = diff_audit.get("variacion", {}).get("porcentaje", 0.0)
                signo = "+" if var_monto > 0 else ""
                color_v = "#ff6a00" if var_monto > 0 else "#00a650"

                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase;">Recibo Julio 2026</div>
                    <div style="font-size: 16px; font-weight: 900; color: #0a2540; margin: 4px 0;">
                        S/ {cliente_meta['recibo_actual']:.2f} <span style="font-size: 12px; color: {color_v};">({signo}S/ {var_monto:.2f})</span>
                    </div>
                    <div style="font-size: 11px; color: #64748b;">Recibo Anterior: S/ {cliente_meta['recibo_anterior']:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            with f_col3:
                eleg_mt = nbo_data.get("es_elegible_mt", False)
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase;">Elegibilidad Movistar Total</div>
                    <div style="font-size: 15px; font-weight: 800; color: {'#00a650' if eleg_mt else '#64748b'}; margin: 4px 0;">
                        {'Apto para Blindaje MT' if eleg_mt else 'Plan Optimizado'}
                    </div>
                    <div style="font-size: 11px; color: #64748b;">Canal Sugerido: {nbo_data.get('canal_mas_usado', 'App Movistar')}</div>
                </div>
                """, unsafe_allow_html=True)

            # Desglose de auditoría del recibo
            st.markdown("##### 🔍 Desglose de Conceptos Auditados (diff_engine.py)")
            conceptos = diff_audit.get("conceptos_adicionales", [])
            if conceptos:
                for c in conceptos:
                    st.markdown(f"""
                    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: #0a2540; font-size: 13px;">{c.get('concepto')}</strong>
                            <span class="badge-orange" style="margin-left: 8px;">{c.get('tipo')}</span>
                        </div>
                        <div style="font-weight: 800; color: #ff6a00; font-size: 14px;">
                            +S/ {c.get('monto', 0.0):.2f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Sin cargos extraordinarios registrados en este ciclo.")

            # Descuentos y Prorrateos
            if ficha.get("descuentos_activos"):
                st.markdown("##### 🎁 Descuentos Activos en Base (BRAINY_DESCUENTOS_CUOTAS)")
                for d in ficha["descuentos_activos"]:
                    st.caption(f"• **{d['descripcion']}**: Descuento de S/ {d['monto']:.2f} (Cuota {d['cuota_actual']}/{d['duracion']}) - Fin: {d['fecha_fin']}")

            if ficha.get("prorrateos_registrados"):
                st.markdown("##### ⏱️ Prorrateos Registrados en Base (BRAINY_PRORRATEO_ALTAS)")
                for p in ficha["prorrateos_registrados"]:
                    st.caption(f"• **Recibo {p['recibo']}**: Prorrateo de S/ {p['monto']:.2f} en ciclo {p['ciclica']} (Línea {p['tipo']})")

        # PANEL 2: TRANSCRIPCIÓN DEL CHAT CON IA
        with tab_exp_2:
            st.markdown("##### 📜 Historial Completo de Conversación Previa")
            st.caption("Revisa la interacción exacta del cliente con el Asistente Digital AI antes de ser derivado:")

            chat_container = st.container(height=340)
            with chat_container:
                history_list = t_sel.get("chat_history", [])
                if not history_list:
                    st.info("No hay mensajes previos registrados en este ticket.")
                for m in history_list:
                    role = m.get("role", "user")
                    content = m.get("content", "")
                    
                    if role == "user":
                        with st.chat_message("user"):
                            st.markdown(f"**👤 Cliente ({t_sel['client_name']}):**\n\n{content}")
                    elif role == "advisor":
                        with st.chat_message("assistant"):
                            st.markdown(f"**👔 Asesor Humano:**\n\n{content}")
                    else:
                        with st.chat_message("assistant"):
                            st.markdown(f"**🤖 Asistente Digital Movistar:**\n\n{content}")

            # Responder al cliente en el chat
            st.markdown("##### ✍️ Enviar Respuesta al Chat del Cliente")
            col_in_msg, col_in_btn = st.columns([3.5, 1.0])
            with col_in_msg:
                respuesta_asesor = st.text_input(
                    "Escribe tu mensaje para el cliente:",
                    placeholder="Ej: Hola Juan, he revisado tu recibo y autoricé la anulación del cobro...",
                    key=f"input_msg_asesor_{t_id}"
                )
            with col_in_btn:
                st.write("")
                if st.button("💬 Enviar", key=f"btn_send_advisor_{t_id}", use_container_width=True):
                    if respuesta_asesor.strip():
                        # Registrar mensaje en historial del ticket y de la sesión
                        nuevo_msg = {
                            "role": "advisor",
                            "content": respuesta_asesor.strip(),
                            "metadata": {"timestamp": datetime.now().strftime("%H:%M"), "asesor": "Carlos Vega"}
                        }
                        t_sel["chat_history"].append(nuevo_msg)
                        add_chat_message("assistant", f"👔 **Asesor Carlos Vega:** {respuesta_asesor.strip()}")
                        st.success("Mensaje enviado y guardado en la conversación del cliente.")
                        st.rerun()

        # PANEL 3: RESOLUCIÓN Y ACCIONES COMERCIALES
        with tab_exp_3:
            # Resumen del problema generado por la IA
            st.markdown("##### 📌 Resumen Contextual del Caso (Generado por IA)")
            st.markdown(f"""
            <div style="background: #fff7ed; border: 1px solid #fed7aa; border-left: 4px solid #ff6a00; border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #9a3412; line-height: 1.5; margin-bottom: 16px;">
                <strong>Motivo Detectado:</strong> {t_sel['reason']}<br><br>
                <strong>Resumen Ejecutivo:</strong><br>
                {t_sel.get('summary', 'El cliente solicitó revisión personalizada de sus conceptos facturados.')}
            </div>
            """, unsafe_allow_html=True)

            # Gestión de Estado y Notas Internas
            st.markdown("##### ⚙️ Actualizar Estado del Ticket")
            col_est1, col_est2 = st.columns([1.5, 2.5])
            with col_est1:
                nuevo_st = st.selectbox(
                    "Estado Actual:",
                    ["PENDIENTE", "EN_ATENCION", "RESUELTO"],
                    index=["PENDIENTE", "EN_ATENCION", "RESUELTO"].index(t_sel["status"]),
                    key=f"sel_st_detail_{t_id}"
                )
            with col_est2:
                nota_int = st.text_input("Nota Interna de Resolución:", value=t_sel.get("notes", ""), key=f"input_notes_{t_id}")

            if st.button("💾 Guardar Estado y Notas", type="primary", key=f"btn_save_st_{t_id}", use_container_width=True):
                update_ticket_status(t_id, nuevo_st, nota_int, agent="Carlos Vega")
                st.success(f"Ticket {t_id} actualizado con éxito a estado: {nuevo_st}.")
                st.rerun()

            st.markdown("---")
            st.markdown("##### ⚡ Palancas y Soluciones Rápidas de Retención")

            s_col1, s_col2 = st.columns(2)
            with s_col1:
                st.markdown("""
                <div class="metric-card" style="text-align: center;">
                    <strong style="color: #0a2540;">💳 Fraccionamiento de Deuda</strong>
                    <p style="font-size: 12px; color: #64748b; margin-top: 4px;">Diferir el saldo en 6 cuotas fijas al 0% de interés</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Aprobar Fraccionamiento 6 Cuotas", key=f"btn_fracc_fast_{t_id}", use_container_width=True):
                    update_ticket_status(t_id, "RESUELTO", "Fraccionamiento de 6 cuotas aprobado por asesor senior.")
                    add_chat_message("assistant", f"👔 **Asesor Carlos Vega:** He aprobado tu plan de fraccionamiento en 6 cuotas sin intereses. Se reflejará en tu próximo ciclo.")
                    st.success("¡Fraccionamiento autorizado y registrado en la cuenta!")
                    st.rerun()

            with s_col2:
                st.markdown("""
                <div class="metric-card" style="text-align: center;">
                    <strong style="color: #0a2540;">🚀 Blindaje Movistar Total</strong>
                    <p style="font-size: 12px; color: #64748b; margin-top: 4px;">Migrar a plan convergente con hasta 50% de ahorro</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Aplicar Upgrade Movistar Total", key=f"btn_mt_fast_{t_id}", use_container_width=True):
                    of_nbo = nbo_data.get("oferta_recomendada", {})
                    update_ticket_status(t_id, "RESUELTO", f"Migración a {of_nbo.get('nombre_oferta', 'Movistar Total')} aplicada con ahorro.")
                    add_chat_message("assistant", f"👔 **Asesor Carlos Vega:** He gestionado tu migración a {of_nbo.get('nombre_oferta', 'Movistar Total')}. Tu nuevo recibo unificado generará un ahorro de hasta el 50%.")
                    st.success("¡Migración a Movistar Total aplicada exitosamente!")
                    st.rerun()
