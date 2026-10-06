# Idea — detector de estados de mercado: consolidación / expansión + coeficiente de desplazamiento (Nico, 2026-10-06)

Pedido de Nico, para hacer después de AVCL-SR-DIR. No está ejecutado.

## Qué
Herramienta target-free que, en cada barra, clasifique el estado del mercado (consolidación o expansión) y publique un
**coeficiente de desplazamiento**.

## Por qué ahora
VOL-2 mostró que, después de una zona aVolClusterPOI, la ventana de 10 barras recorre más sin que crezcan las barras.
Esa diferencia, desplazamiento contra agitación, es justamente lo que el coeficiente tiene que medir.

## Candidatos de definición (a elegir antes de medir, sin mirar retornos)
- **Coeficiente de desplazamiento** = |close[t] − close[t−N]| / Σ |Δclose| en N barras. Es el efficiency ratio de
  Kaufman: 1 = recorrido recto, 0 = ida y vuelta. Variante: rango de la ventana / Σ rangos de barra.
- **Estado**: percentil móvil del coeficiente junto con la volatilidad relativa (rango N / su mediana de 20 sesiones).
  Por ejemplo: consolidación = desplazamiento y volatilidad bajos; expansión = desplazamiento alto.
- Alternativas a considerar: HMM de 2–3 estados sobre (rango, desplazamiento), varianza ratio de Lo–MacKinlay, el
  `VWAP Regime Classification` del corpus SSRN [372] y el HMM asimétrico de OFI [66].

## Requisitos
- Causal: sólo información hasta t. Paridad Python ↔ NT8 si se lleva al chart, y capa en el visor.
- Reutilizable como contexto: sirve para AVCL-VOL-2 contexto D, EdgeReplica y la canasta por régimen.
- Por la regla de población, al usarlo se enumera si se mide como **evento** (cambio de estado) o como **estado
  continuo**.
