"""
test_diff_engine.py - Suite de Pruebas Automatizadas para el Motor diff_engine.py
"""

import json
from diff_engine import auditar_variacion_recibo, main


def run_diff_tests():
    print("============================================================")
    print("SUITE DE PRUEBAS: diff_engine.py (YARA AI / Desafío 1)")
    print("============================================================")

    # 1. Prueba 1: Criterio de Aceptación CLI001 (Cargo Único Repetidor WiFi)
    print("\n1. Test CLI001 (2026-07): Instalación de Repetidor WiFi")
    res1 = auditar_variacion_recibo("CLI001", "2026-07")
    print(json.dumps(res1, ensure_ascii=False, indent=2))
    assert res1["encontrado"] is True
    assert res1["id_cliente"] == "CLI001"
    assert res1["periodo_consultado"] == "2026-07"
    assert res1["variacion"]["monto"] == 30.00
    assert res1["variacion"]["porcentaje"] == 33.37
    assert len(res1["conceptos_adicionales"]) == 1
    assert res1["conceptos_adicionales"][0]["concepto"] == "Instalación de repetidor WiFi"
    assert res1["conceptos_adicionales"][0]["monto"] == 30.00
    assert res1["conceptos_adicionales"][0]["tipo"] == "cargo_unico"
    print("   [PASS] Prueba 1 OK.")

    # 2. Prueba 2: CLI002 (Fin de Descuento Promocional)
    print("\n2. Test CLI002 (2026-07): Fin de Descuento Promocional")
    res2 = auditar_variacion_recibo("CLI002", "2026-07")
    print(json.dumps(res2, ensure_ascii=False, indent=2))
    assert res2["encontrado"] is True
    assert res2["variacion"]["monto"] == 20.00
    assert res2["variacion"]["porcentaje"] == 18.20
    assert any(c["tipo"] == "fin_descuento" for c in res2["conceptos_adicionales"])
    print("   [PASS] Prueba 2 OK.")

    # 3. Prueba 3: CLI003 (Sin Variación)
    print("\n3. Test CLI003 (2026-07): Sin Variación")
    res3 = auditar_variacion_recibo("CLI003", "2026-07")
    print(json.dumps(res3, ensure_ascii=False, indent=2))
    assert res3["encontrado"] is True
    assert res3["variacion"]["monto"] == 0.00
    assert res3["variacion"]["porcentaje"] == 0.00
    assert len(res3["conceptos_adicionales"]) == 0
    print("   [PASS] Prueba 3 OK.")

    # 4. Prueba 4: CLI004 (Prorrateo)
    print("\n4. Test CLI004 (2026-07): Prorrateo")
    res4 = auditar_variacion_recibo("CLI004", "2026-07")
    print(json.dumps(res4, ensure_ascii=False, indent=2))
    assert res4["encontrado"] is True
    assert res4["variacion"]["monto"] == 25.00
    assert res4["conceptos_adicionales"][0]["tipo"] == "prorrateo"
    print("   [PASS] Prueba 4 OK.")

    # 5. Prueba 5: CLI005 (Cuota Equipo ShEq)
    print("\n5. Test CLI005 (2026-07): Cuota Equipo Financiado ShEq")
    res5 = auditar_variacion_recibo("CLI005", "2026-07")
    print(json.dumps(res5, ensure_ascii=False, indent=2))
    assert res5["encontrado"] is True
    assert res5["variacion"]["monto"] == 35.00
    assert res5["conceptos_adicionales"][0]["tipo"] == "cuota_equipo"
    print("   [PASS] Prueba 5 OK.")

    # 6. Prueba 6: CLI006 (Cargo por Reconexión)
    print("\n6. Test CLI006 (2026-07): Cargo Reconexión Morosa")
    res6 = auditar_variacion_recibo("CLI006", "2026-07")
    print(json.dumps(res6, ensure_ascii=False, indent=2))
    assert res6["encontrado"] is True
    assert res6["variacion"]["monto"] == 10.50
    assert res6["conceptos_adicionales"][0]["tipo"] == "cargo_reconexion"
    print("   [PASS] Prueba 6 OK.")

    # 7. Prueba 7: CLI007 (Compra de Paquetes)
    print("\n7. Test CLI007 (2026-07): Compra de Paquetes")
    res7 = auditar_variacion_recibo("CLI007", "2026-07")
    assert res7["encontrado"] is True
    assert res7["variacion"]["monto"] == 20.00
    assert res7["conceptos_adicionales"][0]["tipo"] == "compra_paquetes"
    print("   [PASS] Prueba 7 OK.")

    # 8. Prueba 8: CLI008 (Nota de Crédito)
    print("\n8. Test CLI008 (2026-07): Nota de Crédito")
    res8 = auditar_variacion_recibo("CLI008", "2026-07")
    assert res8["encontrado"] is True
    assert res8["variacion"]["monto"] == -20.00
    assert res8["conceptos_adicionales"][0]["tipo"] == "nota_credito"
    print("   [PASS] Prueba 8 OK.")

    # 9. Prueba 9: CLI009 (Cambio de Plan)
    print("\n9. Test CLI009 (2026-07): Cambio de Plan")
    res9 = auditar_variacion_recibo("CLI009", "2026-07")
    assert res9["encontrado"] is True
    assert res9["variacion"]["monto"] == 30.00
    assert res9["conceptos_adicionales"][0]["tipo"] == "cambio_plan"
    print("   [PASS] Prueba 9 OK.")

    # 10. Prueba 10: Cliente Inexistente (CLI999)
    print("\n10. Test CLI999: Cliente No Encontrado")
    res10 = auditar_variacion_recibo("CLI999", "2026-07")
    assert res10["encontrado"] is False
    print("   [PASS] Prueba 10 OK.")

    # 11. Prueba 11: Interfaz Dify main()
    print("\n11. Test main() Dify interface")
    dify_out = main("CLI001", "2026-07")
    assert "resultado" in dify_out and "data" in dify_out
    assert isinstance(dify_out["resultado"], str)
    print("   [PASS] Prueba 11 OK.")

    print("\n============================================================")
    print(">>> TODAS LAS 11 PRUEBAS DE DIFF ENGINE PASARON CON ÉXITO <<<")
    print("============================================================")



if __name__ == "__main__":
    run_diff_tests()
