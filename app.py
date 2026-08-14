"""
app.py - Asistente Digital de Facturación y CRM de Atención al Cliente (Movistar)
Construido con Streamlit, SQLite, diff_engine.py y nbo_engine.py.
"""

import streamlit as st
import json
from datetime import datetime
from state_manager import (
    init_session_state,
    CLIENTES_CATALOGO,
    add_chat_message,
    escalate_case_to_human,
    update_ticket_status,
    get_active_client_data
)
from diff_engine import auditar_variacion_recibo
from nbo_engine import generar_next_best_offer
from database import get_connection, get_cliente_by_id


# =========================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CORPORATIVOS
# =========================================================

st.set_page_config(
    page_title="Movistar | Asistente Digital & CRM",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyectar estilos corporativos Movistar
st.markdown("""
<style>
    /* Tipografía y Colores Base */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    :root {
        --movistar-navy: #0a2540;
        --movistar-blue: #005cff;
        --movistar-orange: #ff6a00;
        --movistar-green: #00a650;
    }

    /* Header Banner */
    .movistar-header {
        background: linear-gradient(135deg, #0a2540 0%, #0d3b66 60%, #005cff 100%);
        border-radius: 16px;
        padding: 24px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(10, 37, 64, 0.15);
    }

    /* KPI Cards */
    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(10, 37, 64, 0.04);
        margin-bottom: 12px;
    }

    /* Badges */
    .badge-orange {
        background-color: #fff3eb;
        color: #ff6a00;
        border: 1px solid rgba(255, 106, 0, 0.3);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }

    .badge-blue {
        background-color: #e8f1ff;
        color: #005cff;
        border: 1px solid rgba(0, 92, 255, 0.3);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }

    .badge-green {
        background-color: #e6f7ee;
        color: #00a650;
        border: 1px solid rgba(0, 166, 80, 0.3);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
    }

    .badge-red {
        background-color: #fee2e2;
        color: #dc2626;
        border: 1px solid rgba(220, 38, 38, 0.3);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar estado global
init_session_state()


# =========================================================
# 2. BARRA LATERAL (SELECTOR DE ROL Y CONFIGURACIÓN)
# =========================================================

with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
        <div style="background-color: #005cff; color: white; width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 24px;">M</div>
        <div>
            <div style="font-weight: 800; font-size: 18px; color: #0a2540;">Movistar</div>
            <div style="font-size: 11px; color: #64748b; font-weight: 600;">PORTAL INTEGRADO</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔄 Selector de Perfil")
    
    # Selector de rol principal
    rol_seleccionado = st.radio(
        label="Seleccione el modo de operación:",
        options=["👤 Modo Cliente", "👔 Modo Trabajador / Asesor"],
        index=0 if st.session_state.user_role == "cliente" else 1,
        key="radio_role_selector"
    )

    # Actualizar estado del rol
    nuevo_rol = "cliente" if "Cliente" in rol_seleccionado else "trabajador"
    if st.session_state.user_role != nuevo_rol:
        st.session_state.user_role = nuevo_rol
        st.rerun()

    st.markdown("---")

    if st.session_state.user_role == "cliente":
        st.markdown("#### 🔍 Simular Cliente")
        opciones_clientes = {
            "CLI001": "CLI001 - Juan Pérez (Repetidor WiFi +S/ 30.00)",
            "1000001": "1000001 - Carlos Mendoza (Elegible Movistar Total)",
            "CLI002": "CLI002 - María Torres (Fin Descuento +S/ 20.00)",
            "CLI004": "CLI004 - Lucía Ramos (Prorrateo Alta +S/ 25.00)",
            "CLI005": "CLI005 - Roberto Díaz (Cuota ShEq +S/ 35.00)",
            "CLI006": "CLI006 - Ana Castro (Reconexión +S/ 10.50)"
        }
        
        selected_client_key = st.selectbox(
            label="Selecciona un caso de cliente:",
            options=list(opciones_clientes.keys()),
            format_func=lambda x: opciones_clientes[x],
            index=list(opciones_clientes.keys()).index(st.session_state.active_client_id) if st.session_state.active_client_id in opciones_clientes else 0
        )

        if st.session_state.active_client_id != selected_client_key:
            st.session_state.active_client_id = selected_client_key
            st.rerun()

        st.caption("ℹ️ Puedes cambiar de cliente en cualquier momento para auditar las variaciones calculadas por `diff_engine.py`.")

    else:
        st.markdown("#### 📊 Estado de la Cola CRM")
        tickets = st.session_state.get("escalated_tickets", [])
        pendientes = sum(1 for t in tickets if t["status"] == "PENDIENTE")
        en_atencion = sum(1 for t in tickets if t["status"] == "EN_ATENCION")
        resueltos = sum(1 for t in tickets if t["status"] == "RESUELTO")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pendientes", f"🚨 {pendientes}")
        with col2:
            st.metric("En Atención", f"⏳ {en_atencion}")
        st.metric("Resueltos", f"✅ {resueltos}")
        
        st.caption("📌 Los casos transferidos por los clientes desde el chat aparecen aquí en tiempo real.")

    st.markdown("---")
    st.markdown("<div style='font-size: 11px; color: #94a3b8; text-align: center;'>Hackathon AI Telecom Challenge<br>Movistar & U. de Lima · 2026</div>", unsafe_allow_html=True)


# =========================================================
# 3. VISTA 1: MODO CLIENTE
# =========================================================

def render_cliente_view():
    cliente = get_active_client_data()
    cid = cliente["id"]
    periodo = cliente["periodo"]

    # Ejecutar auditoría del motor diff_engine.py
    diff_res = auditar_variacion_recibo(cid, periodo)
    # Ejecutar motor de Next Best Offer (NBO)
    nbo_res = generar_next_best_offer(cid)

    # 1. Header Corporativo de Cliente
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
                <div style="font-size: 11px; color: #cbd5e1; text-transform: uppercase; font-weight: 600;">Total Recibo Julio 2026</div>
                <div style="font-size: 24px; font-weight: 900; color: #ffffff;">S/ {cliente['recibo_actual']:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. KPIs Financieros y Auditoría
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
        var = diff_res.get("variacion", {"monto": 0.0, "porcentaje": 0.0}) if diff_res.get("encontrado") else {"monto": 0.0, "porcentaje": 0.0}
        monto_var = var.get("monto", 0.0)
        pct_var = var.get("porcentaje", 0.0)
        signo = "+" if monto_var > 0 else ""
        color_var = "#ff6a00" if monto_var > 0 else "#00a650"
        
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {color_var};">
            <div style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase;">Variación de Cobro</div>
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
            <div style="font-size: 11px; color: #00a650; font-weight: 600;">✓ Apto para beneficios</div>
        </div>
        """, unsafe_allow_html=True)

    # 3. Auditoría Explicativa de Conceptos (diff_engine.py)
    with st.expander("🔍 **Auditoría Detallada del Recibo (Explicación AI)**", expanded=True):
        conceptos = diff_res.get("conceptos_adicionales", [])
        if not conceptos:
            st.info("✅ **No se detectaron cobros adicionales ni variaciones extraordinarias** en este periodo. Tu tarifa regular se mantiene idéntica.")
        else:
            st.markdown(f"**Se identificaron {len(conceptos)} concepto(s) que explican la variación del recibo:**")
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

    st.markdown("---")

    # 4. Módulo Interactivo de Solución Comercial (Tabs)
    st.markdown("### 💡 Soluciones Comerciales Personalizadas")
    
    tab1, tab2 = st.tabs(["💳 **Opción A: Fraccionamiento de Deuda (0% Intereses)**", "🚀 **Opción B: Upgrade a Movistar Total (Ahorro 50%)**"])

    with tab1:
        st.markdown("#### Plan de Alivio Financiero sin Intereses")
        st.write("Difiere el pago del total de tu recibo en cuotas mensuales automáticas en tus próximos ciclos:")
        
        col_c1, col_c2, col_c3 = st.columns(3)
        total_recibo = cliente["recibo_actual"]

        with col_c1:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center; border: 2px solid #005cff; background: #f0f7ff;">
                <span class="badge-blue">3 Meses</span>
                <div style="font-size: 22px; font-weight: 900; color: #0a2540; margin-top: 8px;">S/ {(total_recibo/3):.2f} / mes</div>
                <div style="font-size: 11px; color: #64748b;">3 cuotas fijas (TCEA 0.0%)</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Solicitar 3 Cuotas", key="btn_3c", use_container_width=True):
                st.success(f"🎉 ¡Fraccionamiento aprobado! Pagarás 3 cuotas fijas de S/ {(total_recibo/3):.2f} a partir de Agosto 2026.")

        with col_c2:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <span class="badge-blue">6 Meses</span>
                <div style="font-size: 22px; font-weight: 900; color: #0a2540; margin-top: 8px;">S/ {(total_recibo/6):.2f} / mes</div>
                <div style="font-size: 11px; color: #64748b;">6 cuotas fijas (TCEA 0.0%)</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Solicitar 6 Cuotas", key="btn_6c", use_container_width=True):
                st.success(f"🎉 ¡Fraccionamiento aprobado! Pagarás 6 cuotas fijas de S/ {(total_recibo/6):.2f} a partir de Agosto 2026.")

        with col_c3:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <span class="badge-blue">12 Meses</span>
                <div style="font-size: 22px; font-weight: 900; color: #0a2540; margin-top: 8px;">S/ {(total_recibo/12):.2f} / mes</div>
                <div style="font-size: 11px; color: #64748b;">12 cuotas fijas (TCEA 0.0%)</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Solicitar 12 Cuotas", key="btn_12c", use_container_width=True):
                st.success(f"🎉 ¡Fraccionamiento aprobado! Pagarás 12 cuotas fijas de S/ {(total_recibo/12):.2f} a partir de Agosto 2026.")

    with tab2:
        if nbo_res.get("encontrado") and nbo_res.get("es_elegible_mt"):
            of = nbo_res["oferta_recomendada"]
            ben = nbo_res["beneficio_economico"]

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
                st.markdown(f"**Vía de contacto sugerida:** `{nbo_res.get('canal_mas_usado')}` | **Probabilidad de Aceptación:** `{nbo_res.get('probabilidad_aceptacion')*100:.0f}%`")
            with col_b2:
                if st.button("🚀 Migrar a Movistar Total", type="primary", use_container_width=True):
                    st.balloons()
                    st.success(f"🎉 ¡Solicitud de migración enviada para {of.get('nombre_oferta')}! Un asesor comercial te contactará por {nbo_res.get('canal_mas_usado')}.")
        else:
            st.info("ℹ️ El cliente ya cuenta con plan convergente o su perfil actual está optimizado.")

    st.markdown("---")

    # 5. Asistente Conversacional AI y Botón de Escalación a Humano
    st.markdown("### 💬 Chat con Asistente Digital Movistar")
    
    col_chat_hdr, col_esc_btn = st.columns([3, 1])
    with col_chat_hdr:
        st.caption("Consulta tus dudas de facturación o pide asistencia directa.")
    with col_esc_btn:
        if st.button("🚨 Transferir a Asesor Humano", use_container_width=True):
            ticket_id = escalate_case_to_human(
                client_id=cid,
                client_name=cliente["nombre"],
                reason=f"Cliente solicita atención humana directa para revisión de recibo {periodo}."
            )
            add_chat_message("assistant", f"⚠️ **Tu caso ha sido transferido a un asesor humano.** Se ha generado el ticket **`{ticket_id}`** en la cola de atención prioritaria.")
            st.warning(f"¡Caso derivado con éxito! Ticket generado: **{ticket_id}**. El asesor asignado responderá a la brevedad.")

    # Renderizar historial de mensajes
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Entrada de texto del usuario
    if prompt := st.chat_input("Escribe tu consulta sobre tu recibo o servicios..."):
        # Agregar mensaje del usuario
        add_chat_message("user", prompt)
        
        # Lógica simulada de respuesta inteligente del Asistente Digital
        prompt_lower = prompt.lower()
        if "por qué" in prompt_lower or "subio" in prompt_lower or "aumento" in prompt_lower or "variacion" in prompt_lower:
            conceptos_txt = ", ".join([f"{c['concepto']} (+S/ {c['monto']:.2f})" for c in diff_res.get("conceptos_adicionales", [])])
            if conceptos_txt:
                bot_reply = f"Auditando tu recibo de {periodo}, tu variación se debe a: **{conceptos_txt}**. Tu cargo fijo base se mantiene sin cambios."
            else:
                bot_reply = f"Tu recibo de {periodo} no presenta cargos extraordinarios respecto al mes anterior."
        elif "fraccionar" in prompt_lower or "cuotas" in prompt_lower or "pagar" in prompt_lower:
            bot_reply = f"Puedes fraccionar tu recibo actual de **S/ {cliente['recibo_actual']:.2f}** en 3 cuotas fijas de **S/ {(cliente['recibo_actual']/3):.2f} sin intereses** desde la pestaña de Soluciones Comerciales."
        elif "movistar total" in prompt_lower or "ahorrar" in prompt_lower or "promo" in prompt_lower:
            bot_reply = "Te recomiendo migrar a **Movistar Total**, unificando tu internet fijo y celular en un solo recibo con hasta **50% de ahorro**."
        elif "humano" in prompt_lower or "asesor" in prompt_lower or "queja" in prompt_lower:
            ticket_id = escalate_case_to_human(
                client_id=cid,
                client_name=cliente["nombre"],
                reason=f"Solicitud de asesor humano vía chat: '{prompt}'"
            )
            bot_reply = f"He transferido tu caso a un asesor especializado. Tu número de ticket es **`{ticket_id}`**."
        else:
            bot_reply = f"Comprendo tu consulta: '{prompt}'. He revisado tu cuenta ({cid}) y todo tu historial se encuentra disponible para ayudarte."

        add_chat_message("assistant", bot_reply)
        st.rerun()


# =========================================================
# 4. VISTA 2: MODO TRABAJADOR / ASESOR CRM
# =========================================================

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
        filtro_estado = st.selectbox("Filtrar por estado:", ["TODOS", "PENDIENTE", "EN_ATENCION", "RESUELTO"], key="filtro_tickets")
        
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

            if st.button(f"Inspeccionar {t_id}", key=f"btn_inspect_{t_id}", use_container_width=True):
                st.session_state.selected_ticket_id = t_id
                st.rerun()

    with col_detalle:
        # Buscar ticket seleccionado
        t_sel = next((t for t in tickets if t["ticket_id"] == st.session_state.selected_ticket_id), tickets[0] if tickets else None)

        if t_sel:
            st.markdown(f"#### 🔎 Detalle del Caso: **`{t_sel['ticket_id']}`**")
            
            # Datos del cliente e historial
            cliente_info = CLIENTES_CATALOGO.get(t_sel["client_id"], {
                "id": t_sel["client_id"],
                "nombre": t_sel["client_name"],
                "servicio": "Servicio Fijo/Móvil",
                "periodo": "2026-07",
                "recibo_actual": 119.90,
                "recibo_anterior": 89.90
            })

            # Auditoría del diff engine para este cliente
            diff_audit = auditar_variacion_recibo(t_sel["client_id"], cliente_info["periodo"])
            
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
                    key="sel_nuevo_estado"
                )
            with col_act2:
                nota_asesor = st.text_input("Nota interna:", value=t_sel.get("notes", ""), key="input_nota_asesor")
            with col_act3:
                st.write("")
                st.write("")
                if st.button("Guardar Cambios", type="primary", use_container_width=True):
                    update_ticket_status(t_sel["ticket_id"], nuevo_estado, nota_asesor, agent="Carlos Vega")
                    st.success(f"Ticket {t_sel['ticket_id']} actualizado a {nuevo_estado}.")
                    st.rerun()

            st.markdown("##### ⚡ Soluciones Rápidas")
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                if st.button("💳 Autorizar Fraccionamiento 6 Cuotas", use_container_width=True):
                    update_ticket_status(t_sel["ticket_id"], "RESUELTO", "Fraccionamiento de 6 cuotas aprobado por asesor.")
                    st.success("¡Fraccionamiento autorizado y registrado en base comercial!")
                    st.rerun()
            with s_col2:
                if st.button("🚀 Aplicar Migración Movistar Total", use_container_width=True):
                    update_ticket_status(t_sel["ticket_id"], "RESUELTO", "Migración a Movistar Total aplicada con 50% de ahorro.")
                    st.success("¡Migración a Movistar Total aplicada exitosamente!")
                    st.rerun()


# =========================================================
# 5. ENRUTAMIENTO PRINCIPAL DE VISTAS SEGÚN ROL
# =========================================================

if st.session_state.user_role == "cliente":
    render_cliente_view()
else:
    render_trabajador_view()
