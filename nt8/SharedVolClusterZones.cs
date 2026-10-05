// ============================================================================
// SharedVolClusterZones.cs - Repositorio compartido de zonas de volumen
// Permite que indicadores externos (ej. aVolMetaCluster) consuman las zonas
// detectadas por aVolClusterPOI de forma desacoplada y con cero costo de CPU.
// ============================================================================

using System;
using System.Collections.Generic;

namespace NinjaTrader.NinjaScript.Indicators
{
	public class SharedClusterZone
	{
		public long Id;
		public int CreatedBar;
		public int StartBar;
		public int InvalidatedBar;
		public long LowerTick;
		public long UpperTick;
		public int Direction;       // +1 Soporte, -1 Resistencia, 0 At-Price
		public string Kind;          // OFF_PRICE | AT_PRICE
		public double Score;
		public double Quality;
		public double AnomalyRatio;
		public bool Active;
	}

	public static class SharedVolClusterZones
	{
		private static readonly object _gate = new object();
		private static readonly Dictionary<string, List<SharedClusterZone>> _store = new Dictionary<string, List<SharedClusterZone>>();

		public static void PublishZone(string instrument, SharedClusterZone zone)
		{
			if (string.IsNullOrEmpty(instrument) || zone == null) return;
			lock (_gate)
			{
				List<SharedClusterZone> list;
				if (!_store.TryGetValue(instrument, out list))
				{
					list = new List<SharedClusterZone>();
					_store[instrument] = list;
				}
				list.Add(zone);
				if (list.Count > 2000)
					list.RemoveAt(0);
			}
		}

		public static void InvalidateZone(string instrument, long zoneId, int bar)
		{
			if (string.IsNullOrEmpty(instrument)) return;
			lock (_gate)
			{
				List<SharedClusterZone> list;
				if (_store.TryGetValue(instrument, out list))
				{
					for (int i = list.Count - 1; i >= 0; i--)
					{
						if (list[i].Id == zoneId)
						{
							list[i].Active = false;
							list[i].InvalidatedBar = bar;
							break;
						}
					}
				}
			}
		}

		public static List<SharedClusterZone> GetZones(string instrument)
		{
			if (string.IsNullOrEmpty(instrument)) return new List<SharedClusterZone>();
			lock (_gate)
			{
				List<SharedClusterZone> list;
				if (!_store.TryGetValue(instrument, out list))
					return new List<SharedClusterZone>();
				return new List<SharedClusterZone>(list);
			}
		}

		public static void Clear(string instrument)
		{
			if (string.IsNullOrEmpty(instrument)) return;
			lock (_gate)
			{
				if (_store.ContainsKey(instrument))
					_store[instrument].Clear();
			}
		}
	}
}
