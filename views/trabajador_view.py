"""
views/trabajador_view.py - Vista Interactiva del Modo Trabajador / Asesor CRM
Gestión de la cola de tickets escalados, inspector de casos con transcripción completa y resolución.
"""

import streamlit as st
from state_manager import CLIENTES_CATALOGO, update_ticket_status
from diff_engine import auditar_variacion_recibo


def render_trabajador_view():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0a2540 0%, #1e293b 100%); border-radius: 16px; padding: 20px; color: white; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <span class="badge-orange" style="background: #ff6a00; color: white; border: none;">PANEL DE GESTIÓN CRM</span>
                <h2 style="color: white; font-weight: 800; font-size: 24px; margin-top: 6px;">Bandeja de Casos Escalados</h2>
                <p style="color: #94a3b8; font-size: 13px;">Gestión y resolución de derivaciones transferidas desde el Asistente Digital</p>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 12px; color: #cbd5e1;">Asesor Conectado:</span>
                <div style="font-weight: 700; color: #ffffff;">Carlos Vega · Supervisor Comercial</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tickets = st.session_state.get("escalated_tickets", [])
    
    if not tickets:
        st.success("🎉 ¡Excelente! No hay tickets pendientes en la cola de atención.")
        return

    # Layout de 2 columnas: Lista de Tickets (Izquierda) + Inspector de Caso (Derecha)
    col_lista, col_detalle = st.columns([1.2, 2.0])

    with col_lista:
        st.markdown("#### 📋 Cola de Derivaciones")
        
        # Filtro de estado
        filtro_estado = st.selectbox("Filtrar por estado:", ["TODOS", "PENDIENTE", "EN_ATENCION", "RESUELTO"], key="filtro_tickets_view")
        tickets_filtrados = [t for t in tickets if filtro_estado == "TODOS" or t["status"] == filtro_estado]

        st.caption(f"Mostrando {len(tickets_filtrados)} casos")

        for t in tickets_filtrados:
            t_id = t["ticket_id"]
            selected_style = "border-left: 4px solid #005cff; background: #f0f7ff;" if t_id == st.session_state.selected_ticket_id else ""
            badge_class = "badge-red" if t["status"] == "PENDIENTE" else ("badge-orange" if t["status"] == "EN_ATENCION" else "badge-green")

            st.markdown(f"""
            <div class="metric-card" style="{selected_style} cursor: pointer;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: #0a2540;">{t['ticket_id']}</strong>
                    <span class="{badge_class}">{t['status']}</span>
                </div>
                <div style="font-size: 13px; font-weight: 600; color: #334155; margin-top: 4px;">{t['client_name']} ({t['client_id']})</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Motivo: {t['reason'][:45]}...</div>
                <div style="font-size: 10px; color: #94a3b8; margin-top: 4px;">Hora: {t['timestamp']}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Inspeccionar {t_id}", key=f"btn_inspect_tab_{t_id}", use_container_width=True):
                st.session_state.selected_ticket_id = t_id
                st.rerun()

    with col_detalle:
        # Buscar ticket seleccionado
        t_sel = next((t for t in tickets if t["ticket_id"] == st.session_state.selected_ticket_id), tickets[0] if tickets else None)

        if t_sel:
            st.markdown(f"#### 🔎 Detalle del Caso: **`{t_sel['ticket_id']}`**")
            
            cliente_info = CLIENTES_CATALOGO.get(t_sel["client_id"], {
                "id": t_sel["client_id"],
                "nombre": t_sel["client_name"],
                "servicio": "Servicio Fijo/Móvil",
                "periodo": "2026-07",
                "recibo_actual": 119.90,
                "recibo_anterior": 89.90
            })

            # Card de Contexto
            st.markdown(f"""
            <div class="metric-card">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <div style="font-size: 16px; font-weight: 800; color: #0a2540;">{t_sel['client_name']}</div>
                        <div style="font-size: 12px; color: #64748b;">ID Cliente: <code>{t_sel['client_id']}</code> | Servicio: {cliente_info['servicio']}</div>
                    </div>
                    <div>
                        <span class="badge-blue">Asignado: {t_sel.get('assigned_agent', 'Sin Asignar')}</span>
                    </div>
                </div>
                <div style="margin-top: 12px; padding: 8px 12px; background: #fff3eb; border-radius: 8px; font-size: 12px; color: #c2410c;">
                    <strong>Motivo de Derivación:</strong> {t_sel['reason']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Historial de Chat Transcrito
            st.markdown("##### 📜 Transcripción del Chat con el Asistente AI")
            chat_container = st.container(height=220)
            with chat_container:
                for m in t_sel.get("chat_history", []):
                    with st.chat_message(m.get("role", "user")):
                        st.write(m.get("content", ""))

            # Acciones del Asesor
            st.markdown("##### 🛠️ Acciones de Resolución")
            col_act1, col_act2, col_act3 = st.columns(3)

            with col_act1:
                nuevo_estado = st.selectbox(
                    "Cambiar Estado:",
                    ["PENDIENTE", "EN_ATENCION", "RESUELTO"],
                    index=["PENDIENTE", "EN_ATENCION", "RESUELTO"].index(t_sel["status"]),
                    key="sel_nuevo_estado_view"
                )
            with col_act2:
                nota_asesor = st.text_input("Nota interna:", value=t_sel.get("notes", ""), key="input_nota_asesor_view")
            with col_act3:
                st.write("")
                st.write("")
                if st.button("Guardar Cambios", type="primary", key="btn_guardar_cambios_view", use_container_width=True):
                    update_ticket_status(t_sel["ticket_id"], nuevo_estado, nota_asesor, agent="Carlos Vega")
                    st.success(f"Ticket {t_sel['ticket_id']} actualizado a {nuevo_estado}.")
                    st.rerun()

            st.markdown("##### ⚡ Soluciones Rápidas")
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                if st.button("💳 Autorizar Fraccionamiento 6 Cuotas", key="btn_auth_fracc_view", use_container_width=True):
                    update_ticket_status(t_sel["ticket_id"], "RESUELTO", "Fraccionamiento de 6 cuotas aprobado por asesor.")
                    st.success("¡Fraccionamiento autorizado y registrado en base comercial!")
                    st.rerun()
            with s_col2:
                if st.button("🚀 Aplicar Migración Movistar Total", key="btn_auth_mt_view", use_container_width=True):
                    update_ticket_status(t_sel["ticket_id"], "RESUELTO", "Migración a Movistar Total aplicada con 50% de ahorro.")
                    st.success("¡Migración a Movistar Total aplicada exitosamente!")
                    st.rerun()
