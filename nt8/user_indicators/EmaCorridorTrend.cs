// EmaCorridorTrend.cs v4.0 — Detector de Zonas y Corredores Tendenciales Estables sobre EMA (Calibrado para ES 25T, NinjaTrader 8).
//
// REFACTORIZACION v4.0 (Cambios clave respecto de v3.3):
//   1. CORREDOR DE PICOS LEJANOS Y CERCANOS SIN SINGULARIDAD EN CERO:
//      En v3.3, EnvelopeOk dividia el desvio de los picos cercanos por su media (ncv = stdNear / meanNear). Cuando los pullbacks
//      se apoyaban prolijamente sobre la EMA (meanNear ~ 0 o levemente negativo por 1-2 ticks), ncv explotaba a infinito o devolvia false,
//      rechazando las mejores tendencias que rebotan en la EMA. En v4.0, tanto la dispersion de los picos mas lejanos (FarPeaks) como la
//      de los picos mas cercanos (NearPeaks) se normalizan por la escala del corredor Max(MeanFarAtr, 1.5), premiando apoyos limpios en la EMA.
//   2. MUESTREO POR SUB-BLOQUES CONTIGUOS (BlockBars = 12) + INMUNIDAD A EMPATES DE TICKS:
//      En ES 25T (TickSize = 0.25), es muy frecuente que 2 barras de un swing toquen exactamente el mismo tick (cnt > 1), lo que hacia
//      que v3.3 descartara >60% de los pivotes reales, y fallara por completo en tendencias de "escalera comprimida" sin swings anchos.
//      En v4.0, la ventana WindowBars se divide en sub-bloques de BlockBars barras; en cada bloque se toma el extremo mas lejano a la EMA
//      (maximo de High-EMA en suba, EMA-Low en baja) y el mas cercano (minimo de Low-EMA en suba, EMA-High en baja). Funciona tanto en
//      tendencias con ondas marcadas como en escaleras comprimidas.
//   3. CUATRO PILARES DE ESTABILIDAD:
//      (P1) Monotonia y Eficiencia de la EMA en ventana SlopeBars (EmaEfficiency >= MinEmaEfficiency, fraccion monotona >= MinEmaMono,
//           pendiente >= MinEmaSlopeAtr).
//      (P2) Dominancia unilateral con tolerancia de beso a la EMA (SideFraction >= MinSideFraction permitiendo pullbacks hasta -0.35 ATR,
//           MeanGapAtr >= MinGapAtr, y sin cierres opuestos profundos > MaxCounterCloseAtr).
//      (P3) Estabilidad de Picos Lejanos (FarDisp <= MaxFarDisp) y Picos Cercanos (NearDisp <= MaxNearDisp) respecto de la EMA.
//      (P4) Linealidad de la trayectoria del precio medio (R^2 de regresion lineal >= MinPriceR2).
//   4. ANCLAJE EXACTO DE ORIGEN Y TERMINACION LIMPIA:
//      - Al activarse una zona, FindZoneOrigin busca hacia atras el ultimo contacto con la EMA previo al despegue y ancla el inicio
//        exactamente en el extremo de arranque (maximo en baja, minimo en suba), sin superponerse con zonas previas.
//      - Reemplaza el HoldBars=100 antiguo por GraceBars corto (absorbe un pullback normal a la EMA) + corte estructural inmediato si el
//        precio cierra del lado opuesto de la EMA durante BreakConfirmBars barras seguidas o sufre un quiebre profundo (> HardBreakEmaAtr).
//      - El dibujo del canal/corredor termina exactamente en el ultimo extremo valido a favor de la tendencia (bestExtremeBar), nunca
//        arrastrandose dentro del giro posterior.
//   5. VISUALIZACION DEL CORREDOR EN EL GRAFICO + PLOTS CAUSALES:
//      - Dibuja el Eje Central de Regresion de la zona, las 2 Bandas Paralelas del Canal (picos lejanos y cercanos) y el Recuadro
//        Sombreado translucido del periodo tendencial.
//      - Mantiene los 5 Plots causales (State, Length, MovePts, SlopeAtr, StabilityScore) calculados estrictamente con datos <= t.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Gui;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
	public class EmaCorridorTrend : Indicator
	{
		private EMA ema;
		private SMA rangeAvg;

		// Estado causal de la zona activa
		private int    activeDir;
		private int    originBar;
		private int    lastOkBar;
		private int    lastZoneEndBar;
		private int    bestExtremeBar;
		private double bestExtremePx;
		private bool   confirmed;
		private int    zoneCounter;
		private string curTagPrefix;

		// Metricas de estabilidad vigentes de la zona
		private double lastStabilityScore;
		private double lastMeanFarAtr;
		private double lastMeanNearAtr;
		private double lastR2;
		private double lastEmaSlopeAtr;

		// Parametros efectivos segun el Preset elegido
		private int    pWindowBars;
		private int    pSlopeBars;
		private int    pBlockBars;
		private int    pMinZoneBars;
		private int    pGraceBars;
		private double pMinEmaEff;
		private double pMinEmaMono;
		private double pMinEmaSlopeAtr;
		private double pMinSideFrac;
		private double pMinGapAtr;
		private double pMaxCounterCloseAtr;
		private double pMaxFarDisp;
		private double pMaxNearDisp;
		private double pMinPriceR2;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name              = "EmaCorridorTrend";
				Description       = "v4.0 — Detecta y enmarca periodos tendenciales muy estables respecto de una EMA (calibrado para ES 25T).";
				Calculate         = Calculate.OnBarClose;
				IsOverlay         = true;
				DisplayInDataBox  = true;
				PaintPriceMarkers = false;

				// 1. Base
				EmaPeriod         = 200;
				AtrPeriod         = 100;
				Preset            = 2;     // 0=Manual, 1=Selectivo (Pocas), 2=Equilibrado (Default ES 25T), 3=Amplio (Muchas)

				// 2. Ciclo de vida y longitud de zona
				MinZoneBars        = 65;
				MinMovePoints      = 0.0;
				LookbackOriginBars = 40;
				GraceBars          = 24;
				BreakConfirmBars   = 5;
				HardBreakEmaAtr    = 1.60;

				// 3. Detector de estabilidad (valores por defecto iguales a Preset 2 para ES 25T)
				WindowBars         = 60;
				SlopeBars          = 45;
				BlockBars          = 12;
				MinEmaEfficiency   = 0.85;
				MinEmaMono         = 0.84;
				MinEmaSlopeAtr     = 0.030;
				MinSideFraction    = 0.88;
				MinGapAtr          = 0.80;
				MaxCounterCloseAtr = 1.05;
				MaxFarDisp         = 0.44;
				MaxNearDisp        = 0.46;
				MinPriceR2         = 0.64;

				// 4. Visual
				ShowChannelLines   = true;
				ShowZoneBox        = true;
				ZoneOpacity        = 12;
				LineWidth          = 2;
				UpTrendBrush       = Brushes.DodgerBlue;
				DownTrendBrush     = Brushes.Crimson;

				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "State");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "Length");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "MovePts");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "SlopeAtr");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "StabilityScore");
			}
			else if (State == State.DataLoaded)
			{
				ema      = EMA(EmaPeriod);
				rangeAvg = SMA(Range(), AtrPeriod);

				activeDir          = 0;
				originBar          = 0;
				lastOkBar          = -1000000;
				lastZoneEndBar     = 0;
				bestExtremeBar     = 0;
				bestExtremePx      = 0.0;
				confirmed          = false;
				zoneCounter        = 0;
				curTagPrefix       = null;
				lastStabilityScore = 0.0;
				lastMeanFarAtr     = 0.0;
				lastMeanNearAtr    = 0.0;
				lastR2             = 0.0;
				lastEmaSlopeAtr    = 0.0;

				ApplyPreset();
			}
		}

		private void ApplyPreset()
		{
			pWindowBars         = Math.Max(20, WindowBars);
			pSlopeBars          = Math.Max(10, SlopeBars);
			pBlockBars          = Math.Max(4, BlockBars);
			pMinZoneBars        = Math.Max(15, MinZoneBars);
			pGraceBars          = Math.Max(0, GraceBars);
			pMinEmaEff          = MinEmaEfficiency;
			pMinEmaMono         = MinEmaMono;
			pMinEmaSlopeAtr     = MinEmaSlopeAtr;
			pMinSideFrac        = MinSideFraction;
			pMinGapAtr          = MinGapAtr;
			pMaxCounterCloseAtr = MaxCounterCloseAtr;
			pMaxFarDisp         = MaxFarDisp;
			pMaxNearDisp        = MaxNearDisp;
			pMinPriceR2         = MinPriceR2;

			if (Preset == 1) // Selectivo: solo tendencias ultra-limpias y largas
			{
				pWindowBars         = 72;
				pSlopeBars          = 50;
				pBlockBars          = 12;
				pMinZoneBars        = 75;
				pGraceBars          = 20;
				pMinEmaEff          = 0.90;
				pMinEmaMono         = 0.88;
				pMinEmaSlopeAtr     = 0.040;
				pMinSideFrac        = 0.92;
				pMinGapAtr          = 1.05;
				pMaxCounterCloseAtr = 0.80;
				pMaxFarDisp         = 0.36;
				pMaxNearDisp        = 0.38;
				pMinPriceR2         = 0.72;
			}
			else if (Preset == 2) // Equilibrado: calibrado para ES 25T (captura tanto canales con ondas como escaleras de 70-220 barras)
			{
				pWindowBars         = 60;
				pSlopeBars          = 45;
				pBlockBars          = 12;
				pMinZoneBars        = 65;
				pGraceBars          = 24;
				pMinEmaEff          = 0.85;
				pMinEmaMono         = 0.84;
				pMinEmaSlopeAtr     = 0.030;
				pMinSideFrac        = 0.88;
				pMinGapAtr          = 0.80;
				pMaxCounterCloseAtr = 1.05;
				pMaxFarDisp         = 0.44;
				pMaxNearDisp        = 0.46;
				pMinPriceR2         = 0.64;
			}
			else if (Preset == 3) // Amplio: mas permisivo para detectar tramos cortos o con pullbacks mas profundos
			{
				pWindowBars         = 48;
				pSlopeBars          = 36;
				pBlockBars          = 12;
				pMinZoneBars        = 50;
				pGraceBars          = 28;
				pMinEmaEff          = 0.80;
				pMinEmaMono         = 0.80;
				pMinEmaSlopeAtr     = 0.024;
				pMinSideFrac        = 0.84;
				pMinGapAtr          = 0.65;
				pMaxCounterCloseAtr = 1.25;
				pMaxFarDisp         = 0.52;
				pMaxNearDisp        = 0.55;
				pMinPriceR2         = 0.55;
			}
		}

		protected override void OnBarUpdate()
		{
			for (int i = 0; i < 5; i++)
				Values[i][0] = 0.0;

			int minBarsNeeded = Math.Max(Math.Max(pWindowBars + LookbackOriginBars, pSlopeBars), Math.Max(EmaPeriod, AtrPeriod)) + 5;
			if (CurrentBar < minBarsNeeded)
				return;

			double atrNow = Math.Max(rangeAvg[0], TickSize);
			int    candDir;
			double stabScore, meanFarAtr, meanNearAtr, r2Val, emaSlopeAtr;

			bool condOk = EvaluateStabilityWindow(out candDir, out stabScore, out meanFarAtr, out meanNearAtr, out r2Val, out emaSlopeAtr);

			if (condOk)
			{
				if (activeDir != candDir)
				{
					// Inicia nueva zona candidata y localiza el pivote exacto donde arranco el movimiento
					activeDir          = candDir;
					originBar          = FindZoneOrigin(activeDir);
					bestExtremeBar     = CurrentBar;
					bestExtremePx      = activeDir > 0 ? High[0] : Low[0];
					confirmed          = false;
					zoneCounter++;
					curTagPrefix       = "ECT_" + zoneCounter.ToString(CultureInfo.InvariantCulture) + "_";
				}

				lastOkBar          = CurrentBar;
				lastStabilityScore = stabScore;
				lastMeanFarAtr     = meanFarAtr;
				lastMeanNearAtr    = meanNearAtr;
				lastR2             = r2Val;
				lastEmaSlopeAtr    = emaSlopeAtr;
			}

			if (activeDir == 0)
				return;

			// Actualizar el extremo mas lejano alcanzado por la tendencia hasta la barra actual
			if (activeDir > 0 && High[0] >= bestExtremePx)
			{
				bestExtremePx  = High[0];
				bestExtremeBar = CurrentBar;
			}
			else if (activeDir < 0 && Low[0] <= bestExtremePx)
			{
				bestExtremePx  = Low[0];
				bestExtremeBar = CurrentBar;
			}

			// Verificar si la tendencia se rompio estructuralmente (cruce confirmado de la EMA o expiracion de GraceBars)
			if (IsTrendBroken(activeDir, atrNow))
			{
				if (confirmed)
				{
					DrawZoneCorridor(activeDir);
					lastZoneEndBar = Math.Max(lastZoneEndBar, bestExtremeBar);
				}

				activeDir = 0;
				confirmed = false;
				return;
			}

			int    zoneLen = CurrentBar - originBar + 1;
			double origPx  = activeDir > 0 ? Low[CurrentBar - originBar] : High[CurrentBar - originBar];
			double movePts = Math.Abs(Close[0] - origPx);

			if (!confirmed && condOk && zoneLen >= pMinZoneBars && (MinMovePoints <= 0.0 || movePts >= MinMovePoints))
				confirmed = true;

			if (confirmed)
			{
				Values[0][0] = activeDir;
				Values[1][0] = zoneLen;
				Values[2][0] = movePts;
				Values[3][0] = activeDir * lastEmaSlopeAtr;
				Values[4][0] = lastStabilityScore;

				DrawZoneCorridor(activeDir);
			}
		}

		// Evalua los 4 Pilares de Estabilidad sobre la ventana movil [CurrentBar - pWindowBars + 1 .. CurrentBar]
		private bool EvaluateStabilityWindow(
			out int    dir,
			out double stabilityScore,
			out double meanFarAtr,
			out double meanNearAtr,
			out double r2Out,
			out double emaSlopeAtrOut)
		{
			dir            = 0;
			stabilityScore = 0.0;
			meanFarAtr     = 0.0;
			meanNearAtr    = 0.0;
			r2Out          = 0.0;
			emaSlopeAtrOut = 0.0;

			double atr0 = Math.Max(rangeAvg[0], TickSize);
			double dispEma = ema[0] - ema[pSlopeBars];
			dir = dispEma > 0.0 ? 1 : (dispEma < 0.0 ? -1 : 0);
			if (dir == 0)
				return false;

			// --- PILAR 1: Eficiencia, Monotonia y Pendiente de la EMA ---
			double sumAbsDe = 0.0;
			int    monoCount = 0;
			for (int i = 0; i < pSlopeBars; i++)
			{
				double de = ema[i] - ema[i + 1];
				sumAbsDe += Math.Abs(de);
				if (de * dir > 0.0)
					monoCount++;
			}
			if (sumAbsDe <= 1e-12)
				return false;

			double emaEff  = Math.Abs(dispEma) / sumAbsDe;
			double emaMono = (double)monoCount / pSlopeBars;
			emaSlopeAtrOut = Math.Abs(dispEma) / (pSlopeBars * atr0);

			if (emaEff < pMinEmaEff || emaMono < pMinEmaMono || emaSlopeAtrOut < pMinEmaSlopeAtr)
				return false;

			// --- PILAR 2: Dominancia de lado respecto a la EMA (con tolerancia de beso en pullbacks) ---
			int    sideCount      = 0;
			double sumSignedClose = 0.0;
			double minSignedClose = 1e18;

			for (int i = 0; i < pWindowBars; i++)
			{
				double aBar        = Math.Max(rangeAvg[i], TickSize);
				double signedClose = dir * (Close[i] - ema[i]) / aBar;
				sumSignedClose += signedClose;
				if (signedClose >= -0.35)
					sideCount++;
				if (signedClose < minSignedClose)
					minSignedClose = signedClose;
			}

			double sideFrac   = (double)sideCount / pWindowBars;
			double meanGapAtr = sumSignedClose / pWindowBars;

			if (sideFrac < pMinSideFrac || meanGapAtr < pMinGapAtr || minSignedClose < -pMaxCounterCloseAtr)
				return false;

			// --- PILAR 3: Estabilidad de Picos Mas Lejanos (Far) y Mas Cercanos (Near) por Sub-Bloques ---
			int nBlocks = Math.Max(2, pWindowBars / pBlockBars);
			double sumFar = 0.0, sumFarSq = 0.0;
			double sumNear = 0.0, sumNearSq = 0.0;

			for (int b = 0; b < nBlocks; b++)
			{
				int startAgo = (nBlocks - 1 - b) * pBlockBars;
				int endAgo   = startAgo + pBlockBars - 1;
				if (endAgo >= pWindowBars)
					endAgo = pWindowBars - 1;

				double maxFar  = -1e18;
				double minNear = 1e18;

				for (int ago = startAgo; ago <= endAgo; ago++)
				{
					double aBar = Math.Max(rangeAvg[ago], TickSize);
					double farD  = dir > 0 ? (High[ago] - ema[ago]) / aBar : (ema[ago] - Low[ago]) / aBar;
					double nearD = dir > 0 ? (Low[ago] - ema[ago]) / aBar  : (ema[ago] - High[ago]) / aBar;

					if (farD > maxFar)   maxFar  = farD;
					if (nearD < minNear) minNear = nearD;
				}

				sumFar    += maxFar;
				sumFarSq  += maxFar * maxFar;
				sumNear   += minNear;
				sumNearSq += minNear * minNear;
			}

			meanFarAtr  = sumFar / nBlocks;
			meanNearAtr = sumNear / nBlocks;
			if (meanFarAtr <= 0.5)
				return false;

			double corridorScale = Math.Max(meanFarAtr, 1.5);
			double stdFar        = Math.Sqrt(Math.Max(sumFarSq / nBlocks - meanFarAtr * meanFarAtr, 0.0));
			double stdNear       = Math.Sqrt(Math.Max(sumNearSq / nBlocks - meanNearAtr * meanNearAtr, 0.0));
			double farDisp       = stdFar / corridorScale;
			double nearDisp      = stdNear / corridorScale;

			if (pMaxFarDisp > 0.0 && farDisp > pMaxFarDisp)
				return false;
			if (pMaxNearDisp > 0.0 && nearDisp > pMaxNearDisp)
				return false;

			// --- PILAR 4: Linealidad de la Trayectoria del Precio Medio (R^2) ---
			double xMean = 0.5 * (pWindowBars - 1);
			double ySum  = 0.0;
			for (int k = 0; k < pWindowBars; k++)
			{
				int ago = pWindowBars - 1 - k;
				ySum += 0.5 * (High[ago] + Low[ago]);
			}
			double yMean = ySum / pWindowBars;

			double sxx = 0.0, syy = 0.0, sxy = 0.0;
			for (int k = 0; k < pWindowBars; k++)
			{
				int    ago = pWindowBars - 1 - k;
				double dx  = k - xMean;
				double dy  = 0.5 * (High[ago] + Low[ago]) - yMean;
				sxx += dx * dx;
				syy += dy * dy;
				sxy += dx * dy;
			}

			double denom = sxx * syy;
			double rCorr = denom > 1e-12 ? sxy / Math.Sqrt(denom) : 0.0;
			r2Out = (rCorr * dir > 0.0) ? (rCorr * rCorr) : 0.0;

			if (r2Out < pMinPriceR2)
				return false;

			double farScore  = pMaxFarDisp > 0.0  ? Math.Max(0.0, 1.0 - farDisp / pMaxFarDisp)   : 1.0;
			double nearScore = pMaxNearDisp > 0.0 ? Math.Max(0.0, 1.0 - nearDisp / pMaxNearDisp) : 1.0;
			stabilityScore   = 100.0 * (0.35 * r2Out + 0.25 * emaEff + 0.20 * farScore + 0.20 * nearScore);
			return true;
		}

		// Localiza el extremo exacto donde el precio se despego de la EMA al iniciar la tendencia
		private int FindZoneOrigin(int dir)
		{
			int minAllowedBar = Math.Max(5, lastZoneEndBar + 1);
			int loBound       = Math.Max(minAllowedBar, CurrentBar - pWindowBars - LookbackOriginBars);
			int hiBound       = Math.Max(loBound, CurrentBar - pWindowBars + 12);

			int touchBar = hiBound;
			for (int b = hiBound; b >= loBound; b--)
			{
				int    ago     = CurrentBar - b;
				double aBar    = Math.Max(rangeAvg[ago], TickSize);
				double signedC = dir * (Close[ago] - ema[ago]) / aBar;
				if (signedC <= 0.15)
				{
					touchBar = b;
					break;
				}
			}

			int pvStart = Math.Max(minAllowedBar, touchBar - 10);
			int pvEnd   = Math.Min(CurrentBar - pWindowBars / 2, touchBar + 10);
			if (pvEnd < pvStart)
				pvEnd = pvStart;

			int    bestBar = pvStart;
			int    ago0    = CurrentBar - pvStart;
			double bestVal = dir > 0 ? Low[ago0] : High[ago0];

			for (int b = pvStart; b <= pvEnd; b++)
			{
				int ago = CurrentBar - b;
				if (dir > 0 && Low[ago] <= bestVal)
				{
					bestVal = Low[ago];
					bestBar = b;
				}
				else if (dir < 0 && High[ago] >= bestVal)
				{
					bestVal = High[ago];
					bestBar = b;
				}
			}
			return bestBar;
		}

		// Verifica si la tendencia sufrio un quiebre estructural de la EMA o agoto GraceBars
		private bool IsTrendBroken(int dir, double atrNow)
		{
			if (CurrentBar - lastOkBar > pGraceBars)
				return true;

			double signedCloseNow = dir * (Close[0] - ema[0]) / atrNow;
			if (signedCloseNow < -HardBreakEmaAtr)
				return true;

			int checkBars = Math.Min(BreakConfirmBars, CurrentBar);
			if (checkBars >= BreakConfirmBars)
			{
				bool allOpposite = true;
				for (int i = 0; i < BreakConfirmBars; i++)
				{
					double aBar = Math.Max(rangeAvg[i], TickSize);
					double sc   = dir * (Close[i] - ema[i]) / aBar;
					if (sc >= -0.35)
					{
						allOpposite = false;
						break;
					}
				}
				if (allOpposite)
					return true;
			}
			return false;
		}

		// Dibuja el Eje Central de Regresion, las Bandas Paralelas (Far/Near) y el Sombreado de la Zona
		// recortando el extremo derecho exactamente en el ultimo extremo valido (bestExtremeBar).
		private void DrawZoneCorridor(int dir)
		{
			if (curTagPrefix == null)
				return;

			int endBar = Math.Max(originBar + 15, bestExtremeBar);
			if (endBar > CurrentBar)
				endBar = CurrentBar;

			int startAgo = CurrentBar - originBar;
			int endAgo   = CurrentBar - endBar;
			int nSpan    = endBar - originBar + 1;
			if (startAgo <= endAgo || nSpan < 10)
				return;

			// Regresion lineal del precio medio entre originBar (k=0) y endBar (k=nSpan-1)
			double xMean = 0.5 * (nSpan - 1);
			double ySum  = 0.0;
			for (int k = 0; k < nSpan; k++)
			{
				int ago = CurrentBar - (originBar + k);
				ySum += 0.5 * (High[ago] + Low[ago]);
			}
			double yMean = ySum / nSpan;

			double sxx = 0.0, sxy = 0.0;
			for (int k = 0; k < nSpan; k++)
			{
				int    ago = CurrentBar - (originBar + k);
				double dx  = k - xMean;
				double dy  = 0.5 * (High[ago] + Low[ago]) - yMean;
				sxx += dx * dx;
				sxy += dx * dy;
			}

			double slope     = sxx > 1e-12 ? sxy / sxx : 0.0;
			double intercept = yMean - slope * xMean;

			// Calcular offsets de las bandas superior e inferior (percentil ~90 / media de extremos respecto del eje)
			List<double> upRes = new List<double>(nSpan);
			List<double> dnRes = new List<double>(nSpan);
			double maxHi = -1e18, minLo = 1e18;

			for (int k = 0; k < nSpan; k++)
			{
				int    ago = CurrentBar - (originBar + k);
				double reg = intercept + slope * k;
				upRes.Add(High[ago] - reg);
				dnRes.Add(reg - Low[ago]);
				if (High[ago] > maxHi) maxHi = High[ago];
				if (Low[ago] < minLo)  minLo = Low[ago];
			}
			upRes.Sort();
			dnRes.Sort();
			int idx90    = Math.Min(nSpan - 1, Math.Max(0, (int)Math.Round(0.90 * (nSpan - 1))));
			double upOff = Math.Max(TickSize, upRes[idx90]);
			double dnOff = Math.Max(TickSize, dnRes[idx90]);

			double yStart = intercept;
			double yEnd   = intercept + slope * (nSpan - 1);
			Brush  cBrush = dir > 0 ? UpTrendBrush : DownTrendBrush;

			// 1. Tangente Estructural del lado de los pullbacks (Picos Cercanos a la EMA: por encima en baja, por debajo en suba)
			//    Se dibuja con trazo SOLIDO como una trendline clasica pero con pendiente regresiva estable.
			double tlStart  = dir < 0 ? (yStart + upOff) : (yStart - dnOff);
			double tlEnd    = dir < 0 ? (yEnd + upOff)   : (yEnd - dnOff);
			double farStart = dir < 0 ? (yStart - dnOff) : (yStart + upOff);
			double farEnd   = dir < 0 ? (yEnd - dnOff)   : (yEnd + upOff);

			Draw.Line(this, curTagPrefix + "TL", false, startAgo, tlStart, endAgo, tlEnd, cBrush, DashStyleHelper.Solid, LineWidth);

			// 2. Banda paralela de Picos Lejanos (impulsos) y Eje Central de Regresion
			if (ShowChannelLines)
			{
				Draw.Line(this, curTagPrefix + "FAR", false, startAgo, farStart, endAgo, farEnd, cBrush, DashStyleHelper.Dash, Math.Max(1, LineWidth - 1));
				Draw.Line(this, curTagPrefix + "MID", false, startAgo, yStart, endAgo, yEnd, cBrush, DashStyleHelper.Dot, 1);
			}

			// 3. Recuadro sombreado del periodo tendencial
			if (ShowZoneBox && ZoneOpacity > 0)
			{
				Draw.Rectangle(this, curTagPrefix + "BOX", false, startAgo, maxHi, endAgo, minLo, Brushes.Transparent, cBrush, ZoneOpacity);
			}
		}

		#region Plot Series Accessors
		[Browsable(false)]
		[XmlIgnore]
		public Series<double> StateSeries { get { return Values[0]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> LengthSeries { get { return Values[1]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> MovePtsSeries { get { return Values[2]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> SlopeAtrSeries { get { return Values[3]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> StabilityScore { get { return Values[4]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Peaks { get { return Values[4]; } }
		#endregion

		#region Properties
		[NinjaScriptProperty] [Range(2, 5000)]
		[Display(Name = "EMA Period", Order = 1, GroupName = "1. Base")]
		public int EmaPeriod { get; set; }

		[NinjaScriptProperty] [Range(2, 5000)]
		[Display(Name = "ATR Period (media de High-Low)", Order = 2, GroupName = "1. Base")]
		public int AtrPeriod { get; set; }

		[NinjaScriptProperty] [Range(0, 3)]
		[Display(Name = "Preset (0 Manual, 1 Selectivo, 2 ES-25T Default, 3 Amplio)", Order = 3, GroupName = "1. Base",
			Description = "2 = Calibrado para ES 25T. 1 = Solo tendencias muy largas/estrictas. 3 = Mas permisivo. 0 = Usa parametros manuales del grupo 3.")]
		public int Preset { get; set; }

		[NinjaScriptProperty] [Range(10, 5000)]
		[Display(Name = "Min Zone Bars (longitud minima)", Order = 1, GroupName = "2. Ciclo de Vida de la Zona",
			Description = "Barras minimas desde el pivote de origen para confirmar la zona tendencial.")]
		public int MinZoneBars { get; set; }

		[NinjaScriptProperty] [Range(0.0, 100000.0)]
		[Display(Name = "Min Move Points (0 = off)", Order = 2, GroupName = "2. Ciclo de Vida de la Zona",
			Description = "Recorrido minimo en puntos desde el origen para confirmar la zona.")]
		public double MinMovePoints { get; set; }

		[NinjaScriptProperty] [Range(5, 500)]
		[Display(Name = "Lookback Origin Bars", Order = 3, GroupName = "2. Ciclo de Vida de la Zona",
			Description = "Barras adicionales hacia atras para enganchar el pivote exacto donde despego de la EMA.")]
		public int LookbackOriginBars { get; set; }

		[NinjaScriptProperty] [Range(0, 200)]
		[Display(Name = "Grace Bars (tolerancia en pullback)", Order = 4, GroupName = "2. Ciclo de Vida de la Zona",
			Description = "Barras de tolerancia durante un pullback hacia la EMA antes de cerrar la zona (el dibujo se recorta en el ultimo extremo valido).")]
		public int GraceBars { get; set; }

		[NinjaScriptProperty] [Range(1, 50)]
		[Display(Name = "Break Confirm Bars", Order = 5, GroupName = "2. Ciclo de Vida de la Zona",
			Description = "Cierres consecutivos del lado opuesto de la EMA (>0.35 ATR) que terminan la zona inmediatamente.")]
		public int BreakConfirmBars { get; set; }

		[NinjaScriptProperty] [Range(0.2, 20.0)]
		[Display(Name = "Hard Break EMA (ATR)", Order = 6, GroupName = "2. Ciclo de Vida de la Zona",
			Description = "Un solo cierre del lado opuesto de la EMA mayor a estos ATRs termina la zona en el acto.")]
		public double HardBreakEmaAtr { get; set; }

		[NinjaScriptProperty] [Range(20, 5000)]
		[Display(Name = "Window Bars (M)", Order = 1, GroupName = "3. Detector Manual (Preset 0)")]
		public int WindowBars { get; set; }

		[NinjaScriptProperty] [Range(10, 5000)]
		[Display(Name = "Slope Bars (K)", Order = 2, GroupName = "3. Detector Manual (Preset 0)")]
		public int SlopeBars { get; set; }

		[NinjaScriptProperty] [Range(4, 200)]
		[Display(Name = "Block Bars (muestreo de picos)", Order = 3, GroupName = "3. Detector Manual (Preset 0)",
			Description = "Tamano de cada sub-bloque para medir los picos mas lejanos y mas cercanos a la EMA.")]
		public int BlockBars { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "Min EMA Efficiency", Order = 4, GroupName = "3. Detector Manual (Preset 0)")]
		public double MinEmaEfficiency { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "Min EMA Monotonicity", Order = 5, GroupName = "3. Detector Manual (Preset 0)")]
		public double MinEmaMono { get; set; }

		[NinjaScriptProperty] [Range(0.0, 10.0)]
		[Display(Name = "Min EMA Slope (ATR/barra)", Order = 6, GroupName = "3. Detector Manual (Preset 0)")]
		public double MinEmaSlopeAtr { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "Min Side Fraction", Order = 7, GroupName = "3. Detector Manual (Preset 0)")]
		public double MinSideFraction { get; set; }

		[NinjaScriptProperty] [Range(0.0, 50.0)]
		[Display(Name = "Min Mean Gap (ATR)", Order = 8, GroupName = "3. Detector Manual (Preset 0)")]
		public double MinGapAtr { get; set; }

		[NinjaScriptProperty] [Range(0.0, 20.0)]
		[Display(Name = "Max Counter Close (ATR)", Order = 9, GroupName = "3. Detector Manual (Preset 0)")]
		public double MaxCounterCloseAtr { get; set; }

		[NinjaScriptProperty] [Range(0.0, 10.0)]
		[Display(Name = "Max Far Peak Dispersion", Order = 10, GroupName = "3. Detector Manual (Preset 0)",
			Description = "Dispersión maxima de los picos mas lejanos a la EMA (normalizada por la escala del corredor).")]
		public double MaxFarDisp { get; set; }

		[NinjaScriptProperty] [Range(0.0, 10.0)]
		[Display(Name = "Max Near Peak Dispersion", Order = 11, GroupName = "3. Detector Manual (Preset 0)",
			Description = "Dispersión maxima de los picos mas cercanos a la EMA (normalizada por la escala del corredor; sin singularidad cuando toca la EMA).")]
		public double MaxNearDisp { get; set; }

		[NinjaScriptProperty] [Range(0.0, 1.0)]
		[Display(Name = "Min Price Linear R2", Order = 12, GroupName = "3. Detector Manual (Preset 0)",
			Description = "R^2 minimo de la regresion lineal del precio medio en la ventana.")]
		public double MinPriceR2 { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Parallel Channel Lines", Order = 1, GroupName = "4. Visual")]
		public bool ShowChannelLines { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Shaded Zone Box", Order = 2, GroupName = "4. Visual")]
		public bool ShowZoneBox { get; set; }

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "Zone Box Opacity (0-100)", Order = 3, GroupName = "4. Visual")]
		public int ZoneOpacity { get; set; }

		[NinjaScriptProperty] [Range(1, 10)]
		[Display(Name = "Main Line Width", Order = 4, GroupName = "4. Visual")]
		public int LineWidth { get; set; }

		[XmlIgnore]
		[Display(Name = "Up Trend Color", Order = 5, GroupName = "4. Visual")]
		public Brush UpTrendBrush { get; set; }
		[Browsable(false)]
		public string UpTrendBrushSerialize
		{
			get { return Serialize.BrushToString(UpTrendBrush); }
			set { UpTrendBrush = Serialize.StringToBrush(value); }
		}

		[XmlIgnore]
		[Display(Name = "Down Trend Color", Order = 6, GroupName = "4. Visual")]
		public Brush DownTrendBrush { get; set; }
		[Browsable(false)]
		public string DownTrendBrushSerialize
		{
			get { return Serialize.BrushToString(DownTrendBrush); }
			set { DownTrendBrush = Serialize.StringToBrush(value); }
		}
		#endregion
	}
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private EmaCorridorTrend[] cacheEmaCorridorTrend;
		public EmaCorridorTrend EmaCorridorTrend(int emaPeriod, int atrPeriod, int preset, int minZoneBars, double minMovePoints, int lookbackOriginBars, int graceBars, int breakConfirmBars, double hardBreakEmaAtr, int windowBars, int slopeBars, int blockBars, double minEmaEfficiency, double minEmaMono, double minEmaSlopeAtr, double minSideFraction, double minGapAtr, double maxCounterCloseAtr, double maxFarDisp, double maxNearDisp, double minPriceR2, bool showChannelLines, bool showZoneBox, int zoneOpacity, int lineWidth)
		{
			return EmaCorridorTrend(Input, emaPeriod, atrPeriod, preset, minZoneBars, minMovePoints, lookbackOriginBars, graceBars, breakConfirmBars, hardBreakEmaAtr, windowBars, slopeBars, blockBars, minEmaEfficiency, minEmaMono, minEmaSlopeAtr, minSideFraction, minGapAtr, maxCounterCloseAtr, maxFarDisp, maxNearDisp, minPriceR2, showChannelLines, showZoneBox, zoneOpacity, lineWidth);
		}

		public EmaCorridorTrend EmaCorridorTrend(ISeries<double> input, int emaPeriod, int atrPeriod, int preset, int minZoneBars, double minMovePoints, int lookbackOriginBars, int graceBars, int breakConfirmBars, double hardBreakEmaAtr, int windowBars, int slopeBars, int blockBars, double minEmaEfficiency, double minEmaMono, double minEmaSlopeAtr, double minSideFraction, double minGapAtr, double maxCounterCloseAtr, double maxFarDisp, double maxNearDisp, double minPriceR2, bool showChannelLines, bool showZoneBox, int zoneOpacity, int lineWidth)
		{
			if (cacheEmaCorridorTrend != null)
				for (int idx = 0; idx < cacheEmaCorridorTrend.Length; idx++)
					if (cacheEmaCorridorTrend[idx] != null && cacheEmaCorridorTrend[idx].EmaPeriod == emaPeriod && cacheEmaCorridorTrend[idx].AtrPeriod == atrPeriod && cacheEmaCorridorTrend[idx].Preset == preset && cacheEmaCorridorTrend[idx].MinZoneBars == minZoneBars && cacheEmaCorridorTrend[idx].MinMovePoints == minMovePoints && cacheEmaCorridorTrend[idx].LookbackOriginBars == lookbackOriginBars && cacheEmaCorridorTrend[idx].GraceBars == graceBars && cacheEmaCorridorTrend[idx].BreakConfirmBars == breakConfirmBars && cacheEmaCorridorTrend[idx].HardBreakEmaAtr == hardBreakEmaAtr && cacheEmaCorridorTrend[idx].WindowBars == windowBars && cacheEmaCorridorTrend[idx].SlopeBars == slopeBars && cacheEmaCorridorTrend[idx].BlockBars == blockBars && cacheEmaCorridorTrend[idx].MinEmaEfficiency == minEmaEfficiency && cacheEmaCorridorTrend[idx].MinEmaMono == minEmaMono && cacheEmaCorridorTrend[idx].MinEmaSlopeAtr == minEmaSlopeAtr && cacheEmaCorridorTrend[idx].MinSideFraction == minSideFraction && cacheEmaCorridorTrend[idx].MinGapAtr == minGapAtr && cacheEmaCorridorTrend[idx].MaxCounterCloseAtr == maxCounterCloseAtr && cacheEmaCorridorTrend[idx].MaxFarDisp == maxFarDisp && cacheEmaCorridorTrend[idx].MaxNearDisp == maxNearDisp && cacheEmaCorridorTrend[idx].MinPriceR2 == minPriceR2 && cacheEmaCorridorTrend[idx].ShowChannelLines == showChannelLines && cacheEmaCorridorTrend[idx].ShowZoneBox == showZoneBox && cacheEmaCorridorTrend[idx].ZoneOpacity == zoneOpacity && cacheEmaCorridorTrend[idx].LineWidth == lineWidth && cacheEmaCorridorTrend[idx].EqualsInput(input))
						return cacheEmaCorridorTrend[idx];
			return CacheIndicator<EmaCorridorTrend>(new EmaCorridorTrend(){ EmaPeriod = emaPeriod, AtrPeriod = atrPeriod, Preset = preset, MinZoneBars = minZoneBars, MinMovePoints = minMovePoints, LookbackOriginBars = lookbackOriginBars, GraceBars = graceBars, BreakConfirmBars = breakConfirmBars, HardBreakEmaAtr = hardBreakEmaAtr, WindowBars = windowBars, SlopeBars = slopeBars, BlockBars = blockBars, MinEmaEfficiency = minEmaEfficiency, MinEmaMono = minEmaMono, MinEmaSlopeAtr = minEmaSlopeAtr, MinSideFraction = minSideFraction, MinGapAtr = minGapAtr, MaxCounterCloseAtr = maxCounterCloseAtr, MaxFarDisp = maxFarDisp, MaxNearDisp = maxNearDisp, MinPriceR2 = minPriceR2, ShowChannelLines = showChannelLines, ShowZoneBox = showZoneBox, ZoneOpacity = zoneOpacity, LineWidth = lineWidth }, input, ref cacheEmaCorridorTrend);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.EmaCorridorTrend EmaCorridorTrend(int emaPeriod, int atrPeriod, int preset, int minZoneBars, double minMovePoints, int lookbackOriginBars, int graceBars, int breakConfirmBars, double hardBreakEmaAtr, int windowBars, int slopeBars, int blockBars, double minEmaEfficiency, double minEmaMono, double minEmaSlopeAtr, double minSideFraction, double minGapAtr, double maxCounterCloseAtr, double maxFarDisp, double maxNearDisp, double minPriceR2, bool showChannelLines, bool showZoneBox, int zoneOpacity, int lineWidth)
		{
			return indicator.EmaCorridorTrend(Input, emaPeriod, atrPeriod, preset, minZoneBars, minMovePoints, lookbackOriginBars, graceBars, breakConfirmBars, hardBreakEmaAtr, windowBars, slopeBars, blockBars, minEmaEfficiency, minEmaMono, minEmaSlopeAtr, minSideFraction, minGapAtr, maxCounterCloseAtr, maxFarDisp, maxNearDisp, minPriceR2, showChannelLines, showZoneBox, zoneOpacity, lineWidth);
		}

		public Indicators.EmaCorridorTrend EmaCorridorTrend(ISeries<double> input , int emaPeriod, int atrPeriod, int preset, int minZoneBars, double minMovePoints, int lookbackOriginBars, int graceBars, int breakConfirmBars, double hardBreakEmaAtr, int windowBars, int slopeBars, int blockBars, double minEmaEfficiency, double minEmaMono, double minEmaSlopeAtr, double minSideFraction, double minGapAtr, double maxCounterCloseAtr, double maxFarDisp, double maxNearDisp, double minPriceR2, bool showChannelLines, bool showZoneBox, int zoneOpacity, int lineWidth)
		{
			return indicator.EmaCorridorTrend(input, emaPeriod, atrPeriod, preset, minZoneBars, minMovePoints, lookbackOriginBars, graceBars, breakConfirmBars, hardBreakEmaAtr, windowBars, slopeBars, blockBars, minEmaEfficiency, minEmaMono, minEmaSlopeAtr, minSideFraction, minGapAtr, maxCounterCloseAtr, maxFarDisp, maxNearDisp, minPriceR2, showChannelLines, showZoneBox, zoneOpacity, lineWidth);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.EmaCorridorTrend EmaCorridorTrend(int emaPeriod, int atrPeriod, int preset, int minZoneBars, double minMovePoints, int lookbackOriginBars, int graceBars, int breakConfirmBars, double hardBreakEmaAtr, int windowBars, int slopeBars, int blockBars, double minEmaEfficiency, double minEmaMono, double minEmaSlopeAtr, double minSideFraction, double minGapAtr, double maxCounterCloseAtr, double maxFarDisp, double maxNearDisp, double minPriceR2, bool showChannelLines, bool showZoneBox, int zoneOpacity, int lineWidth)
		{
			return indicator.EmaCorridorTrend(Input, emaPeriod, atrPeriod, preset, minZoneBars, minMovePoints, lookbackOriginBars, graceBars, breakConfirmBars, hardBreakEmaAtr, windowBars, slopeBars, blockBars, minEmaEfficiency, minEmaMono, minEmaSlopeAtr, minSideFraction, minGapAtr, maxCounterCloseAtr, maxFarDisp, maxNearDisp, minPriceR2, showChannelLines, showZoneBox, zoneOpacity, lineWidth);
		}

		public Indicators.EmaCorridorTrend EmaCorridorTrend(ISeries<double> input , int emaPeriod, int atrPeriod, int preset, int minZoneBars, double minMovePoints, int lookbackOriginBars, int graceBars, int breakConfirmBars, double hardBreakEmaAtr, int windowBars, int slopeBars, int blockBars, double minEmaEfficiency, double minEmaMono, double minEmaSlopeAtr, double minSideFraction, double minGapAtr, double maxCounterCloseAtr, double maxFarDisp, double maxNearDisp, double minPriceR2, bool showChannelLines, bool showZoneBox, int zoneOpacity, int lineWidth)
		{
			return indicator.EmaCorridorTrend(input, emaPeriod, atrPeriod, preset, minZoneBars, minMovePoints, lookbackOriginBars, graceBars, breakConfirmBars, hardBreakEmaAtr, windowBars, slopeBars, blockBars, minEmaEfficiency, minEmaMono, minEmaSlopeAtr, minSideFraction, minGapAtr, maxCounterCloseAtr, maxFarDisp, maxNearDisp, minPriceR2, showChannelLines, showZoneBox, zoneOpacity, lineWidth);
		}
	}
}

#endregion
