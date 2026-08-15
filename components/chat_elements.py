"""
components/chat_elements.py - Componentes UI de Yara AI Billing Copilot (Apple Minimalist + Movistar Colors)
Renderiza tarjetas Bento de facturación, marcadores de análisis (Consultar -> Comprender -> Explicar),
tarjetas de decisión de upgrade/fraccionamiento y modales de confirmación con soporte completo para Modo Claro y Oscuro.
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime
from state_manager import add_chat_message, CLIENTES_CATALOGO
from services.escalation_service import escalar_a_humano
from services.order_service import ejecutar_upgrade_plan, ejecutar_fraccionamiento_deuda
from nbo_engine import generar_next_best_offer
from diff_engine import auditar_variacion_recibo

YARA_AVATAR_URL = "https://lh3.googleusercontent.com/aida-public/AB6AXuAK6qFdc2J_wKYqG2JmJHwr75_UuOq6HvRDxGPSGW7ElnZd8r0-Vq9MMRNS6TAsAaOd698fjpeVi5thubsxcuEDYCvxKRdD_udnIjO9xOJz8znzK6aVbwYHrxq2OpzJUnVEyAU9igi_ZSVuL3WvmklqJtp6OddNlV50r3vjjFOCF8krxLLgg-faEEmuIHHBoEIfgdujI-dxoWjKzh-1RBP1XLf5GOulW8hbi_2lIsIaf_jhfMwVSOXQ7g"


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
    
    recibo_ant = cliente_context.get("recibo_anterior", 89.90)
    recibo_act = cliente_context.get("recibo_actual", 119.90)
    
    var = diff.get("variacion", {}) or {}
    delta = var.get("monto", recibo_act - recibo_ant)
    signo = "+" if delta > 0 else ""
    
    conceptos = diff.get("conceptos_adicionales", [])
    motivo = conceptos[0]["concepto"] if conceptos else "Variación por ajuste de ciclo o prorrateo"

    st.markdown(f"""
    <div style="background: {theme['bg_card']}; border-radius: 16px; border: 1px solid {theme['border']}; box-shadow: 0 4px 16px rgba(0,0,0,0.04); overflow: hidden; width: 100%; max-width: 520px; margin: 10px 0;">
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
    """Renderiza tarjetas interactivas de decisión y botones de acción rápida."""
    theme = get_theme_colors()
    metadata = msg.get("metadata", {}) or {}
    action_payload = metadata.get("action_payload") or {}
    content_lower = msg.get("content", "").lower()
    cid = str(client_context.get("id") or "CLI001").strip().upper()

    action_executed_key = f"action_executed_{msg_idx}"
    is_executed = st.session_state.get(action_executed_key, False)

    # 1. Tarjeta Bento de Facturación si corresponde
    if action_payload.get("action") == "SHOW_BILLING_BREAKDOWN" or any(k in content_lower for k in ["desglose", "variación", "variacion", "subió", "subio", "aumento", "prorrateo", "repetidor"]):
        render_bento_billing_card(client_context)

    # 2. Tarjeta / Modal de Confirmación para Movistar Total
    is_upgrade_action = (
        action_payload.get("action") in ["SHOW_UPGRADE_CARD", "UPGRADE_MOVISTAR_TOTAL"] or
        ("movistar total" in content_lower and ("elegible" in content_lower or "ahorro" in content_lower or "plan recomendado" in content_lower))
    )

    if is_upgrade_action:
        nbo_data = action_payload.get("nbo") or generar_next_best_offer(cid)
        of = nbo_data.get("oferta_recomendada", {})
        ben = nbo_data.get("beneficio_economico", {})

        plan_nombre = of.get("nombre_oferta", "Movistar Total Dúo 200 Mbps + 1 Línea")
        precio_promo = of.get("precio_promocional", 110.40)
        velocidad = of.get("velocidad_mbps", 200)
        gigas = of.get("gigas_datos", 40)
        ahorro_mes = ben.get("ahorro_mensual_soles", 29.40)

        st.markdown(f"""
        <div style="background: {theme['bg_card']}; border: 1px solid {theme['border']}; border-radius: 16px; padding: 18px 20px; box-shadow: 0 4px 16px rgba(0,0,0,0.04); max-width: 520px; margin: 10px 0;">
            <div style="display: flex; align-items: center; gap: 8px; color: {theme['highlight']}; margin-bottom: 6px;">
                <span style="font-size: 18px;">⭐</span>
                <span style="font-size: 15px; font-weight: 700;">Propuesta Movistar Total</span>
            </div>
            <p style="font-size: 13.5px; color: {theme['text_secondary']}; line-height: 1.4; margin: 0 0 12px 0;">
                Cambio a <strong style="color: {theme['text_primary']};">{plan_nombre}</strong> ({velocidad} Mbps + {gigas} GB) por <strong style="color: {theme['highlight']};">S/ {precio_promo:.2f}/mes</strong> (Ahorro de S/ {ahorro_mes:.2f}/mes).
            </p>
        </div>
        """, unsafe_allow_html=True)

        if not is_executed:
            col_b1, col_b2 = st.columns([1.2, 1.2])

            with col_b1:
                if st.button("✅ Confirmar Cambio", key=f"btn_confirm_mt_{msg_idx}", type="primary", use_container_width=True):
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
                            f"🎉 **¡Listo! Solicitud registrada con éxito.**\n\n"
                            f"• **Orden:** `{resultado_orden['orden_id']}`\n"
                            f"• **Nuevo Plan:** **{resultado_orden['nuevo_plan']}**\n"
                            f"• **Tarifa:** `S/ {resultado_orden['precio_nuevo']:.2f}/mes` (Ahorro de S/ {resultado_orden['ahorro_mensual']:.2f}/mes)\n"
                            f"• **Vigencia:** `{resultado_orden['fecha_vigencia']}`."
                        ),
                        metadata={"type": "CONFIRMACION_UPGRADE", "orden": resultado_orden}
                    )
                    st.rerun()

            with col_b2:
                if st.button("❌ Cancelar", key=f"btn_cancel_mt_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    add_chat_message("user", "Prefiero mantener mi plan actual.")
                    add_chat_message("assistant", "Entendido. Mantendremos tu plan actual sin ningún cambio.")
                    st.rerun()
        else:
            st.caption("✅ *Operación gestionada.*")

    # 3. Botones de Acción Sugerida (Sutiles y minimalistas)
    elif not is_executed and not is_upgrade_action:
        col_act1, col_act2, col_act3 = st.columns(3)
        
        with col_act1:
            if st.button("💳 Pagar ahora", key=f"btn_pagar_s_{msg_idx}", use_container_width=True):
                st.session_state[action_executed_key] = True
                add_chat_message("user", "Deseo realizar el pago de mi recibo.")
                add_chat_message(
                    "assistant",
                    f"💳 **Pasarela de Pago Movistar:** Redirigiendo a pasarela bancaria para el abono de `S/ {client_context.get('recibo_actual', 119.90):.2f}`."
                )
                st.rerun()

        with col_act2:
            if st.button("🚀 Cambiar de Plan", key=f"btn_cambiar_s_{msg_idx}", use_container_width=True):
                st.session_state[action_executed_key] = True
                add_chat_message("user", "Quiero evaluar planes y opciones de ahorro.")
                nbo = generar_next_best_offer(cid)
                of = nbo.get("oferta_recomendada", {})
                add_chat_message(
                    "assistant",
                    f"Te propongo unirte a **{of.get('nombre_oferta', 'Movistar Total')}** por **S/ {of.get('precio_promocional', 110.40):.2f}/mes** para unificar y ahorrar más del 20% mensual.",
                    metadata={"action_payload": {"action": "SHOW_UPGRADE_CARD", "nbo": nbo}}
                )
                st.rerun()

        with col_act3:
            if st.button("👨‍💼 Asesor Humano", key=f"btn_asesor_s_{msg_idx}", use_container_width=True):
                st.session_state[action_executed_key] = True
                ticket = escalar_a_humano(
                    client_id=cid,
                    chat_history=st.session_state.get("chat_history", []),
                    motivo_detectado="Cliente solicita atención con asesor humano"
                )
                add_chat_message("user", "Deseo comunicarme con un asesor.")
                add_chat_message(
                    "assistant",
                    f"🔔 **He transferido tu caso a un asesor.** Ticket de atención: **`{ticket['ticket_id']}`**."
                )
                st.rerun()
