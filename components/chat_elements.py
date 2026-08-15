"""
components/chat_elements.py - Componentes UI de Yara AI Billing Copilot (Apple Minimalist + Movistar Colors)
Renderiza tarjetas Bento de facturación, marcadores de análisis y botones interactivos de decisión agéntica.
Los botones ejecutan transacciones reales sobre la base de datos (Órdenes, Fraccionamientos, Pagos y Escalamiento).
"""

import streamlit as st
import re
from typing import Dict, Any, Optional
from datetime import datetime
from state_manager import add_chat_message, CLIENTES_CATALOGO
from services.escalation_service import escalar_a_humano
from services.order_service import ejecutar_upgrade_plan, ejecutar_fraccionamiento_deuda, ejecutar_pago_recibo
from nbo_engine import generar_next_best_offer
from diff_engine import auditar_variacion_recibo

YARA_AVATAR_URL = "https://lh3.googleusercontent.com/aida-public/AB6AXuAK6qFdc2J_wKYqG2JmJHwr75_UuOq6HvRDxGPSGW7ElnZd8r0-Vq9MMRNS6TAsAaOd698fjpeVi5thubsxcuEDYCvxKRdD_udnIjO9xOJz8znzK6aVbwYHrxq2OpzJUnVEyAU9igi_ZSVuL3WvmklqJtp6OddNlV50r3vjjFOCF8krxLLgg-faEEmuIHHBoEIfgdujI-dxoWjKzh-1RBP1XLf5GOulW8hbi_2lIsIaf_jhfMwVSOXQ7g"


def format_text_to_html(text: str) -> str:
    """
    Convierte sintaxis de texto a HTML limpio garantizando que negritas
    (<strong>...</strong>) y saltos de línea se rendericen correctamente sin asteriscos.
    """
    if not text:
        return ""
    # Convertir **texto** a <strong>texto</strong>
    html = re.sub(r"\*\*(.*?)\*\*", r"<strong style='font-weight: 700;'>\1</strong>", text)
    # Convertir *texto* a <em>texto</em>
    html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)
    # Convertir saltos de línea a <br>
    html = html.replace("\n", "<br>")
    return html


def get_theme_colors() -> Dict[str, str]:
    """Retorna los colores de la interfaz según el modo seleccionado (Claro / Oscuro)."""
    is_dark = st.session_state.get("theme_mode", "light") == "dark"
    if is_dark:
        return {
            "bg_card": "#1e293b",
            "bg_card_header": "#0f172a",
            "border": "#334155",
            "text_primary": "#f8fafc",
            "text_secondary": "#94a3b8",
            "bg_pill": "#334155",
            "text_pill": "#cbd5e1",
            "highlight": "#019df4"
        }
    else:
        return {
            "bg_card": "#ffffff",
            "bg_card_header": "#f8fafc",
            "border": "#e2e8f0",
            "text_primary": "#1e293b",
            "text_secondary": "#64748b",
            "bg_pill": "#f1f5f9",
            "text_pill": "#475569",
            "highlight": "#00639c"
        }


