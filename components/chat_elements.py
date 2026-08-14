"""
components/chat_elements.py - Componentes Interactivos de Decisión en el Chat (Yara AI)
Renderiza tarjetas visuales y botones de acción (Upgrade Movistar Total, Fraccionamiento, Asesor Humano)
directamente dentro de los mensajes de Yara AI en Streamlit.
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime
from state_manager import add_chat_message, CLIENTES_CATALOGO
from services.escalation_service import escalar_a_humano
from nbo_engine import generar_next_best_offer


def render_chat_action_elements(msg: Dict[str, Any], msg_idx: int, client_context: Dict[str, Any]):
    """
    Evalúa si un mensaje del asistente contiene metadatos de acción o menciones de oportunidades
    y renderiza tarjetas y botones de decisión interactivos dentro del flujo conversacional.
    """
    metadata = msg.get("metadata", {}) or {}
    action_payload = metadata.get("action_payload") or {}
    content_lower = msg.get("content", "").lower()
    cid = str(client_context.get("id") or "CLI001").strip().upper()

    # Si la acción ya fue ejecutada/respondida en este mensaje, no volver a mostrar los botones activos
    action_executed_key = f"action_executed_{msg_idx}"
    is_executed = st.session_state.get(action_executed_key, False)

    # =========================================================================
    # ACCIÓN 1: PROPUESTA DE UPGRADE A MOVISTAR TOTAL
    # =========================================================================
    is_upgrade_action = (
        action_payload.get("action") in ["SHOW_UPGRADE_CARD", "UPGRADE_MOVISTAR_TOTAL"] or
        ("movistar total" in content_lower and ("elegible" in content_lower or "ahorro real" in content_lower or "plan propuesto" in content_lower or "plan recomendado" in content_lower))
    )

    if is_upgrade_action:
        # Obtener datos de oferta NBO
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

        # 1. Tarjeta Resumen de la Propuesta
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0a2540 0%, #0d3b66 60%, #ff6a00 100%); border-radius: 14px; padding: 18px 20px; color: white; margin: 12px 0; box-shadow: 0 4px 15px rgba(10,37,64,0.15);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="background: #ff6a00; color: white; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 800; text-transform: uppercase;">
                    ⭐ PROPUESTA EXCLUSIVA NBO
                </span>
                <span style="font-size: 12px; color: #cbd5e1;">Ahorro: <strong>{ahorro_pct:.1f}% OFF</strong></span>
            </div>
            <div style="font-size: 18px; font-weight: 800; color: #ffffff;">{plan_nombre}</div>
            <div style="font-size: 13px; color: #e2e8f0; margin-top: 4px;">
                ⚡ <strong>{velocidad} Mbps Fibra Simétrica</strong> + 📱 <strong>{gigas} GB Full Móvil</strong> en un solo recibo
            </div>
            <div style="display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap;">
                <div style="background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: 8px;">
                    <span style="font-size: 10px; color: #cbd5e1; text-transform: uppercase;">Precio Promocional</span>
                    <div style="font-size: 16px; font-weight: 900; color: #ffffff;">S/ {precio_promo:.2f} / mes</div>
                </div>
                <div style="background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: 8px;">
                    <span style="font-size: 10px; color: #cbd5e1; text-transform: uppercase;">Ahorro Mensual</span>
                    <div style="font-size: 16px; font-weight: 800; color: #ffeb3b;">S/ {ahorro_mes:.2f}</div>
                </div>
                <div style="background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: 8px;">
                    <span style="font-size: 10px; color: #cbd5e1; text-transform: uppercase;">Ahorro Anual</span>
                    <div style="font-size: 16px; font-weight: 800; color: #ffffff;">S/ {ahorro_anio:.2f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not is_executed:
            # 2. Botones de Decisión Interactivos
            col_b1, col_b2, col_b3 = st.columns([1.6, 1.2, 1.2])

            with col_b1:
                if st.button("✅ Autorizar Upgrade a Movistar Total", key=f"btn_auth_mt_{msg_idx}", type="primary", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    if cid in CLIENTES_CATALOGO:
                        CLIENTES_CATALOGO[cid]["servicio"] = plan_nombre
                        CLIENTES_CATALOGO[cid]["recibo_actual"] = precio_promo
                        CLIENTES_CATALOGO[cid]["estado_linea"] = "Activa - Movistar Total"
                    
                    st.balloons()
                    # Mensaje formal de transacción autorizada
                    add_chat_message(
                        role="assistant",
                        content=(
                            f"🎉 **¡TRANSACCIÓN COMERCIAL AUTORIZADA CON ÉXITO!**\n\n"
                            f"Has confirmado tu migración a **{plan_nombre}**.\n\n"
                            f"• **Tarifa Promocional:** `S/ {precio_promo:.2f} / mes`\n"
                            f"• **Velocidad Fibra:** `{velocidad} Mbps Simétricos`\n"
                            f"• **Gigas Móviles:** `{gigas} GB Full`\n"
                            f"• **Ahorro Anual Estimado:** `S/ {ahorro_anio:.2f}`\n"
                            f"• **Código de Operación:** `OP-MT-{datetime.now().strftime('%Y%m%d%H%M')}`\n\n"
                            f"Tus beneficios han sido actualizados en el sistema. ¡Gracias por confiar en Movistar!"
                        ),
                        metadata={"type": "CONFIRMACION_UPGRADE"}
                    )
                    st.rerun()

            with col_b2:
                if st.button("❌ No, mantener mi plan actual", key=f"btn_cancel_mt_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    add_chat_message(
                        role="user",
                        content="Prefiero mantener mi plan actual por el momento."
                    )
                    add_chat_message(
                        role="assistant",
                        content="Entendido perfectamente. Mantendremos tu plan actual sin ningún cambio. Si en el futuro deseas unificar tus servicios para ahorrar, con gusto te ayudaré."
                    )
                    st.rerun()

            with col_b3:
                if st.button("👨‍💼 Hablar con asesor", key=f"btn_human_mt_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    ticket = escalar_a_humano(
                        client_id=cid,
                        chat_history=st.session_state.get("chat_history", []),
                        motivo_detectado=f"Cliente solicita asesor humano para evaluar propuesta de {plan_nombre}"
                    )
                    t_id = ticket["ticket_id"]
                    add_chat_message(
                        role="assistant",
                        content=(
                            f"🔔 **He transferido tu caso a uno de nuestros asesores comerciales.**\n\n"
                            f"Se ha generado el ticket prioritario **`{t_id}`**. Un asesor te contactará para resolver tus dudas sobre la oferta de {plan_nombre}."
                        )
                    )
                    st.rerun()
        else:
            st.caption("✅ *Acción gestionada para esta propuesta.*")

    # =========================================================================
    # ACCIÓN 2: FRACCIONAMIENTO DE DEUDA EN CUOTAS
    # =========================================================================
    is_fracc_action = (
        action_payload.get("action") in ["SHOW_INSTALLMENT_MODAL", "SHOW_INSTALLMENT_OPTION", "FRACCIONAMIENTO_DEUDA"] or
        ("fraccionamiento" in content_lower and "cuotas fijas" in content_lower)
    )

    if is_fracc_action and not is_upgrade_action:
        total_recibo = client_context.get("recibo_actual", 119.90)

        st.markdown(f"""
        <div style="background: #f0f7ff; border: 1px solid #bae6fd; border-left: 4px solid #005cff; border-radius: 12px; padding: 14px 18px; margin: 10px 0;">
            <strong style="color: #0369a1;">💳 ALIVIO FINANCIERO: Fraccionamiento de Recibo (0% Intereses)</strong>
            <div style="font-size: 13px; color: #334155; margin-top: 4px;">
                Monto total a fraccionar: <strong>S/ {total_recibo:.2f}</strong> (TCEA 0.0%). Selecciona una opción:
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not is_executed:
            f_col1, f_col2, f_col3, f_col4 = st.columns([1.1, 1.1, 1.1, 1.1])
            
            with f_col1:
                if st.button(f"3 Cuotas (S/ {total_recibo/3:.2f}/m)", key=f"btn_3c_chat_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    add_chat_message(
                        role="assistant",
                        content=(
                            f"✅ **¡FRACCIONAMIENTO APROBADO EN 3 CUOTAS!**\n\n"
                            f"Has diferido tu recibo de **S/ {total_recibo:.2f}** en **3 cuotas fijas de S/ {(total_recibo/3):.2f} / mes** sin intereses a partir de Agosto 2026.\n"
                            f"• **N° Operación:** `FRACC-3M-{datetime.now().strftime('%Y%m%d%H%M')}`"
                        )
                    )
                    st.rerun()

            with f_col2:
                if st.button(f"6 Cuotas (S/ {total_recibo/6:.2f}/m)", key=f"btn_6c_chat_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    add_chat_message(
                        role="assistant",
                        content=(
                            f"✅ **¡FRACCIONAMIENTO APROBADO EN 6 CUOTAS!**\n\n"
                            f"Has diferido tu recibo de **S/ {total_recibo:.2f}** en **6 cuotas fijas de S/ {(total_recibo/6):.2f} / mes** sin intereses a partir de Agosto 2026.\n"
                            f"• **N° Operación:** `FRACC-6M-{datetime.now().strftime('%Y%m%d%H%M')}`"
                        )
                    )
                    st.rerun()

            with f_col3:
                if st.button(f"12 Cuotas (S/ {total_recibo/12:.2f}/m)", key=f"btn_12c_chat_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    add_chat_message(
                        role="assistant",
                        content=(
                            f"✅ **¡FRACCIONAMIENTO APROBADO EN 12 CUOTAS!**\n\n"
                            f"Has diferido tu recibo de **S/ {total_recibo:.2f}** en **12 cuotas fijas de S/ {(total_recibo/12):.2f} / mes** sin intereses a partir de Agosto 2026.\n"
                            f"• **N° Operación:** `FRACC-12M-{datetime.now().strftime('%Y%m%d%H%M')}`"
                        )
                    )
                    st.rerun()

            with f_col4:
                if st.button("👨‍💼 Asesor", key=f"btn_human_fracc_{msg_idx}", use_container_width=True):
                    st.session_state[action_executed_key] = True
                    ticket = escalar_a_humano(
                        client_id=cid,
                        chat_history=st.session_state.get("chat_history", []),
                        motivo_detectado=f"Cliente solicita asesor humano para evaluar plan de fraccionamiento de S/ {total_recibo:.2f}"
                    )
                    t_id = ticket["ticket_id"]
                    add_chat_message(
                        role="assistant",
                        content=f"🔔 **He derivado tu caso a un asesor.** Tu ticket de atención es **`{t_id}`**."
                    )
                    st.rerun()
        else:
            st.caption("✅ *Fraccionamiento gestionado.*")
