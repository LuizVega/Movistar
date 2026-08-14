"""
test_nbo_engine.py - Suite de Pruebas Automatizadas para el Motor Next Best Offer (nbo_engine.py)
"""

import json
from database import get_connection
from nbo_engine import generar_next_best_offer, main


def run_nbo_tests():
    print("============================================================")
    print("SUITE DE PRUEBAS: nbo_engine.py (Desafío 2 - Next Best Offer)")
    print("============================================================")

    conn = get_connection()
    cur = conn.cursor()

    # 1. Caso Principal: Cliente Elegible para MT
    cur.execute("SELECT cliente_id FROM clientes WHERE elegible_mt = 1 AND es_movistar_total = 0 LIMIT 1;")
    c_mt = cur.fetchone()["cliente_id"]

    print(f"\n1. Test Cliente Elegible para MT (ID={c_mt}):")
    res1 = generar_next_best_offer(c_mt, conn)
    print(json.dumps(res1, ensure_ascii=False, indent=2))
    assert res1["encontrado"] is True
    assert res1["es_elegible_mt"] is True
    assert res1["es_movistar_total_actual"] is False
    assert res1["estrategia_nbo"] == "BLINDAJE_CONVERGENTE_MOVISTAR_TOTAL"
    assert res1["oferta_recomendada"]["tipo_oferta"] == "MOVISTAR_TOTAL"
    assert "ahorro_mensual_soles" in res1["beneficio_economico"]
    assert "ahorro_porcentaje" in res1["beneficio_economico"]
    assert res1["beneficio_economico"]["ahorro_mensual_soles"] > 0
    assert 0.0 < res1["probabilidad_aceptacion"] <= 1.0
    assert "canal_mas_usado" in res1
    assert len(res1["motivos_recomendacion"]) >= 3
    print("   [PASS] Prueba 1 OK: Cliente elegible MT con cálculo de ahorro y canal.")

    # 2. Caso de Borde: Cliente Sin Historial de Facturación (monto_facturado_prom = 0.0)
    cur.execute("SELECT cliente_id FROM clientes WHERE elegible_mt = 1 AND es_movistar_total = 0 LIMIT 1;")
    c_null = cur.fetchone()["cliente_id"]
    
    # Guardar monto anterior
    cur.execute("SELECT monto_facturado_prom FROM clientes WHERE cliente_id = ?;", (c_null,))
    monto_ant = cur.fetchone()["monto_facturado_prom"]
    
    # Actualizar temporalmente a 0.0 para simular cliente sin historial previo
    cur.execute("UPDATE clientes SET monto_facturado_prom = 0.0 WHERE cliente_id = ?;", (c_null,))
    conn.commit()

    print(f"\n2. Test Manejo de Excepciones: Cliente sin historial (monto = 0.0, ID={c_null}):")
    res2 = generar_next_best_offer(c_null, conn)
    print(json.dumps(res2, ensure_ascii=False, indent=2))
    assert res2["encontrado"] is True
    assert res2["es_elegible_mt"] is True
    assert res2["beneficio_economico"]["ahorro_mensual_soles"] > 0
    assert any("sin historial previo" in m.lower() for m in res2["motivos_recomendacion"])
    print("   [PASS] Prueba 2 OK: Manejo de valores sin historial y cálculo estimado.")

    # Restaurar valor
    cur.execute("UPDATE clientes SET monto_facturado_prom = ? WHERE cliente_id = ?;", (monto_ant, c_null))
    conn.commit()

    # 3. Caso: Cliente que ya es Movistar Total (es_movistar_total = 1)
    cur.execute("SELECT cliente_id FROM clientes WHERE es_movistar_total = 1 LIMIT 1;")
    c_already_mt = cur.fetchone()["cliente_id"]

    print(f"\n3. Test Cliente ya Convergente (ID={c_already_mt}):")
    res3 = generar_next_best_offer(c_already_mt, conn)
    print(json.dumps(res3, ensure_ascii=False, indent=2))
    assert res3["encontrado"] is True
    assert res3["es_movistar_total_actual"] is True
    assert res3["estrategia_nbo"] == "FIDELIZACION_UPGRADE_MOVISTAR_TOTAL"
    print("   [PASS] Prueba 3 OK: Estrategia de Upgrade / Fidelización.")

    # 4. Caso: Cliente No Elegible para MT (elegible_mt = 0, es_movistar_total = 0)
    cur.execute("SELECT cliente_id FROM clientes WHERE elegible_mt = 0 AND es_movistar_total = 0 LIMIT 1;")
    c_not_mt = cur.fetchone()["cliente_id"]

    print(f"\n4. Test Cliente No Elegible MT (ID={c_not_mt}):")
    res4 = generar_next_best_offer(c_not_mt, conn)
    print(json.dumps(res4, ensure_ascii=False, indent=2))
    assert res4["encontrado"] is True
    assert res4["es_elegible_mt"] is False
    assert res4["estrategia_nbo"] == "OPTIMIZACION_MONOPRODUCTO"
    print("   [PASS] Prueba 4 OK: Estrategia Monoproducto.")

    # 5. Caso: Cliente Inexistente
    print("\n5. Test Cliente Inexistente (ID=9999999):")
    res5 = generar_next_best_offer(9999999, conn)
    print(json.dumps(res5, ensure_ascii=False, indent=2))
    assert res5["encontrado"] is False
    print("   [PASS] Prueba 5 OK: Cliente no encontrado.")

    # 6. Wrapper Dify / API main()
    print("\n6. Test main() Dify interface:")
    dify_out = main(c_mt)
    assert "resultado" in dify_out and "data" in dify_out
    assert isinstance(dify_out["resultado"], str)
    print("   [PASS] Prueba 6 OK: Interfaz Dify/API funcional.")

    conn.close()
    print("\n============================================================")
    print(">>> TODAS LAS PRUEBAS DE NBO ENGINE PASARON CON ÉXITO <<<")
    print("============================================================")


if __name__ == "__main__":
    run_nbo_tests()
