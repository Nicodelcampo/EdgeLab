# Autorización explícita — upload privado NQ pre-holdout

**Emitida:** 2026-08-28T20:40:08.393Z  
**Autoridad:** propietario del proyecto  
**Token:** `AUTHORIZE_UPLOAD_KAGGLE_NQ_PREHOLDOUT_PRIVATE_V1`  
**Estado:** `AUTHORIZED_PENDING_LOCAL_EXECUTION`

## Alcance exacto

Se autoriza exclusivamente:

```text
kaggle datasets create -p "E:\EdgeLab\kaggle_nq_research"
```

para crear:

```text
nicodelcampo/edgelab-ticks-nq-preholdout
```

con visibilidad `private_only`.

## Condiciones obligatorias

- owner autenticado `nicodelcampo`;
- slug inexistente antes del create;
- metadata e inventario coincidentes;
- siete hashes y self-hash verificados;
- sin fallback a `version`;
- privacidad confirmada después mediante Web/API autenticada;
- cero kernel antes del rehash post-upload.

## Fuera de alcance

```text
PUBLIC_UPLOAD                 = false
AUTOMATIC_VERSION             = false
NOTEBOOK_EXECUTION            = false
BIGTRAP2_RERUN_AUTHORIZED     = false
BT2A_NQ_GATE1_AUTHORIZED      = false
HOLDOUT_AUTHORIZED            = false
SCIENTIFIC_RUN_AUTHORIZED     = false
```

## Ejecución

La autorización queda registrada, pero el upload no fue ejecutado desde este entorno porque no tiene acceso al directorio local `E:\EdgeLab\kaggle_nq_research`, a la cuenta Kaggle ni a sus credenciales.

## Aporte al referente

La decisión del propietario queda registrada como autorización de create privado y nada más; la ejecución local, verificación de privacidad y rehash post-upload siguen pendientes.
