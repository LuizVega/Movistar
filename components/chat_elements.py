"""
components/chat_elements.py - Componentes UI de Yara AI Billing Copilot (Diseño Oficial Stitch)
Renderiza tarjetas Bento de desglose de facturación, marcadores de análisis (Consultar -> Comprender -> Explicar),
tarjetas de decisión de upgrade/fraccionamiento y modales de confirmación interactivos.
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


def render_analysis_markers():
    """Renderiza la barra de estado de razonamiento de Yara AI (Stitch Design)."""
    st.markdown("""
    <div style="display: flex; justify-content: center; margin: 10px 0 16px 0;">
        <div style="display: inline-flex; background: #f5f3f3; border-radius: 9999px; border: 1px solid #bec7d3; padding: 4px 6px; gap: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="display: flex; items-center; gap: 6px; padding: 4px 12px; border-radius: 9999px; background: #e3e2e2; font-size: 11px; font-weight: 700; color: #1b1c1c;">
                <span style="color: #00639c;">✓</span> Consultar
            </div>
            <div style="display: flex; items-center; gap: 6px; padding: 4px 12px; border-radius: 9999px; background: #e3e2e2; font-size: 11px; font-weight: 700; color: #1b1c1c;">
                <span style="color: #00639c;">✓</span> Comprender
            </div>
            <div style="display: flex; items-center; gap: 6px; padding: 4px 12px; border-radius: 9999px; background: #019df4; font-size: 11px; font-weight: 700; color: #ffffff;">
                <span>⟳</span> Explicar
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_bento_billing_card(cliente_context: Dict[str, Any], diff_data: Optional[Dict[str, Any]] = None):
    """Renderiza la tarjeta Bento de Desglose de Facturación según el diseño de Stitch."""
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
    <div style="background: #ffffff; border-radius: 14px; border: 1px solid #bec7d3; box-shadow: 0 4px 12px rgba(0,0,0,0.05); overflow: hidden; width: 100%; max-width: 540px; margin: 12px 0;">
        <div style="background: #f5f3f3; padding: 12px 16px; border-bottom: 1px solid #bec7d3; display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 15px; font-weight: 700; color: #00639c; display: flex; align-items: center; gap: 6px;">
                📑 Desglose de Facturación
            </div>
            <span style="background: #ffdad6; color: #93000a; font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 9999px; border: 1px solid rgba(186,26,26,0.2);">
                ▲ {signo}S/ {delta:.2f}
            </span>
        </div>
        <div style="padding: 16px 20px; display: flex; flex-col; gap: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1px solid #e3e2e2; padding-bottom: 12px;">
                <div>
                    <div style="font-size: 11px; font-weight: 700; color: #3f4852; text-transform: uppercase;">Mes Anterior (Junio)</div>
                    <div style="font-size: 20px; font-weight: 700; color: #1b1c1c;">S/ {recibo_ant:.2f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; font-weight: 700; color: #3f4852; text-transform: uppercase;">Mes Actual (Julio)</div>
                    <div style="font-size: 22px; font-weight: 800; color: #ba1a1a;">S/ {recibo_act:.2f}</div>
                </div>
            </div>
            <div style="background: #ffffff; padding: 10px 14px; border-radius: 8px; border: 1px solid #e3e2e2; display: flex; gap: 8px; align-items: flex-start;">
                <span style="color: #00639c; font-size: 16px;">ℹ️</span>
                <span style="font-size: 13px; color: #3f4852; line-height: 1.4;">
                    El cargo adicional corresponde a: <strong>{motivo}</strong> (+S/ {delta:.2f}).
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_chat_action_elements(msg: Dict[str, Any], msg_idx: int, client_context: Dict[str, Any]):
    """
    Renderiza los componentes interactivos de decisión de Yara AI:
    - Tarjeta Bento de Desglose de Facturación
    - Botones de acción sugeridos (Pagar ahora, Cambiar de Plan, Presentar Reclamo)
    - Modal de Confirmación de Plan / Upgrade Movistar Total
    """
    metadata = msg.get("metadata", {}) or {}
    action_payload = metadata.get("action_payload") or {}
    content_lower = msg.get("content", "").lower()
    cid = str(client_context.get("id") or "CLI001").strip().upper()

    action_executed_key = f"action_executed_{msg_idx}"
    is_executed = st.session_state.get(action_executed_key, False)

    # 1. Si el mensaje habla de la variación o desglose, renderizar Bento Card de Facturación
    if any(k in content_lower for k in ["desglose", "variación", "variacion", "subió", "subio", "aumento", "recibo", "prorrateo", "repetidor"]):
        render_bento_billing_card(client_context)

    # =========================================================================
    # ACCIÓN: PROPUESTA DE UPGRADE A MOVISTAR TOTAL (Modal / Card Stitch)
    # =========================================================================
    is_upgrade_action = (
        action_payload.get("action") in ["SHOW_UPGRADE_CARD", "UPGRADE_MOVISTAR_TOTAL"] or
        ("movistar total" in content_lower and ("elegible" in content_lower or "ahorro real" in content_lower or "plan propuesto" in content_lower or "plan recomendado" in content_lower or "migrar" in content_lower))
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
        ahorro_pct = ben.get("ahorro_porcentaje", 21.0)
        ahorro_anio = ben.get("ahorro_anual_estimado_soles", 352.80)

        # Modal / Card de Confirmación estilo Stitch (Screen 6a45aae93de2474f8dbf88d9614f03b9)
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #bec7d3; border-radius: 16px; padding: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); max-width: 520px; margin: 12px 0;">
            <div style="display: flex; align-items: center; gap: 8px; color: #00639c; margin-bottom: 8px;">
                <span style="font-size: 20px;">⭐</span>
                <span style="font-size: 16px; font-weight: 800;">Confirmar Cambio de Plan</span>
            </div>
            <p style="font-size: 14px; color: #3f4852; line-height: 1.5; margin: 0 0 12px 0;">
                Estás por cambiar al plan <strong style="color: #1b1c1c;">{plan_nombre}</strong> ({velocidad} Mbps + {gigas} GB) por <strong style="color: #00639c; font-size: 16px;">S/ {precio_promo:.2f} mensuales</strong> (Ahorro de S/ {ahorro_mes:.2f}/mes).
            </p>
        </div>
        """, unsafe_allow_html=True)

        if not is_executed:
            col_b1, col_b2, col_b3 = st.columns([1.5, 1.2, 1.2])

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
                            f"🎉 **¡Listo! He procesado tu solicitud con éxito.**\n\n"
                            f"• **Código de Solicitud:** **`{resultado_orden['orden_id']}`**\n"
                            f"• **Nuevo Plan:** **{resultado_orden['nuevo_plan']}**\n"
                            f"• **Tarifa Mensual Promocional:** `S/ {resultado_orden['precio_nuevo']:.2f} / mes`\n"
                            f"• **Ahorro Estimado:** `S/ {resultado_orden['ahorro_mensual']:.2f} / mes` (S/ {resultado_orden['ahorro_anual']:.2f} al año)\n"
                            f"• **Inicio de Vigencia:** **`{resultado_orden['fecha_vigencia']}`**\n\n"
                            f"Tu nuevo plan **Movistar Total** estará activo a partir de tu próximo ciclo de facturación sin costos ocultos."
                        ),
                        metadata={"type": "CONFIRMACION_UPGRADE", "orden": resultado_orden}
                    )
                    st.rerun()

            with col_b2:
                if st.button("❌ Cancelar", key=f"btn_cancel_mt_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    add_chat_message("user", "Prefiero mantener mi plan actual.")
                    add_chat_message("assistant", "Entendido perfectamente. Mantendremos tu plan actual sin ningún cambio.")
                    st.rerun()

            with col_b3:
                if st.button("👨‍💼 Asesor", key=f"btn_human_mt_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    ticket = escalar_a_humano(
                        client_id=cid,
                        chat_history=st.session_state.get("chat_history", []),
                        motivo_detectado=f"Cliente solicita asesor para evaluar propuesta de {plan_nombre}"
                    )
                    add_chat_message("assistant", f"🔔 **He transferido tu caso a un asesor.** Ticket de atención: **`{ticket['ticket_id']}`**.")
                    st.rerun()
        else:
            st.caption("✅ *Operación gestionada.*")

    # =========================================================================
    # BOTONES DE ACCIÓN RÁPIDA ESTILO STITCH (Pagar Ahora / Cambiar Plan / Reclamo)
    # =========================================================================
    elif not is_executed and not is_upgrade_action:
        st.markdown("<div style='font-size: 12px; font-weight: 700; color: #6f7883; margin: 8px 0 4px 0; text-transform: uppercase;'>Acciones Sugeridas</div>", unsafe_allow_html=True)
        col_act1, col_act2, col_act3 = st.columns(3)
        
        with col_act1:
            if st.button("💳 Pagar ahora", key=f"btn_pagar_stitch_{msg_idx}", use_container_width=True):
                st.session_state[action_executed_key] = True
                add_chat_message("user", "Deseo realizar el pago de mi recibo.")
                add_chat_message(
                    "assistant",
                    f"💳 **Pasarela de Pago Seguro Movistar**\n\n"
                    f"• **Monto a pagar:** `S/ {client_context.get('recibo_actual', 119.90):.2f}`\n"
                    f"• **Estado:** Redirigiendo a pasarela bancaria protegida (Visa / Mastercard / Yape / Plin)..."
                )
                st.rerun()

        with col_act2:
            if st.button("🚀 Cambiar de Plan", key=f"btn_cambiar_stitch_{msg_idx}", use_container_width=True):
                st.session_state[action_executed_key] = True
                add_chat_message("user", "Quiero evaluar planes y opciones de ahorro.")
                nbo = generar_next_best_offer(cid)
                of = nbo.get("oferta_recomendada", {})
                add_chat_message(
                    "assistant",
                    f"¡Excelente decisión! Te propongo unirte a **{of.get('nombre_oferta', 'Movistar Total')}** por **S/ {of.get('precio_promocional', 110.40):.2f}/mes**, unificando tu fibra y móvil para ahorrar más del 20% mensual.",
                    metadata={"action_payload": {"action": "SHOW_UPGRADE_CARD", "nbo": nbo}}
                )
                st.rerun()

        with col_act3:
            if st.button("⚠️ Presentar Reclamo", key=f"btn_reclamo_stitch_{msg_idx}", use_container_width=True):
                st.session_state[action_executed_key] = True
                ticket = escalar_a_humano(
                    client_id=cid,
                    chat_history=st.session_state.get("chat_history", []),
                    motivo_detectado="Cliente solicita presentar reclamo formal de facturación",
                    prioridad="ALTA"
                )
                add_chat_message("user", "Deseo presentar un reclamo formal sobre mi facturación.")
                add_chat_message(
                    "assistant",
                    f"🚨 **He registrado tu reclamo y lo he derivado a un supervisor de atención.**\n\n"
                    f"• **Ticket de Reclamo Prioritario:** **`{ticket['ticket_id']}`**\n"
                    f"• **Canal:** `Atención Especializada Movistar`\n\n"
                    f"Un asesor senior revisará tu historial en detalle para darte solución."
                )
                st.rerun()
