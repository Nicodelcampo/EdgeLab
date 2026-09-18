from pathlib import Path

p = Path('tools/paridad_hftzones_nq_v2.py')
s = p.read_text(encoding='utf-8')
s = s.replace(
'''    # Verificación fail-closed de procedencia de esquema: termination_reason debe ser NOT NULL
    # Si notnull == 0, fue agregado a posteriori vía ALTER TABLE (backfill Python).
''',
'''    # Elegibilidad de esquema: NOT NULL bloquea el backfill histórico nullable.
    # No demuestra procedencia nativa; hace falta congelar el SQLite antes de Python.
''')
s = s.replace(
'''        return False, "Columna termination_reason es NULLABLE (indica ALTER TABLE / backfill Python). Requiere creación nativa NT8 con TEXT NOT NULL."
''',
'''        return False, "termination_reason es NULLABLE: esquema no elegible para replay fresco (compatible con backfill Python); requiere TEXT NOT NULL desde la creación."
''')
s = s.replace(
'''    status = "PASS_CERTIFIED_FULL_FIELD_PARITY_NATIVE_NT8_38_FIELDS" if is_pass else "FAIL_V2_DISCREPANCY"
''',
'''    # Igualdad exacta no demuestra procedencia. Abstenerse hasta verificar el
    # hash físico y el manifiesto de preservación del replay fresco.
    status = ("PASS_EXACT_38_FIELDS_AWAITING_NATIVE_NT8_PROVENANCE"
              if is_pass else "FAIL_V2_DISCREPANCY")
''')
s = s.replace(
'''        "native_nt8_termination": True,
''',
'''        "native_nt8_termination": False,
        "certification_blocker": "fresh NT8 SQLite hash/preservation manifest not verified by comparator",
''')
p.write_text(s, encoding='utf-8')

p = Path('tests/bridge/test_paridad_hftzones_v2.py')
s = p.read_text(encoding='utf-8')
s = s.replace(
'''    assert res["status"] == "PASS_CERTIFIED_FULL_FIELD_PARITY_NATIVE_NT8_38_FIELDS"
''',
'''    assert res["status"] == "PASS_EXACT_38_FIELDS_AWAITING_NATIVE_NT8_PROVENANCE"
    assert res["native_nt8_termination"] is False
    assert "manifest" in res["certification_blocker"]
''')
p.write_text(s, encoding='utf-8')
