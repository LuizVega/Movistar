"""
nbo_engine.py - Motor de Recomendación Next Best Offer (NBO)
Desafío 2: Personalización Comercial Inteligente (Movistar)

Este módulo implementa:
1. Evaluación determinista de clientes para priorizar "Movistar Total" (MT) como palanca de blindaje.
2. Identificación de clientes con `elegible_mt == True` y `es_movistar_total == False`.
3. Selección de la variante óptima de Movistar Total del catálogo de ofertas.
4. Cálculo del beneficio económico real (ahorro financiero en Soles y porcentaje de hasta ~50% vs. gasto fragmentado).
5. Extracción del canal idóneo de contacto a partir del historial y perfil del cliente.
6. Estimación de probabilidad simulada de aceptación mediante propensión analítica.
7. Manejo robusto de excepciones (clientes sin historial de facturación o valores nulos).
"""

import json
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from database import get_connection, get_cliente_by_id, get_historial_por_cliente, DB_PATH


# =========================================================
# Constantes de Negocio y Precios de Referencia Fragmentados
# =========================================================

COSTO_ESTANDAR_LINEA_MOVIL = 49.90  # Plan Móvil Ilimitado estándar individual
COSTO_ESTANDAR_INTERNET_HOGAR = 89.90  # Fibra 200 Mbps estándar individual
COSTO_ESTANDAR_TV_HD = 50.00  # Decodificador y canales HD estándar individual


def estimar_gasto_fragmentado(cliente: Dict[str, Any], oferta_mt_propuesta: Dict[str, Any]) -> float:
    """
    Calcula el costo total que el cliente pagaría adquiriendo los servicios por separado
    (internet fijo hogar + líneas móviles + TV) de forma fragmentada.
    """
    monto_prom = cliente.get("monto_facturado_prom")
    lineas_moviles = cliente.get("lineas_moviles_activas") or 1
    
    # Líneas requeridas por la oferta de Movistar Total seleccionada
    gigas_mt = oferta_mt_propuesta.get("gigas_datos") or 65
    lineas_incluidas = 1
    if "2 Líneas" in oferta_mt_propuesta.get("nombre_oferta", ""):
        lineas_incluidas = 2
    elif "3 Líneas" in oferta_mt_propuesta.get("nombre_oferta", ""):
        lineas_incluidas = 3

    # Costo por separado de la fibra según velocidad
    vel = oferta_mt_propuesta.get("velocidad_mbps") or 200
    if vel >= 1000:
        costo_fijo_sep = 199.90
    elif vel >= 500:
        costo_fijo_sep = 139.90
    elif vel >= 300:
        costo_fijo_sep = 109.90
    else:
        costo_fijo_sep = 89.90

    # Costo por separado de las líneas móviles
    costo_movil_sep = lineas_incluidas * COSTO_ESTANDAR_LINEA_MOVIL
    
    # Costo TV si la oferta es Trío
    costo_tv_sep = COSTO_ESTANDAR_TV_HD if "Trío" in oferta_mt_propuesta.get("nombre_oferta", "") else 0.0

    costo_fragmentado_teorico = costo_fijo_sep + costo_movil_sep + costo_tv_sep

    # Si el cliente tiene un monto facturado promedio válido, usamos el máximo para reflejar
    # el consumo real o el costo equivalente por separado
    if monto_prom is not None and float(monto_prom) > 0:
        monto_float = float(monto_prom)
        # Si el cliente ya gasta en servicios separados pero aún no tiene MT
        if monto_float > costo_fragmentado_teorico * 0.7:
            return round(max(monto_float * 1.25, costo_fragmentado_teorico), 2)
        else:
            return round(costo_fragmentado_teorico, 2)
    else:
        return round(costo_fragmentado_teorico, 2)


