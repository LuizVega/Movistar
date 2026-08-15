"""
views/trabajador_view.py - Panel de Control Optimizado del Asesor CRM (Movistar Perú)
Permite gestionar en tiempo real los tickets escalados por Yara AI, visualizar la ficha del cliente,
revisar el historial de chat con la IA, enviar respuestas y aplicar soluciones comerciales inmediatas.
"""

import streamlit as st
from datetime import datetime
from state_manager import (
    CLIENTES_CATALOGO,
    update_ticket_status,
    add_chat_message,
    get_active_client_data
)
from diff_engine import auditar_variacion_recibo
from database import get_ficha_cliente_completa
from nbo_engine import generar_next_best_offer


def render_trabajador_view():
    """Renderiza el panel de control del asesor CRM optimizado y libre de errores."""
    
    # 1. Barra Superior con Botón de Navegación Arriba a la Izquierda
    col_nav_left, col_nav_center, col_nav_right = st.columns([2.5, 3.5, 2.0])

    with col_nav_left:
        t_btn1, t_btn2 = st.columns(2)
        with t_btn1:
            if st.button("👤 Cliente", key="btn_switch_to_client_top_worker", use_container_width=True):
                st.session_state.view_mode = "cliente"
                st.session_state.user_role = "cliente"
                st.rerun()
        with t_btn2:
            if st.button("🏠 Inicio", key="btn_switch_to_landing_top_worker", use_container_width=True):
                st.session_state.view_mode = "landing"
                st.rerun()

    with col_nav_center:
        st.markdown("""
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; padding-top: 4px;">
            <span style="font-size: 18px;">👔</span>
            <span style="font-size: 17px; font-weight: 800; color: #0a2540;">Bandeja CRM</span>
            <span style="font-size: 12px; color: #64748b; font-weight: 600;">| Atención y Derivaciones</span>
        </div>
        """, unsafe_allow_html=True)

    with col_nav_right:
        col_w_th, col_w_user = st.columns([0.6, 1.4])
        with col_w_th:
            is_dark = st.session_state.get("theme_mode", "light") == "dark"
            theme_icon = "🌙" if not is_dark else "☀️"
            if st.button(theme_icon, key="btn_toggle_theme_worker", help="Modo Claro / Oscuro"):
                st.session_state.theme_mode = "dark" if not is_dark else "light"
                st.rerun()
        with col_w_user:
            st.markdown("""
            <div style="text-align: right; font-size: 12px; color: #64748b; padding-top: 6px;">
                Asesor: <strong style="color: #00639c;">Carlos Vega</strong>
            </div>
            """, unsafe_allow_html=True)


    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 2. Métricas de la Cola CRM
    tickets = st.session_state.get("escalated_tickets", [])
    total_tickets = len(tickets)
    pendientes = sum(1 for t in tickets if t.get("status") == "PENDIENTE")
    en_atencion = sum(1 for t in tickets if t.get("status") == "EN_ATENCION")
    resueltos = sum(1 for t in tickets if t.get("status") == "RESUELTO")

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric("Total Tickets", f"📋 {total_tickets}")
    with m_col2:
        st.metric("Pendientes", f"🚨 {pendientes}")
    with m_col3:
        st.metric("En Atención", f"⏳ {en_atencion}")
    with m_col4:
        st.metric("Resueltos", f"✅ {resueltos}")

    st.markdown("---")

    # Si la cola está vacía, mostrar mensaje amigable y botón para crear caso de prueba
    if not tickets:
        st.info("ℹ️ No hay tickets registrados en la cola en este momento.")
        if st.button("➕ Generar Ticket de Prueba para Demostración", key="btn_gen_test_ticket"):
            from state_manager import escalate_case_to_human
            escalate_case_to_human(
                client_id="CLI001",
                client_name="Juan Pérez",
                reason="Consulta de variación de cobro en recibo de Julio 2026."
            )
            st.rerun()
        return

    # 3. Filtros y Búsqueda
    col_filtro, col_search = st.columns([1.5, 2.5])
    with col_filtro:
        filtro_estado = st.selectbox(
            "Filtrar por Estado:",
            ["TODOS", "PENDIENTE", "EN_ATENCION", "RESUELTO"],
            key="sel_filtro_estado_crm"
        )
    with col_search:
        search_query = st.text_input(
            "🔍 Buscar por Cliente, DNI o ID de Ticket:",
            placeholder="Ej: Lucía Ramos / TCK-1001",
            key="input_search_ticket_crm"
        ).strip().lower()

    tickets_filtrados = [
        t for t in tickets
        if (filtro_estado == "TODOS" or t.get("status") == filtro_estado) and
           (not search_query or search_query in t.get("ticket_id", "").lower() or search_query in t.get("client_name", "").lower() or search_query in t.get("client_id", "").lower())
    ]

    # 4. Layout Dividido: Lista de Casos (Izquierda) + Ficha y Expediente (Derecha)
    col_lista, col_detalle = st.columns([1.2, 2.2])

    with col_lista:
        st.markdown("#### 📋 Casos Derivados")
        
        if not tickets_filtrados:
            st.caption("No se encontraron tickets con los filtros actuales.")
        
        for t in tickets_filtrados:
            t_id = t["ticket_id"]
            is_selected = (t_id == st.session_state.get("selected_ticket_id"))
            border_col = "#005cff" if is_selected else "#e2e8f0"
            bg_col = "#f0f7ff" if is_selected else "#ffffff"

            badge_bg = "#fee2e2" if t.get("status") == "PENDIENTE" else ("#fff3eb" if t.get("status") == "EN_ATENCION" else "#e6f7ee")
            badge_fg = "#dc2626" if t.get("status") == "PENDIENTE" else ("#ff6a00" if t.get("status") == "EN_ATENCION" else "#00a650")
            prioridad_str = "🔥 ALTA" if t.get("priority") == "ALTA" else "MEDIA"

            st.markdown(f"""
            <div style="background: {bg_col}; border: 1px solid {border_col}; border-radius: 12px; padding: 12px 16px; margin-bottom: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.02);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: #0a2540; font-size: 14px;">{t_id}</strong>
                    <span style="background: {badge_bg}; color: {badge_fg}; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 9999px;">{t.get('status')}</span>
                </div>
                <div style="font-size: 13px; font-weight: 700; color: #1e293b; margin-top: 4px;">
                    {t.get('client_name')} <span style="font-size: 11px; color: #64748b; font-weight: normal;">(ID: {t.get('client_id')})</span>
                </div>
                <div style="font-size: 12px; color: #475569; margin-top: 4px; line-height: 1.3;">
                    <strong>Motivo:</strong> {t.get('reason', '')[:65]}...
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 6px;">
                    🕒 {t.get('timestamp', '')} · Prioridad: <strong>{prioridad_str}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Abrir Expediente {t_id}", key=f"btn_open_exp_{t_id}", use_container_width=True):
                st.session_state.selected_ticket_id = t_id
                if t.get("status") == "PENDIENTE":
                    update_ticket_status(t_id, "EN_ATENCION", agent="Carlos Vega")
                st.rerun()

    with col_detalle:
        # Resolver ticket seleccionado de forma segura
        selected_id = st.session_state.get("selected_ticket_id")
        t_sel = next((t for t in tickets if t["ticket_id"] == selected_id), tickets[0] if tickets else None)

        if not t_sel:
            st.info("Selecciona un ticket de la lista para ver su expediente.")
            return

        t_id = t_sel["ticket_id"]
        cid = t_sel.get("client_id", "CLI001")

        st.markdown(f"### 📂 Expediente del Caso: **`{t_id}`**")

        cliente_meta = CLIENTES_CATALOGO.get(cid, {
            "id": cid,
            "nombre": t_sel.get("client_name", "Cliente"),
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

        # Tabs de Inspección
        tab1, tab2, tab3 = st.tabs([
            "📊 **1. Ficha del Cliente**",
            "💬 **2. Transcripción con Yara AI**",
            "🛠️ **3. Gestión & Resolución**"
        ])

        # TAB 1: FICHA Y FACTURACIÓN
        with tab1:
            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 18px; margin-bottom: 12px; border-left: 4px solid #005cff;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 17px; font-weight: 800; color: #0a2540;">{t_sel.get('client_name')}</div>
                        <div style="font-size: 12px; color: #64748b;">
                            ID: <code>{cid}</code> | Tel: <strong>{cliente_meta['telefono']}</strong> | Plan: <strong>{cliente_meta['servicio']}</strong>
                        </div>
                    </div>
                    <span style="background: #e6f7ee; color: #00a650; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 9999px;">
                        ● {cliente_meta.get('estado_linea', 'Activa')}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            f_c1, f_c2 = st.columns(2)
            with f_c1:
                var_m = diff_audit.get("variacion", {}).get("monto", 0.0)
                signo_v = "+" if var_m > 0 else ""
                col_v = "#ff6a00" if var_m > 0 else "#00a650"
                st.markdown(f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 14px;">
                    <div style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase;">Recibo Auditado (Julio)</div>
                    <div style="font-size: 18px; font-weight: 800; color: #0a2540; margin-top: 4px;">
                        S/ {cliente_meta['recibo_actual']:.2f} <span style="font-size: 13px; color: {col_v}; font-weight: 700;">({signo_v}S/ {var_m:.2f})</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with f_c2:
                eleg_mt = nbo_data.get("es_elegible_mt", False)
                st.markdown(f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 14px;">
                    <div style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase;">Elegibilidad NBO Movistar Total</div>
                    <div style="font-size: 16px; font-weight: 800; color: {'#00a650' if eleg_mt else '#64748b'}; margin-top: 4px;">
                        {'⭐ Elegible para Blindaje' if eleg_mt else 'Plan Optimizado'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            conceptos = diff_audit.get("conceptos_adicionales", [])
            if conceptos:
                st.markdown("##### 🔍 Conceptos de Variación Detectados:")
                for c in conceptos:
                    st.caption(f"• **{c.get('concepto')}**: +S/ {c.get('monto', 0.0):.2f} (`{c.get('tipo')}`)")

        # TAB 2: TRANSCRIPCIÓN DEL CHAT
        with tab2:
            st.markdown("##### 📜 Transcripción Completa del Asistente")
            chat_container = st.container(height=280)
            with chat_container:
                history_list = t_sel.get("chat_history", [])
                if not history_list:
                    st.caption("Sin mensajes previos registrados.")
                for m in history_list:
                    role = m.get("role", "user")
                    content = m.get("content", "")
                    if role == "user":
                        with st.chat_message("user"):
                            st.markdown(f"**👤 Cliente:** {content}")
                    elif role == "advisor":
                        with st.chat_message("assistant"):
                            st.markdown(f"**👔 Asesor Humano:** {content}")
                    else:
                        with st.chat_message("assistant"):
                            st.markdown(f"**🤖 Yara AI:** {content}")

            # Responder al cliente
            st.markdown("##### ✍️ Enviar Mensaje al Cliente:")
            col_msg_in, col_msg_btn = st.columns([3.5, 1.0])
            with col_msg_in:
                msg_asesor = st.text_input("Respuesta:", placeholder="Ej: Hola, autoricé la anulación del cargo...", key=f"inp_msg_{t_id}")
            with col_msg_btn:
                st.write("")
                if st.button("💬 Enviar", key=f"btn_send_{t_id}", use_container_width=True):
                    if msg_asesor.strip():
                        t_sel["chat_history"].append({
                            "role": "advisor",
                            "content": msg_asesor.strip(),
                            "metadata": {"timestamp": datetime.now().strftime("%H:%M"), "asesor": "Carlos Vega"}
                        })
                        add_chat_message("assistant", f"👔 **Asesor Carlos Vega:** {msg_asesor.strip()}")
                        st.success("Mensaje enviado con éxito.")
                        st.rerun()

        # TAB 3: GESTIÓN Y RESOLUCIÓN
        with tab3:
            st.markdown(f"""
            <div style="background: #fff7ed; border-left: 4px solid #ff6a00; border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #9a3412; margin-bottom: 14px;">
                <strong>Motivo Registrado:</strong> {t_sel.get('reason')}<br>
                <strong>Resumen IA:</strong> {t_sel.get('summary', 'Revisión técnica de facturación solicitada por el cliente.')}
            </div>
            """, unsafe_allow_html=True)

            col_s1, col_s2 = st.columns([1.5, 2.5])
            with col_s1:
                cur_status = t_sel.get("status", "PENDIENTE")
                nuevo_st = st.selectbox(
                    "Estado del Ticket:",
                    ["PENDIENTE", "EN_ATENCION", "RESUELTO"],
                    index=["PENDIENTE", "EN_ATENCION", "RESUELTO"].index(cur_status) if cur_status in ["PENDIENTE", "EN_ATENCION", "RESUELTO"] else 0,
                    key=f"sel_st_{t_id}"
                )
            with col_s2:
                notas = st.text_input("Notas de Cierre:", value=t_sel.get("notes", ""), key=f"inp_notes_{t_id}")

            if st.button("💾 Guardar Actualización", type="primary", key=f"btn_save_{t_id}", use_container_width=True):
                update_ticket_status(t_id, nuevo_st, notas, agent="Carlos Vega")
                st.success(f"Ticket {t_id} actualizado a {nuevo_st}.")
                st.rerun()

            st.markdown("---")
            st.markdown("##### ⚡ Acciones Rápidas de Retención:")
            a_col1, a_col2 = st.columns(2)
            with a_col1:
                if st.button("💳 Aprobar Fraccionamiento 6 Cuotas", key=f"btn_act_fracc_{t_id}", use_container_width=True):
                    update_ticket_status(t_id, "RESUELTO", "Fraccionamiento de 6 cuotas aprobado.")
                    add_chat_message("assistant", "👔 **Asesor Carlos Vega:** He aprobado el fraccionamiento de tu recibo en 6 cuotas fijas sin intereses.")
                    st.success("Fraccionamiento autorizado.")
                    st.rerun()
            with a_col2:
                if st.button("🚀 Aplicar Upgrade Movistar Total", key=f"btn_act_mt_{t_id}", use_container_width=True):
                    of_nbo = nbo_data.get("oferta_recomendada", {})
                    update_ticket_status(t_id, "RESUELTO", f"Upgrade a {of_nbo.get('nombre_oferta', 'Movistar Total')} aplicado.")
                    add_chat_message("assistant", f"👔 **Asesor Carlos Vega:** He gestionado tu migración a {of_nbo.get('nombre_oferta', 'Movistar Total')} con descuento.")
                    st.success("Upgrade a Movistar Total aplicado.")
                    st.rerun()
