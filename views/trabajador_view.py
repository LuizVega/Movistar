"""
views/trabajador_view.py - Panel de Control del Asesor CRM (Diseño Apple Minimalist + Movistar Colors)
Sincronizado en tiempo real con el Chat del Cliente, con Resumen Ejecutivo de IA,
Protección de Datos Personales (Anonimización) y Acciones Inmediatas de Resolución.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional
from state_manager import (
    CLIENTES_CATALOGO,
    update_ticket_status,
    add_chat_message,
    switch_active_client,
    get_active_client_data
)
from diff_engine import auditar_variacion_recibo
from database import get_ficha_cliente_completa
from nbo_engine import generar_next_best_offer
from components.chat_elements import get_theme_colors, YARA_AVATAR_URL


def mask_sensitive_data(val: str) -> str:
    """Aplica anonimización y enmascaramiento para seguridad de datos personales."""
    if not val:
        return "••••••••"
    val_str = str(val).strip()
    if len(val_str) <= 4:
        return "••••"
    return f"{val_str[:2]}••••{val_str[-2:]}"


def render_trabajador_view():
    """Renderiza el panel de control del asesor con diseño Apple Minimalist y conexión total con Yara AI."""
    theme = get_theme_colors()
    is_dark = st.session_state.get("theme_mode", "light") == "dark"
    privacy_mode = st.session_state.get("privacy_mode_active", False)

    # 1. Barra de Navegación Superior
    col_nav_left, col_nav_center, col_nav_right = st.columns([2.0, 3.2, 2.4])

    with col_nav_left:
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("👤 Chat Cliente", key="btn_to_client_from_worker", type="primary", use_container_width=True):
                st.session_state.view_mode = "cliente"
                st.session_state.user_role = "cliente"
                st.rerun()
        with btn_c2:
            if st.button("🏠 Inicio", key="btn_to_landing_from_worker", use_container_width=True):
                st.session_state.view_mode = "landing"
                st.rerun()

    with col_nav_center:
        st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; padding-top: 4px;">
            <span style="font-size: 20px;">👔</span>
            <span style="font-size: 17px; font-weight: 800; color: {theme['highlight']};">Bandeja de Asesor CRM</span>
            <span style="font-size: 11px; background: #e0f2fe; color: #0284c7; padding: 2px 8px; border-radius: 9999px; font-weight: 700;">🟢 En Vivo</span>
        </div>
        """, unsafe_allow_html=True)

    with col_nav_right:
        col_priv, col_th = st.columns([1.5, 0.7])
        with col_priv:
            label_priv = "🔒 Privacidad: ON" if privacy_mode else "🔓 Privacidad: OFF"
            if st.button(label_priv, key="btn_toggle_privacy_crm", help="Anonimizar datos personales sensibles"):
                st.session_state.privacy_mode_active = not privacy_mode
                st.rerun()
        with col_th:
            theme_icon = "🌙" if not is_dark else "☀️"
            if st.button(theme_icon, key="btn_theme_worker", help="Alternar Modo Claro / Oscuro"):
                st.session_state.theme_mode = "dark" if not is_dark else "light"
                st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # 2. Métricas Resumen Bento
    tickets = st.session_state.get("escalated_tickets", [])
    total_t = len(tickets)
    pend_t = sum(1 for t in tickets if t.get("status") == "PENDIENTE")
    atn_t = sum(1 for t in tickets if t.get("status") == "EN_ATENCION")
    res_t = sum(1 for t in tickets if t.get("status") == "RESUELTO")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div style="background: {theme['bg_card']}; border: 1px solid {theme['border']}; border-radius: 14px; padding: 12px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
            <div style="font-size: 11px; font-weight: 600; color: {theme['text_secondary']}; text-transform: uppercase;">Total Derivaciones</div>
            <div style="font-size: 20px; font-weight: 800; color: {theme['text_primary']}; margin-top: 2px;">📋 {total_t}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div style="background: {theme['bg_card']}; border: 1px solid {theme['border']}; border-radius: 14px; padding: 12px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
            <div style="font-size: 11px; font-weight: 600; color: #dc2626; text-transform: uppercase;">Pendientes</div>
            <div style="font-size: 20px; font-weight: 800; color: #dc2626; margin-top: 2px;">🚨 {pend_t}</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div style="background: {theme['bg_card']}; border: 1px solid {theme['border']}; border-radius: 14px; padding: 12px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
            <div style="font-size: 11px; font-weight: 600; color: #d97706; text-transform: uppercase;">En Atención</div>
            <div style="font-size: 20px; font-weight: 800; color: #d97706; margin-top: 2px;">⏳ {atn_t}</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div style="background: {theme['bg_card']}; border: 1px solid {theme['border']}; border-radius: 14px; padding: 12px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
            <div style="font-size: 11px; font-weight: 600; color: #16a34a; text-transform: uppercase;">Resueltos</div>
            <div style="font-size: 20px; font-weight: 800; color: #16a34a; margin-top: 2px;">✅ {res_t}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    if not tickets:
        st.info("ℹ️ No hay tickets registrados en la cola en este momento.")
        if st.button("➕ Generar Ticket de Prueba para Demostración", key="btn_gen_test_ticket_w"):
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
            key="sel_filtro_estado_crm",
            label_visibility="collapsed"
        )
    with col_search:
        search_query = st.text_input(
            "🔍 Buscar Ticket o Cliente:",
            placeholder="Buscar por ID, Cliente o Motivo...",
            key="input_search_ticket_crm",
            label_visibility="collapsed"
        ).strip().lower()

    tickets_filtrados = [
        t for t in tickets
        if (filtro_estado == "TODOS" or t.get("status") == filtro_estado) and
           (not search_query or search_query in t.get("ticket_id", "").lower() or search_query in t.get("client_name", "").lower() or search_query in t.get("client_id", "").lower())
    ]

    # 4. Layout Dividido: Bandeja (Izquierda) + Expediente 360° (Derecha)
    col_lista, col_detalle = st.columns([1.1, 2.1])

    with col_lista:
        st.markdown(f"<div style='font-size: 14px; font-weight: 700; color: {theme['text_primary']}; margin-bottom: 8px;'>📋 Casos en Espera</div>", unsafe_allow_html=True)

        if not tickets_filtrados:
            st.caption("No se encontraron tickets con los filtros seleccionados.")

        for t in tickets_filtrados:
            t_id = t["ticket_id"]
            is_selected = (t_id == st.session_state.get("selected_ticket_id"))
            border_col = theme["highlight"] if is_selected else theme["border"]
            bg_col = "#e0f2fe" if (is_selected and not is_dark) else (theme["bg_card"] if not is_selected else "#1e3a5f")

            badge_bg = "#fee2e2" if t.get("status") == "PENDIENTE" else ("#fff3eb" if t.get("status") == "EN_ATENCION" else "#dcfce7")
            badge_fg = "#dc2626" if t.get("status") == "PENDIENTE" else ("#d97706" if t.get("status") == "EN_ATENCION" else "#15803d")
            prio_label = "🔥 ALTA" if t.get("priority") == "ALTA" else "MEDIA"

            c_name = t.get("client_name", "Cliente")
            if privacy_mode:
                c_name = mask_sensitive_data(c_name)

            st.markdown(f"""
            <div style="background: {bg_col}; border: 1px solid {border_col}; border-radius: 12px; padding: 12px 14px; margin-bottom: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.02);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: {theme['highlight']}; font-size: 13px;">{t_id}</strong>
                    <span style="background: {badge_bg}; color: {badge_fg}; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 9999px;">{t.get('status')}</span>
                </div>
                <div style="font-size: 13px; font-weight: 700; color: {theme['text_primary']}; margin-top: 4px;">
                    {c_name} <span style="font-size: 11px; color: {theme['text_secondary']}; font-weight: normal;">({t.get('client_id')})</span>
                </div>
                <div style="font-size: 12px; color: {theme['text_secondary']}; margin-top: 4px; line-height: 1.3;">
                    {t.get('reason', '')[:65]}...
                </div>
                <div style="font-size: 10px; color: {theme['text_secondary']}; margin-top: 6px;">
                    🕒 {t.get('timestamp', '')} · Prioridad: <strong>{prio_label}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"📂 Ver Expediente {t_id}", key=f"btn_open_exp_{t_id}", use_container_width=True):
                st.session_state.selected_ticket_id = t_id
                if t.get("status") == "PENDIENTE":
                    update_ticket_status(t_id, "EN_ATENCION", agent="Carlos Vega")
                st.rerun()

    with col_detalle:
        selected_id = st.session_state.get("selected_ticket_id")
        t_sel = next((t for t in tickets if t["ticket_id"] == selected_id), tickets[0] if tickets else None)

        if not t_sel:
            st.info("Selecciona un ticket de la lista para ver su expediente.")
            return

        t_id = t_sel["ticket_id"]
        cid = t_sel.get("client_id", "CLI001")
        cliente_meta = CLIENTES_CATALOGO.get(cid, {
            "id": cid,
            "nombre": t_sel.get("client_name", "Cliente"),
            "servicio": "Plan Fibra Óptica + Móvil",
            "recibo_actual": 119.90,
            "recibo_anterior": 89.90,
            "diferencia": 30.00,
            "motivo_principal": "Ajuste de facturación",
            "beneficios_actuales": "Internet simétrico y minutos ilimitados"
        })

        diff_audit = auditar_variacion_recibo(cid, "2026-07")
        nbo_data = generar_next_best_offer(cid)
        ai_exec = t_sel.get("ai_exec") or {}

        c_display_name = cliente_meta["nombre"]
        c_display_phone = cliente_meta.get("telefono_movil", "987654321")
        if privacy_mode:
            c_display_name = mask_sensitive_data(c_display_name)
            c_display_phone = mask_sensitive_data(c_display_phone)

        # Header del Expediente
        mod_fac = cliente_meta.get("modalidad_facturacion", "Renta Adelantada")
        prod_b2c = cliente_meta.get("tipo_producto_b2c", cliente_meta.get("servicio", "B2C"))
        esc_tag = cliente_meta.get("escenario_tag", cliente_meta.get("motivo_principal", "Facturación"))

        badge_m_bg = "#e0f2fe" if mod_fac == "Renta Adelantada" else "#fef3c7"
        badge_m_fg = "#0284c7" if mod_fac == "Renta Adelantada" else "#b45309"

        col_h1, col_h2 = st.columns([2.3, 0.9])
        with col_h1:
            st.markdown(f"""
            <div style="background: {theme['bg_card']}; border: 1px solid {theme['border']}; border-radius: 14px; padding: 14px 18px; margin-bottom: 10px; border-left: 4px solid {theme['highlight']};">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 16px; font-weight: 800; color: {theme['text_primary']};">{c_display_name}</span>
                            <span style="background: {badge_m_bg}; color: {badge_m_fg}; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px;">{mod_fac}</span>
                        </div>
                        <div style="font-size: 12px; color: {theme['text_secondary']}; margin-top: 4px;">
                            ID: <code>{cid}</code> | Móvil: <strong>{c_display_phone}</strong> | Producto: <strong>{prod_b2c}</strong>
                        </div>
                    </div>
                    <span style="background: #eef2ff; color: #4338ca; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px;">
                        {esc_tag}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_h2:
            if st.button("💬 Ir a Chat Cliente", key=f"btn_jump_to_chat_{t_id}", type="primary", use_container_width=True):
                switch_active_client(cid)
                st.session_state.view_mode = "cliente"
                st.session_state.user_role = "cliente"
                st.rerun()


        # Tabs de Inspección
        tab_resumen, tab_chat, tab_gestion = st.tabs([
            "🧠 **Resumen IA & Auditoría**",
            "💬 **Transcripción en Vivo**",
            "⚡ **Acciones de Resolución**"
        ])

        # TAB 1: RESUMEN EJECUTIVO IA Y AUDITORÍA
        with tab_resumen:
            # Tarjeta de Resumen Ejecutivo por IA
            res_ia_texto = ai_exec.get("resumen_texto") or t_sel.get("summary") or "Consulta por variación de recibo."
            sentimiento_ia = ai_exec.get("sentimiento", "CONSULTIVO")
            sugerencia_ia = ai_exec.get("sugerencia_asesor", "Aclarar motivo de cobro y ofrecer facilidades.")

            st.markdown(f"""
            <div style="background: {theme['bg_card_header']}; border: 1px solid {theme['border']}; border-radius: 14px; padding: 14px 18px; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: {theme['highlight']};">
                        <span>🤖</span> Resumen Ejecutivo para el Asesor (Yara AI)
                    </div>
                    <span style="background: #e0f2fe; color: #0284c7; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">
                        Sentimiento: {sentimiento_ia}
                    </span>
                </div>
                <p style="font-size: 13px; color: {theme['text_primary']}; line-height: 1.45; margin: 0 0 8px 0;">
                    {res_ia_texto}
                </p>
                <div style="font-size: 12px; color: {theme['text_secondary']}; background: {theme['bg_card']}; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #16a34a;">
                    💡 <strong>Sugerencia de Resolución:</strong> {sugerencia_ia}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Bento Grid Financiero
            f1, f2 = st.columns(2)
            with f1:
                r_act = float(cliente_meta.get("recibo_actual", 119.90))
                r_ant = float(cliente_meta.get("recibo_anterior", 89.90))
                delta_m = round(r_act - r_ant, 2)
                signo = "+" if delta_m > 0 else ""
                st.markdown(f"""
                <div style="background: {theme['bg_card']}; border: 1px solid {theme['border']}; border-radius: 12px; padding: 12px 14px;">
                    <div style="font-size: 11px; color: {theme['text_secondary']}; font-weight: 700; text-transform: uppercase;">Variación Auditada (Julio vs Junio)</div>
                    <div style="font-size: 18px; font-weight: 800; color: {theme['text_primary']}; margin-top: 4px;">
                        S/ {r_act:.2f} <span style="font-size: 13px; color: {'#dc2626' if delta_m > 0 else '#16a34a'}; font-weight: 700;">({signo}S/ {delta_m:.2f})</span>
                    </div>
                    <div style="font-size: 12px; color: {theme['text_secondary']}; margin-top: 2px;">
                        Motivo: <strong>{cliente_meta.get('motivo_principal')}</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with f2:
                nbo_of = nbo_data.get("oferta_recomendada", {})
                ahorro_nbo = nbo_data.get("beneficio_economico", {}).get("ahorro_mensual_soles", 0.0)
                st.markdown(f"""
                <div style="background: {theme['bg_card']}; border: 1px solid {theme['border']}; border-radius: 12px; padding: 12px 14px;">
                    <div style="font-size: 11px; color: {theme['text_secondary']}; font-weight: 700; text-transform: uppercase;">Propuesta Comercial NBO</div>
                    <div style="font-size: 15px; font-weight: 800; color: {theme['highlight']}; margin-top: 4px;">
                        {nbo_of.get('nombre_oferta', 'Movistar Total')}
                    </div>
                    <div style="font-size: 12px; color: #16a34a; font-weight: 700; margin-top: 2px;">
                        Ahorro mensual potencial: S/ {ahorro_nbo:.2f}/mes
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # TAB 2: TRANSCRIPCIÓN DEL CHAT
        with tab_chat:
            st.markdown(f"<div style='font-size: 13px; font-weight: 700; color: {theme['text_primary']}; margin-bottom: 6px;'>💬 Historial de Conversación en Vivo</div>", unsafe_allow_html=True)
            
            chat_container = st.container(height=260)
            with chat_container:
                history_list = t_sel.get("chat_history", [])
                if not history_list:
                    st.caption("Sin mensajes previos registrados en el chat.")
                for m in history_list:
                    role = m.get("role", "user")
                    content = m.get("content", "")
                    if role == "user":
                        st.markdown(f"""
                        <div style="display: flex; justify-content: flex-start; margin-bottom: 8px;">
                            <div style="background: #00639c; color: #ffffff; border-radius: 14px; padding: 8px 14px; font-size: 13px; max-width: 85%;">
                                <strong>👤 Cliente:</strong> {content}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif role == "advisor":
                        st.markdown(f"""
                        <div style="display: flex; justify-content: flex-end; margin-bottom: 8px;">
                            <div style="background: #16a34a; color: #ffffff; border-radius: 14px; padding: 8px 14px; font-size: 13px; max-width: 85%;">
                                <strong>👔 Asesor Carlos Vega:</strong> {content}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="display: flex; justify-content: flex-start; margin-bottom: 8px;">
                            <div style="background: {theme['bg_card_header']}; color: {theme['text_primary']}; border: 1px solid {theme['border']}; border-radius: 14px; padding: 8px 14px; font-size: 13px; max-width: 85%;">
                                <strong>🤖 Yara AI:</strong> {content}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

            # Responder directamente al chat del cliente
            st.markdown(f"<div style='font-size: 12px; font-weight: 700; color: {theme['text_secondary']}; margin-top: 8px;'>✍️ Responder al Cliente en su Chat:</div>", unsafe_allow_html=True)
            col_msg_in, col_msg_btn = st.columns([3.5, 1.0])
            with col_msg_in:
                msg_asesor = st.text_input("Respuesta:", placeholder="Ej: Hola, revisé tu caso y he autorizado el fraccionamiento...", key=f"inp_msg_{t_id}", label_visibility="collapsed")
            with col_msg_btn:
                if st.button("💬 Enviar", key=f"btn_send_{t_id}", type="primary", use_container_width=True):
                    if msg_asesor.strip():
                        t_sel["chat_history"].append({
                            "role": "advisor",
                            "content": msg_asesor.strip(),
                            "metadata": {"timestamp": datetime.now().strftime("%H:%M"), "asesor": "Carlos Vega"}
                        })
                        add_chat_message("assistant", f"👔 **Asesor Carlos Vega:** {msg_asesor.strip()}")
                        st.success("Mensaje sincronizado con el cliente.")
                        st.rerun()

        # TAB 3: ACCIONES DE RESOLUCIÓN INMEDIATA
        with tab_gestion:
            st.markdown(f"""
            <div style="background: {theme['bg_card_header']}; border-radius: 10px; padding: 12px 16px; font-size: 13px; margin-bottom: 12px;">
                <strong>Estado del Caso:</strong> <code>{t_sel.get('status')}</code> | <strong>Prioridad:</strong> <code>{t_sel.get('priority')}</code>
            </div>
            """, unsafe_allow_html=True)

            col_s1, col_s2 = st.columns([1.4, 2.6])
            with col_s1:
                cur_status = t_sel.get("status", "PENDIENTE")
                nuevo_st = st.selectbox(
                    "Actualizar Estado:",
                    ["PENDIENTE", "EN_ATENCION", "RESUELTO"],
                    index=["PENDIENTE", "EN_ATENCION", "RESUELTO"].index(cur_status) if cur_status in ["PENDIENTE", "EN_ATENCION", "RESUELTO"] else 0,
                    key=f"sel_st_{t_id}"
                )
            with col_s2:
                notas = st.text_input("Notas de Resolución:", value=t_sel.get("notes", ""), key=f"inp_notes_{t_id}")

            if st.button("💾 Guardar Gestión", key=f"btn_save_crm_{t_id}", type="secondary", use_container_width=True):
                update_ticket_status(t_id, nuevo_st, notas, agent="Carlos Vega")
                st.success(f"Ticket {t_id} actualizado.")
                st.rerun()

            st.markdown("---")
            st.markdown(f"<div style='font-size: 13px; font-weight: 700; color: {theme['text_primary']}; margin-bottom: 6px;'>⚡ Acciones Rápidas del Asesor:</div>", unsafe_allow_html=True)
            
            act_col1, act_col2 = st.columns(2)
            with act_col1:
                if st.button("💳 Aprobar Fraccionamiento (6 cuotas)", key=f"btn_act_f_{t_id}", use_container_width=True):
                    update_ticket_status(t_id, "RESUELTO", "Fraccionamiento de 6 cuotas aprobado por asesor.")
                    add_chat_message("assistant", "👔 **Asesor Carlos Vega:** He aprobado el fraccionamiento de tu recibo en 6 cuotas fijas sin intereses.")
                    st.success("Fraccionamiento autorizado y notificado al chat.")
                    st.rerun()
            with act_col2:
                if st.button("💵 Aplicar Nota de Crédito S/ 20", key=f"btn_act_nc_{t_id}", use_container_width=True):
                    update_ticket_status(t_id, "RESUELTO", "Nota de crédito de S/ 20.00 aprobada por fidelización.")
                    add_chat_message("assistant", "👔 **Asesor Carlos Vega:** He emitido una Nota de Crédito por **S/ 20.00** a tu favor para regularizar tu saldo.")
                    st.success("Nota de crédito registrada con éxito.")
                    st.rerun()