def render_analysis_markers():
    """Renderiza la barra de estado de razonamiento de Yara AI (Consultar -> Comprender -> Explicar)."""
    theme = get_theme_colors()
    st.markdown(f"""
    <div style="display: flex; justify-content: center; margin: 8px 0 16px 0;">
        <div style="display: inline-flex; background: {theme['bg_pill']}; border-radius: 9999px; border: 1px solid {theme['border']}; padding: 3px 5px; gap: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="display: flex; align-items: center; gap: 5px; padding: 4px 12px; border-radius: 9999px; font-size: 11px; font-weight: 600; color: {theme['text_pill']};">
                <span style="color: #00639c;">✓</span> Consultar
            </div>
            <div style="display: flex; align-items: center; gap: 5px; padding: 4px 12px; border-radius: 9999px; font-size: 11px; font-weight: 600; color: {theme['text_pill']};">
                <span style="color: #00639c;">✓</span> Comprender
            </div>
            <div style="display: flex; align-items: center; gap: 5px; padding: 4px 12px; border-radius: 9999px; background: #00639c; font-size: 11px; font-weight: 700; color: #ffffff;">
                <span>⟳</span> Explicar
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_bento_billing_card(cliente_context: Dict[str, Any], diff_data: Optional[Dict[str, Any]] = None):
    """Renderiza la tarjeta Bento de Desglose de Facturación minimalista."""
    theme = get_theme_colors()
    cid = str(cliente_context.get("id", "CLI001")).strip().upper()
    diff = diff_data or auditar_variacion_recibo(cid, "2026-07")
    
    recibo_ant = float(cliente_context.get("recibo_anterior", 89.90))
    recibo_act = float(cliente_context.get("recibo_actual", 119.90))
    
    var = diff.get("variacion", {}) or {}
    delta = var.get("monto", recibo_act - recibo_ant)
    signo = "+" if delta > 0 else ""
    
    conceptos = diff.get("conceptos_adicionales", [])
    motivo = conceptos[0]["concepto"] if conceptos else "Variación por ajuste de ciclo o prorrateo"

    st.markdown(f"""
    <div style="background: {theme['bg_card']}; border-radius: 16px; border: 1px solid {theme['border']}; box-shadow: 0 4px 16px rgba(0,0,0,0.04); overflow: hidden; width: 100%; max-width: 520px; margin: 10px 0 14px 48px;">
        <div style="background: {theme['bg_card_header']}; padding: 12px 18px; border-bottom: 1px solid {theme['border']}; display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 14px; font-weight: 700; color: {theme['highlight']}; display: flex; align-items: center; gap: 6px;">
                📑 Desglose de Facturación
            </div>
            <span style="background: #fee2e2; color: #b91c1c; font-size: 12px; font-weight: 700; padding: 2px 10px; border-radius: 9999px;">
                ▲ {signo}S/ {delta:.2f}
            </span>
        </div>
        <div style="padding: 16px 20px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1px solid {theme['border']}; padding-bottom: 12px; margin-bottom: 12px;">
                <div>
                    <div style="font-size: 11px; font-weight: 600; color: {theme['text_secondary']}; text-transform: uppercase;">Mes Anterior (Junio)</div>
                    <div style="font-size: 19px; font-weight: 700; color: {theme['text_primary']};">S/ {recibo_ant:.2f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; font-weight: 600; color: {theme['text_secondary']}; text-transform: uppercase;">Mes Actual (Julio)</div>
                    <div style="font-size: 21px; font-weight: 800; color: {theme['highlight']};">S/ {recibo_act:.2f}</div>
                </div>
            </div>
            <div style="font-size: 13px; color: {theme['text_secondary']}; line-height: 1.4;">
                ℹ️ Cargo auditado: <strong style="color: {theme['text_primary']};">{motivo}</strong> ({signo}S/ {delta:.2f}).
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_chat_action_elements(msg: Dict[str, Any], msg_idx: int, client_context: Dict[str, Any]):
    """
    Renderiza tarjetas interactivas de decisión y botones de acción rápida.
    Los botones SOLO aparecen cuando el agente los recomienda y ejecutan transacciones reales.
    """
    theme = get_theme_colors()
    metadata = msg.get("metadata", {}) or {}
    action_payload = metadata.get("action_payload") or {}
    cid = str(client_context.get("id") or "CLI001").strip().upper()
    recibo_actual = float(client_context.get("recibo_actual", 119.90))

    action_executed_key = f"action_executed_{msg_idx}"
    is_executed = st.session_state.get(action_executed_key, False)

    action_type = action_payload.get("action")

    # 1. Si la acción recomendada es mostrar el Desglose de Facturación
    if action_type == "SHOW_BILLING_BREAKDOWN":
        render_bento_billing_card(client_context)

    # 2. Si la acción recomendada es Propuesta de Movistar Total o Ayuda Comercial
    elif action_type in ["SHOW_UPGRADE_CARD", "UPGRADE_MOVISTAR_TOTAL"]:
        nbo_data = action_payload.get("nbo") or generar_next_best_offer(cid)
        of = nbo_data.get("oferta_recomendada", {})
        ben = nbo_data.get("beneficio_economico", {})

        plan_nombre = of.get("nombre_oferta", "Movistar Total Dúo 200 Mbps + 1 Línea")
        precio_promo = float(of.get("precio_promocional", 110.40))
        velocidad = of.get("velocidad_mbps", 200)
        gigas = of.get("gigas_datos", 40)
        ahorro_mes = float(ben.get("ahorro_mensual_soles", 29.40))
        ahorro_pct = float(ben.get("ahorro_porcentaje", 20.0))

        st.markdown(f"""
        <div style="background: {theme['bg_card']}; border: 1px solid {theme['border']}; border-radius: 16px; padding: 18px 20px; box-shadow: 0 4px 16px rgba(0,0,0,0.04); max-width: 520px; margin: 10px 0 10px 48px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px; color: {theme['highlight']};">
                    <span style="font-size: 18px;">⭐</span>
                    <span style="font-size: 15px; font-weight: 700;">Propuesta de Ahorro Movistar Total</span>
                </div>
                <span style="background: #dcfce7; color: #15803d; font-size: 12px; font-weight: 700; padding: 2px 10px; border-radius: 9999px;">
                    Ahorras {ahorro_pct:.0f}% (S/ {ahorro_mes:.2f}/mes)
                </span>
            </div>
            <p style="font-size: 13.5px; color: {theme['text_secondary']}; line-height: 1.45; margin: 0 0 10px 0;">
                Unifica tu internet y línea móvil en <strong style="color: {theme['text_primary']};">{plan_nombre}</strong> ({velocidad} Mbps + {gigas} GB) por solo <strong style="color: {theme['highlight']}; font-size: 16px;">S/ {precio_promo:.2f}/mes</strong>.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if not is_executed:
            col_b1, col_b2, col_b3, col_b4 = st.columns([1.2, 1.1, 1.0, 1.1])

            with col_b1:
                if st.button("🚀 Cambiar de Plan", key=f"btn_confirm_mt_{msg_idx}", type="primary", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    resultado_orden = ejecutar_upgrade_plan(
                        cliente_id=cid,
                        nuevo_plan_id=of.get("oferta_id", 10),
                        canal="YARA_AI"
                    )
                    st.balloons()
                    add_chat_message(
                        role="assistant",
                        content=(
                            f"🎉 **¡Excelente! Cambio a Movistar Total registrado.**\n\n"
                            f"• **Código de Orden:** `{resultado_orden['orden_id']}`\n"
                            f"• **Nuevo Plan Unificado:** **{resultado_orden['nuevo_plan']}**\n"
                            f"• **Nueva Tarifa:** `S/ {resultado_orden['precio_nuevo']:.2f}/mes` (Ahorras S/ {resultado_orden['ahorro_mensual']:.2f} al mes)\n"
                            f"• **Fecha de Vigencia:** `{resultado_orden['fecha_vigencia']}`."
                        ),
                        metadata={"type": "CONFIRMACION_UPGRADE", "orden": resultado_orden}
                    )
                    st.rerun()

            with col_b2:
                if st.button("💳 Fraccionar", key=f"btn_fracc_quick_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    res_fracc = ejecutar_fraccionamiento_deuda(cid, 6, recibo_actual)
                    add_chat_message(
                        role="assistant",
                        content=f"🎉 **Fraccionamiento Aprobado.** Tu solicitud `{res_fracc['solicitud_id']}` fue procesada en 6 cuotas fijas de **S/ {res_fracc['monto_cuota']:.2f}/mes al 0.0% de interés**."
                    )
                    st.rerun()

            with col_b3:
                if st.button("💳 Pagar", key=f"btn_pay_quick_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    res_pago = ejecutar_pago_recibo(cid, recibo_actual)
                    add_chat_message(
                        role="assistant",
                        content=f"✅ **Pago Registrado con Éxito.** Transacción `{res_pago['transaccion_id']}` por un importe de **S/ {res_pago['monto_pagado']:.2f}**. Tu recibo de julio se encuentra al día."
                    )
                    st.rerun()

            with col_b4:
                if st.button("👨‍💼 Asesor", key=f"btn_advisor_quick_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    ticket = escalar_a_humano(cid, st.session_state.get("chat_history", []), "Cliente solicita atención personalizada de asesor")
                    add_chat_message(
                        role="assistant",
                        content=f"🔔 **He derivado tu caso a un asesor senior.** Ticket CRM: **`{ticket['ticket_id']}`**."
                    )
                    st.rerun()
        else:
            st.caption("✅ *Gestión registrada exitosamente en el sistema.*")

    # 3. Si la acción recomendada es Fraccionamiento de Deuda
    elif action_type == "SHOW_INSTALLMENT_MODAL":
        monto_fracc = float(action_payload.get("monto", recibo_actual))
        if not is_executed:
            st.markdown(f"""
            <div style="background: {theme['bg_card']}; border: 1px solid {theme['border']}; border-radius: 16px; padding: 16px 20px; max-width: 520px; margin: 10px 0 10px 48px;">
                <div style="font-size: 14px; font-weight: 700; color: {theme['highlight']}; margin-bottom: 6px;">💳 Opción de Fraccionamiento al 0.0% TCEA</div>
                <div style="font-size: 13px; color: {theme['text_secondary']};">¿Deseas diferir tu recibo de S/ {monto_fracc:.2f} en 6 cuotas fijas de S/ {(monto_fracc/6):.2f}/mes sin intereses ni comisiones?</div>
            </div>
            """, unsafe_allow_html=True)
            col_f1, col_f2 = st.columns([1.2, 1.2])
            with col_f1:
                if st.button("✅ Fraccionar en 6 cuotas", key=f"btn_fracc_opt_{msg_idx}", type="primary", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    res_fracc = ejecutar_fraccionamiento_deuda(cid, 6, monto_fracc)
                    add_chat_message(
                        role="assistant",
                        content=f"🎉 **Fraccionamiento Aprobado.** Tu solicitud `{res_fracc['solicitud_id']}` fue procesada en 6 cuotas fijas de **S/ {res_fracc['monto_cuota']:.2f}/mes al 0.0% de interés**."
                    )
                    st.rerun()
            with col_f2:
                if st.button("❌ No por ahora", key=f"btn_no_fracc_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    st.rerun()

    # 4. Botones puntuales recomendados por el agente
    elif action_payload.get("show_action_buttons"):
        btns = action_payload.get("show_action_buttons", [])
        if not is_executed:
            cols = st.columns(len(btns))
            for idx_b, b_type in enumerate(btns):
                with cols[idx_b]:
                    if b_type == "PAGAR" and st.button("💳 Pagar ahora", key=f"btn_p_rec_{msg_idx}", type="primary", use_container_width=True):
                        st.session_state[action_executed_key] = True
                        res_pago = ejecutar_pago_recibo(cid, recibo_actual)
                        add_chat_message(
                            role="assistant",
                            content=f"✅ **Pago Registrado con Éxito.** Transacción `{res_pago['transaccion_id']}` por un importe de **S/ {res_pago['monto_pagado']:.2f}**. Tu recibo se encuentra al día."
                        )
                        st.rerun()
                    elif b_type == "CAMBIAR_PLAN" and st.button("🚀 Cambiar de Plan", key=f"btn_c_rec_{msg_idx}", type="primary", use_container_width=True):
                        st.session_state[action_executed_key] = True
                        nbo = generar_next_best_offer(cid)
                        add_chat_message(
                            role="assistant",
                            content=f"Te propongo migrar a **{nbo.get('oferta_recomendada', {}).get('nombre_oferta', 'Movistar Total')}** para ahorrar mensualmente.",
                            metadata={"action_payload": {"action": "SHOW_UPGRADE_CARD", "nbo": nbo}}
                        )
                        st.rerun()
                    elif b_type == "ASESOR" and st.button("👨‍💼 Asesor Humano", key=f"btn_a_rec_{msg_idx}", use_container_width=True):
                        st.session_state[action_executed_key] = True
                        ticket = escalar_a_humano(cid, st.session_state.get("chat_history", []), "Cliente solicita asesor humano")
                        add_chat_message(
                            role="assistant",
                            content=f"🔔 **He transferido tu caso a un asesor.** Ticket de atención: **`{ticket['ticket_id']}`**."
                        )
                        st.rerun()
