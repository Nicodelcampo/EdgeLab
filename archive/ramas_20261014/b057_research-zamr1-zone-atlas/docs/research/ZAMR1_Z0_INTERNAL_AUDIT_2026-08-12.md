# ZAMR-1 — auditoría interna Z0 (2026-08-12)

## Dictamen

`Z0_KAGGLE_ENVIRONMENT_PASS_WITH_HARDENING`

Kaggle reprodujo el fixture sintético: 8 hashes, 13 checks estructurales, 20 sesiones, 120 eventos, 120 zonas y seis frames; no se accedió a outcomes, P&L ni holdout.

## Defectos encontrados después del PASS

1. El layout actual de Kaggle anida datasets bajo `/kaggle/input/datasets/<owner>/<slug>`; el descubrimiento original sólo inspeccionaba un nivel.
2. La enmienda rápida del Notebook quedó minificada y perdió legibilidad/auditabilidad.
3. Faltaban tests explícitos de transporte: CSV debía ser aceptado sólo en Z0 y rechazado en Z1.
4. El repositorio no contiene evidencia suficiente para decidir licencia/proveedor de los ticks reales.

## Correcciones

- descubrimiento recursivo con unicidad estricta;
- carga aislada del validador incluido en el bundle;
- verificación de archivos, hashes y schemas antes de leer tablas;
- CSV exclusivamente para `Z0_SYNTHETIC_ENVIRONMENT`;
- Parquet obligatorio para datasets reales o derivados;
- tests de layout anidado, ambigüedad, transporte y path traversal;
- registro M0 fail-closed en `specs/zamr1_license_decision_v0.json`.

## Estado de gates

- Z0 entorno/contrato sintético: PASS.
- M0 licencia/privacidad: BLOCKED — faltan proveedor, producto y términos aplicables.
- M1 paridad real: NOT RUN.
- M2 recursos del constructor real: NOT RUN.

## Autorización vigente

Se permite seguir desarrollando contratos, validadores, builders y fixtures sintéticos. No se permite subir ticks reales ni derivados reales a Kaggle hasta que M0 tenga evidencia y decisión explícita. No se abren outcomes, P&L ni holdout.
