# Handoff para próximas sesiones

1. Leer `README.md`, `HYBRID_ARCHITECTURE.md` y los JSON de este directorio.
2. Verificar que el commit base y los hashes de raw coincidan antes de reutilizar arrays.
3. No abrir `trade_date >= 20260401`.
4. No tratar el grid núcleo de 42 como sustituto del registro original de 126.
5. La próxima unidad de trabajo es recuperar/preregistrar las 126 celdas y extender el motor compartido con tests.
6. Los datos/arrays locales no están en Git; se regeneran con el runbook. El acceso privado a Kaggle se hace mediante el Worker y su credencial brokered, nunca con tokens en archivos o commits.
