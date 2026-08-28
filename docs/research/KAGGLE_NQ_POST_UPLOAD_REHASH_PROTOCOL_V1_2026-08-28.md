# Protocolo de rehash post-upload — NQ pre-holdout

**Estado:** `READY_FOR_POST_UPLOAD_REHASH_NOT_RUN`  
**Dataset:** `nicolasbuttaro/edgelab-ticks-nq-preholdout`  
**Modo:** integridad únicamente, sin kernel científico

## Objetivo

Verificar los bytes realmente montados por Kaggle antes de congelar BigTrap2 V2. El verificador no ejecuta indicadores, lifecycle, first touch, MFE/MAE, P&L ni selección.

## Entrypoints

```text
notebooks/kaggle/20_nq_post_upload_rehash.py
tools/verify_kaggle_nq_post_upload.py
```

El notebook clona un commit exacto, hace checkout detached y ejecuta sólo el verificador.

## Configuración Kaggle

Adjuntar únicamente el dataset privado:

```text
nicolasbuttaro/edgelab-ticks-nq-preholdout
```

Definir:

```text
EDGELAB_EXPECTED_COMMIT = <commit exacto que contiene el verificador>
EDGELAB_DATA_DIR        = /kaggle/input/edgelab-ticks-nq-preholdout
```

No definir tokens de campaña y no usar `EDGELAB_EXECUTE=1`.

## Verificaciones fail-closed

1. inventario exacto de ocho archivos;
2. self-hash físico de `files.sha256`;
3. siete entradas y siete hashes de payload;
4. hashes específicos de registry y manifest;
5. payload hash canónico del manifest;
6. cinco Parquet;
7. filas reales desde metadata Parquet;
8. bytes físicos;
9. `ts_max` recalculado por row group;
10. `ts_max < HOLDOUT_OPEN_UTC_NS`.

Resultado único aceptable:

```text
PASS_POST_UPLOAD_BYTE_REHASH
```

Artefacto:

```text
/kaggle/working/nq_post_upload_rehash.json
```

Cualquier discrepancia produce:

```text
FAIL_CLOSED_POST_UPLOAD_REHASH
```

## Nota sobre `files.sha256`

El reporte de upload mostró `652 B`, mientras el paquete local certificado registró `645 bytes`. La diferencia coincide numéricamente con siete terminadores LF convertidos a CRLF, pero esto es sólo una hipótesis. El verificador compara el self-hash físico y no normaliza EOL. Si el hash falla, el gate falla aunque los siete payloads individuales coincidan.

## Firewalls

```text
POST_UPLOAD_REHASH_AUTHORIZED = diagnostic_integrity_only
SCIENTIFIC_RUN_AUTHORIZED     = false
BIGTRAP2_RERUN_AUTHORIZED     = false
HOLDOUT_AUTHORIZED            = false
```

## Aporte al referente

El rehash se convierte en una operación reproducible y fail-closed que verifica bytes, filas y frontera temporal directamente dentro de Kaggle sin abrir ninguna capacidad científica.