def seleccionar_variante_optima_mt(cliente: Dict[str, Any], ofertas_mt: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Selecciona la variante de Movistar Total más adecuada según:
    - Cantidad de líneas móviles del cliente
    - Nivel de facturación actual (monto_facturado_prom)
    - Tipo de cliente (Residencial, Pyme, Corporativo)
    """
    if not ofertas_mt:
        raise ValueError("No se encontraron ofertas de Movistar Total en el catálogo.")

    lineas = cliente.get("lineas_moviles_activas") or 1
    monto = float(cliente.get("monto_facturado_prom") or 80.0)
    tipo_c = (cliente.get("tipo_cliente") or "RESIDENCIAL").upper()

    # Filtro por tipo de necesidad
    if tipo_c in ("PYME", "CORPORATIVO") or monto >= 200.0 or lineas >= 3:
        # Perfil Alto / Negocio -> Trío 500M / 1000M o Dúo 500M con 3 líneas
        candidatas = [o for o in ofertas_mt if (o.get("velocidad_mbps") or 0) >= 500 or "3 Líneas" in o.get("nombre_oferta", "")]
    elif monto >= 120.0 or lineas == 2:
        # Perfil Medio -> Dúo 300M + 2 Líneas o Trío 300M
        candidatas = [o for o in ofertas_mt if "2 Líneas" in o.get("nombre_oferta", "") or (o.get("velocidad_mbps") == 300)]
    else:
        # Perfil Entrada -> Dúo 200M + 1 Línea
        candidatas = [o for o in ofertas_mt if "1 Línea" in o.get("nombre_oferta", "") or (o.get("velocidad_mbps") == 200)]

    if not candidatas:
        candidatas = ofertas_mt

    # Ordenar por mejor balance de precio promocional
    candidatas.sort(key=lambda x: float(x.get("precio_promocional", 999.0)))
    return candidatas[0]


def determinar_canal_contacto_optimo(cliente: Dict[str, Any], historial: List[Dict[str, Any]]) -> str:
    """
    Determina la vía de contacto más efectiva cruzando el canal con mayor tasa de aceptación
    en el historial de campañas y el canal preferido del cliente.
    """
    if historial:
        # Contar canales con respuesta positiva
        canales_exito: Dict[str, int] = {}
        canales_total: Dict[str, int] = {}
        for h in historial:
            canal = h.get("canal_contacto", "APP_MOVISTAR")
            canales_total[canal] = canales_total.get(canal, 0) + 1
            if h.get("acepto_oferta") == 1:
                canales_exito[canal] = canales_exito.get(canal, 0) + 1

        if canales_exito:
            # Seleccionar el canal con mayor cantidad de aceptaciones
            mejor_canal = max(canales_exito.items(), key=lambda x: x[1])[0]
            return mejor_canal

    # Fallback al canal preferido del cliente o por propensión digital
    canal_pref = cliente.get("canal_preferido")
    if canal_pref:
        return canal_pref

    score_digital = float(cliente.get("score_propension_digital") or 0.5)
    return "APP_MOVISTAR" if score_digital >= 0.5 else "CALL_CENTER"


def calcular_probabilidad_aceptacion(cliente: Dict[str, Any], ahorro_porcentaje: float, historial: List[Dict[str, Any]]) -> float:
    """
    Calcula una probabilidad simulada de aceptación basada en:
    - Score de propensión digital del cliente (peso 30%)
    - Antigüedad del cliente (fidelidad y confianza, peso 20%)
    - Magnitud del ahorro económico porcentual (peso 35%)
    - Tasa histórica de conversión en campañas (peso 15%)
    """
    score_digital = float(cliente.get("score_propension_digital") or 0.5)
    antiguedad = min(float(cliente.get("antiguedad_meses") or 12), 120.0) / 120.0  # Normalizado 0 a 1
    
    # Factor de ahorro (hasta 50% de ahorro -> factor 1.0)
    factor_ahorro = min(max(ahorro_porcentaje / 50.0, 0.1), 1.0)

    # Factor histórico
    if historial:
        tasa_hist = sum(1 for h in historial if h.get("acepto_oferta") == 1) / len(historial)
    else:
        tasa_hist = 0.35  # Tasa base esperada en telecomunicaciones

    prob = (
        0.30 * score_digital +
        0.20 * antiguedad +
        0.35 * factor_ahorro +
        0.15 * tasa_hist
    )

    # Ajuste de rango realista entre 0.15 y 0.95
    prob_final = max(min(prob, 0.95), 0.15)
    return round(prob_final, 2)


# =========================================================
# Servicio Principal de Next Best Offer (NBO)
# =========================================================

def generar_next_best_offer(cliente_id: int | str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """
    Evalúa y genera la Next Best Offer (NBO) para un cliente, priorizando 'Movistar Total' (MT)
    como palanca de blindaje para clientes convergentes potenciales.
    
    Parámetros:
    - cliente_id: Identificador numérico o alfanumérico del cliente.
    - conn: Conexión SQLite opcional.
    """
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    try:
        # 1. Recuperar información del cliente (soporta CLI001 -> 1000001 y 1000001 directo)
        s_cid = str(cliente_id).strip().upper()
        if s_cid.startswith("CLI") or s_cid.startswith("C"):
            try:
                num = int(s_cid.replace("CLI", "").replace("C", ""))
                cid_int = 1000000 + num if num < 1000 else num
            except ValueError:
                cid_int = cliente_id
        else:
            try:
                cid_int = int(cliente_id)
            except ValueError:
                cid_int = cliente_id


        cursor = conn.execute("""
            SELECT c.*, o.nombre_oferta AS nombre_oferta_actual, o.precio_promocional AS precio_oferta_actual
            FROM clientes c
            LEFT JOIN catalogo_ofertas o ON c.oferta_hogar_id = o.oferta_id
            WHERE c.cliente_id = ?
        """, (cid_int,))
        row = cursor.fetchone()

        if not row:
            return {
                "encontrado": False,
                "cliente_id": cliente_id,
                "mensaje": f"Cliente con ID {cliente_id} no encontrado en la base de datos."
            }

        cliente = dict(row)

        # 2. Recuperar historial de campañas
        historial = get_historial_por_cliente(cid_int, conn)

        # 3. Recuperar catálogo de ofertas
        cur_of = conn.execute("SELECT * FROM catalogo_ofertas WHERE activo = 1;")
        todas_ofertas = [dict(r) for r in cur_of.fetchall()]
        ofertas_mt = [o for o in todas_ofertas if o.get("tipo_oferta") == "MOVISTAR_TOTAL"]

        # 4. Manejo de excepciones en historial de facturación
        monto_facturado = cliente.get("monto_facturado_prom")
        sin_historial_monto = False
        if monto_facturado is None or float(monto_facturado) <= 0.0:
            sin_historial_monto = True
            # Imputar consumo estimado de entrada (S/ 79.90 base)
            cliente["monto_facturado_prom"] = 79.90

        es_elegible_mt = bool(cliente.get("elegible_mt") == 1)
        es_mt_actual = bool(cliente.get("es_movistar_total") == 1)

        # 5. Evaluación de Reglas de Negocio NBO
        if es_elegible_mt and not es_mt_actual:
            # ESTRATEGIA PRINCIPAL: BLINDAJE CONVERGENTE MOVISTAR TOTAL
            oferta_seleccionada = seleccionar_variante_optima_mt(cliente, ofertas_mt)
            
            # Cálculo del beneficio económico dinámico y numérico
            gasto_fragmentado = estimar_gasto_fragmentado(cliente, oferta_seleccionada)
            precio_mt_promo = float(oferta_seleccionada.get("precio_promocional", 110.40))
            precio_mt_regular = float(oferta_seleccionada.get("cargo_fijo", 139.90))


            ahorro_mensual = round(max(gasto_fragmentado - precio_mt_promo, 0.0), 2)
            ahorro_pct = round((ahorro_mensual / gasto_fragmentado) * 100.0, 1) if gasto_fragmentado > 0 else 0.0
            ahorro_anual = round(ahorro_mensual * 12, 2)

            # Canal y Propensión
            canal_optimo = determinar_canal_contacto_optimo(cliente, historial)
            prob_aceptacion = calcular_probabilidad_aceptacion(cliente, ahorro_pct, historial)

            # Motivos de recomendación estructurados
            motivos = [
                f"Cliente elegible para convergencia Movistar Total como palanca de blindaje.",
                f"Ahorro económico del {ahorro_pct}% (S/ {ahorro_mensual:.2f} al mes) respecto a su gasto actual de S/ {gasto_fragmentado:.2f}.",
                f"Unificación de recibo de internet fibra ({oferta_seleccionada.get('velocidad_mbps')} Mbps) + telefonía móvil ({oferta_seleccionada.get('gigas_datos')} GB).",
                f"Canal óptimo sugerido: {canal_optimo} basado en afinidad y respuesta del cliente."
            ]
            if sin_historial_monto:
                motivos.append("Nota: Perfil sin historial previo de facturación; se calculó el beneficio en base al consumo base estimado.")


            return {
                "encontrado": True,
                "cliente_id": cliente["cliente_id"],
                "es_elegible_mt": True,
                "es_movistar_total_actual": False,
                "estrategia_nbo": "BLINDAJE_CONVERGENTE_MOVISTAR_TOTAL",
                "oferta_recomendada": {
                    "oferta_id": oferta_seleccionada["oferta_id"],
                    "nombre_oferta": oferta_seleccionada["nombre_oferta"],
                    "tipo_oferta": oferta_seleccionada["tipo_oferta"],
                    "cargo_fijo_regular": precio_mt_regular,
                    "precio_promocional": precio_mt_promo,
                    "velocidad_mbps": oferta_seleccionada.get("velocidad_mbps"),
                    "gigas_datos": oferta_seleccionada.get("gigas_datos"),
                    "descripcion": oferta_seleccionada.get("descripcion")
                },
                "beneficio_economico": {
                    "gasto_actual_fragmentado_estimado": gasto_fragmentado,
                    "precio_nuevo_movistar_total": precio_mt_promo,
                    "ahorro_mensual_soles": ahorro_mensual,
                    "ahorro_porcentaje": ahorro_pct,
                    "ahorro_anual_estimado_soles": ahorro_anual
                },
                "probabilidad_aceptacion": prob_aceptacion,
                "canal_mas_usado": canal_optimo,
                "motivos_recomendacion": motivos
            }

        elif es_mt_actual:
            # ESTRATEGIA: UP-SELL / RETENCIÓN DE CLIENTE CONVERGENTE
            ofertas_upgrade = [o for o in todas_ofertas if o.get("tipo_oferta") in ("UPGRADE", "MOVISTAR_TOTAL") and (o.get("velocidad_mbps") or 0) > 300]
            oferta_up = ofertas_upgrade[0] if ofertas_upgrade else todas_ofertas[0]
            canal_optimo = determinar_canal_contacto_optimo(cliente, historial)

            return {
                "encontrado": True,
                "cliente_id": cliente["cliente_id"],
                "es_elegible_mt": False,
                "es_movistar_total_actual": True,
                "estrategia_nbo": "FIDELIZACION_UPGRADE_MOVISTAR_TOTAL",
                "oferta_recomendada": {
                    "oferta_id": oferta_up["oferta_id"],
                    "nombre_oferta": oferta_up["nombre_oferta"],
                    "tipo_oferta": oferta_up["tipo_oferta"],
                    "precio_promocional": oferta_up["precio_promocional"],
                    "velocidad_mbps": oferta_up.get("velocidad_mbps"),
                    "descripcion": oferta_up.get("descripcion")
                },
                "beneficio_economico": {
                    "gasto_actual_promedio": float(cliente.get("monto_facturado_prom") or 0.0),
                    "precio_upgrade": float(oferta_up["precio_promocional"]),
                    "ahorro_mensual_soles": 0.0,
                    "ahorro_porcentaje": 0.0,
                    "ahorro_anual_estimado_soles": 0.0
                },
                "probabilidad_aceptacion": round(float(cliente.get("score_propension_digital") or 0.6) * 0.9, 2),
                "canal_mas_usado": canal_optimo,
                "motivos_recomendacion": [
                    "El cliente ya cuenta con Movistar Total.",
                    "Se propone un Upgrade de velocidad o paquete de fidelización para retención."
                ]
            }

        else:
            # ESTRATEGIA: MEJORA MONOPRODUCTO (FIBRA / MÓVIL)
            ofertas_mono = [o for o in todas_ofertas if o.get("tipo_oferta") in ("FIBRA", "MOVIL", "DUO")]
            oferta_mono = ofertas_mono[0] if ofertas_mono else todas_ofertas[0]
            canal_optimo = determinar_canal_contacto_optimo(cliente, historial)

            return {
                "encontrado": True,
                "cliente_id": cliente["cliente_id"],
                "es_elegible_mt": False,
                "es_movistar_total_actual": False,
                "estrategia_nbo": "OPTIMIZACION_MONOPRODUCTO",
                "oferta_recomendada": {
                    "oferta_id": oferta_mono["oferta_id"],
                    "nombre_oferta": oferta_mono["nombre_oferta"],
                    "tipo_oferta": oferta_mono["tipo_oferta"],
                    "precio_promocional": oferta_mono["precio_promocional"],
                    "descripcion": oferta_mono.get("descripcion")
                },
                "beneficio_economico": {
                    "gasto_actual_promedio": float(cliente.get("monto_facturado_prom") or 0.0),
                    "precio_nuevo_plan": float(oferta_mono["precio_promocional"]),
                    "ahorro_mensual_soles": round(max(float(cliente.get("monto_facturado_prom") or 0.0) - float(oferta_mono["precio_promocional"]), 0.0), 2),
                    "ahorro_porcentaje": 10.0,
                    "ahorro_anual_estimado_soles": 0.0
                },
                "probabilidad_aceptacion": 0.45,
                "canal_mas_usado": canal_optimo,
                "motivos_recomendacion": [
                    "Cliente no elegible actualmente para paquete convergente Movistar Total.",
                    "Se ofrece optimización y mejora en su plan individual actual."
                ]
            }

    finally:
        if close_after:
            conn.close()


def main(cliente_id: int | str = 1000001) -> Dict[str, Any]:
    """
    Función de entrada para pruebas y consumo desde APIs / Dify / CLI.
    """
    resultado = generar_next_best_offer(cliente_id)
    return {
        "resultado": json.dumps(resultado, ensure_ascii=False, indent=2),
        "data": resultado
    }


if __name__ == "__main__":
    print("============================================================")
    print("DEMOSTRACIÓN Y PRUEBA TÉCNICA LOCAL: nbo_engine.py")
    print("============================================================")
    
    # Probar con cliente elegible para MT
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT cliente_id FROM clientes WHERE elegible_mt = 1 AND es_movistar_total = 0 LIMIT 1;")
    cliente_test_id = cur.fetchone()["cliente_id"]
    conn.close()
    
    print(f"\nConsultando NBO para cliente elegible para MT (ID={cliente_test_id}):")
    resp = generar_next_best_offer(cliente_test_id)
    print(json.dumps(resp, ensure_ascii=False, indent=2))
