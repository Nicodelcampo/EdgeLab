# Kaggle dataset access Worker

Notion Worker usado para acceso autenticado y brokered a Kaggle sin exponer el token al chat ni al repositorio.

Worker desplegado: `01a0fddc-7cd2-7931-af05-23d821b1b3a8`.

Capacidades:

- buscar datasets accesibles;
- listar datasets propios/privados;
- inspeccionar metadata y archivos;
- leer previews de texto acotados;
- paginar archivos;
- emitir URL firmada de archivo o archive completo.

La credencial requerida se llama `KAGGLE_API_TOKEN` y debe cargarse mediante el flujo seguro de Notion Workers. Nunca se guarda en Git.

Para desplegar una copia:

```bash
npm install
npm run check
ntn workers deploy
```

El `workers.json` de enlace a workspace es local y no se versiona.

## Private kernel execution

`pushKaggleKernel` and `getKaggleKernelStatus` use Kaggle's official RPC host (`api.kaggle.com`) to launch private CPU/GPU scripts and monitor them. Expanding an existing credential to this host requires a new secure approval. The synthetic parity script is `gpu_parity.py`; it never reads D2 or market data.
