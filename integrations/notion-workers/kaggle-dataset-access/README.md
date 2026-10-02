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
