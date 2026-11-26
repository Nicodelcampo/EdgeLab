// EdgeLabCarteraBook (2026-11-25): ejecucion por estrategia sobre una cuenta neta. Cada estrategia (sleeve) del coordinador
// tiene SUS ordenes reales: entrada (mercado o stop), stop de proteccion y objetivo (OCO) y salida a mercado. La cuenta queda
// con la suma de las posiciones de las estrategias. Ventajas frente al ajuste de posicion neta al cierre de vela del
// adaptador historico: las entradas salen al cierre de la vela de la senal (no una vela despues), los stops estan en el
// broker (protegen aunque se corte la conexion) y el registro usa los precios reales de ejecucion.
// C# puro (sin tipos de NinjaTrader): el host NT8 (EdgeLabCartera.cs) implementa ICarteraGateway con ordenes unmanaged;
// el arnes tools/nt8_cartera_harness lo implementa con un broker simulado para verificar la logica fuera de NT8.
using System;
using System.Collections.Generic;

namespace NinjaTrader.NinjaScript.Strategies.EdgeLabFundedSync
{
    public enum CarteraOrderType { Market = 0, Stop = 1, Limit = 2 }
    public enum CarteraRole { Entry = 0, Stop = 1, Target = 2, Exit = 3 }

    public interface ICarteraGateway
    {
        /// <summary>Envia la orden `tag` (nombre unico, ya registrado por el libro). side +1 compra, -1 venta.</summary>
        void Submit(CarteraBook book, string tag, CarteraRole role, string sleeveId, int side, int qty, CarteraOrderType type, double price, string oco);
        void Change(CarteraBook book, string tag, int qty, double price);
        void Cancel(CarteraBook book, string tag);
        void Log(string msg);
    }

    internal sealed class SleeveExec
    {
        public string EntryTag, StopTag, TargetTag, ExitTag;
        public int EntrySide, EntryQty;
        public double EntryPrice = double.NaN, StopPx = double.NaN, TargetPx = double.NaN;
        public CarteraOrderType EntryType;
        public bool ExitRequested;
        public string ExitReason;
        public int Seq;
        public string Oco;                 // grupo OCO vivo (stop + objetivo de la posicion abierta); uno nuevo por posicion
        public bool SinObjetivo;           // el broker rechazo el objetivo: la posicion sigue con el stop y la salida de la estrategia
        public bool OcoMuerto;             // el broker cerro el grupo OCO sin pedirlo: se rearma recien en la vela siguiente
    }

    public sealed class CarteraBook
    {
        public readonly int Index;
        public readonly string Root;
        public readonly PortfolioCoordinator Coord;
        public readonly double TickSize;
        public double LastClose = double.NaN;
        public DateTime LastNy;
        private readonly ICarteraGateway _gw;
        private readonly Dictionary<string, SleeveExec> _ex = new Dictionary<string, SleeveExec>();
        private readonly Dictionary<string, KeyValuePair<string, CarteraRole>> _tags = new Dictionary<string, KeyValuePair<string, CarteraRole>>();

        public CarteraBook(int index, string root, PortfolioCoordinator coord, double tickSize, ICarteraGateway gw, bool brokerDriven)
        {
            Index = index; Root = root; Coord = coord; TickSize = tickSize; _gw = gw;
            Coord.BrokerDriven = brokerDriven;
            foreach (string id in Coord.SleeveIds) _ex[id] = new SleeveExec();
        }

        private SleeveExec Ex(string id)
        {
            SleeveExec e;
            if (!_ex.TryGetValue(id, out e)) { e = new SleeveExec(); _ex[id] = e; }
            return e;
        }

        private double Rt(double px) { return Math.Round(px / TickSize, MidpointRounding.AwayFromZero) * TickSize; }

        /// <summary>Senales de la vela que acaba de cerrar y ordenes que corresponden.</summary>
        public void OnBar(BarTimeContext bar)
        {
            LastClose = bar.Close; LastNy = bar.CloseNy;
            Coord.FeedBar(bar);
            Sync();
        }

        /// <summary>Contratos netos que deberia tener la cuenta en este instrumento segun las estrategias abiertas.</summary>
        public int ExpectedNet
        {
            get { int n = 0; foreach (string id in Coord.SleeveIds) { var s = Coord.Sleeves[id]; if (s.IsOpen) n += s.Side * s.Contracts; } return n; }
        }

        public bool AnyWorkingOrOpen
        {
            get
            {
                foreach (string id in Coord.SleeveIds)
                {
                    var s = Coord.Sleeves[id]; var e = Ex(id);
                    if (s.IsOpen || e.EntryTag != null || e.StopTag != null || e.TargetTag != null || e.ExitTag != null) return true;
                }
                return false;
            }
        }

        public void Sync()
        {
            if (!Coord.BrokerDriven) return;                // simulacion virtual (historico de una corrida en vivo): sin ordenes
            foreach (string id in Coord.SleeveIds) SyncSleeve(id);
        }

        // la otra pata del OCO: el broker la cancela solo; se deja de seguir para que una reentrada no la confunda
        private void DropTag(ref string tag)
        {
            if (tag == null) return;
            string t = tag; tag = null; _tags.Remove(t);       // primero se suelta: el aviso de cancelacion ya no es de este libro
            _gw.Cancel(this, t);
        }

        /// <summary>Paso de historico (virtual) a tiempo real: arranca plano, sin posiciones ni ordenes heredadas.</summary>
        public void ResetToFlatBrokerMode()
        {
            foreach (string id in Coord.SleeveIds)
            {
                var s = Coord.Sleeves[id];
                s.IsOpen = false; s.Contracts = 0; s.HasPendingEntry = false; s.PendingEntryIsStopOrder = false;
                s.PendingExitReason = null; s.PendingAbsStop = double.NaN; s.PendingAbsTarget = double.NaN;
                s.StopPrice = double.NaN; s.TargetPrice = double.NaN; s.AppliedW = 0;
                _ex[id] = new SleeveExec();
            }
            _tags.Clear();
            Coord.BrokerDriven = true;
        }

        private int _seq, _ocoSeq, _depth;
        private void Submit(ref string campo, string id, CarteraRole role, int side, int qty, CarteraOrderType type, double price, string oco)
        {
            // el nombre se registra y se asigna al campo ANTES de enviar: NT8 puede rechazar o llenar dentro de la misma llamada
            // (2026-11-25: asignarlo despues dejaba referencias viejas y la estrategia no volvia a operar)
            string tag = Root + "|" + id + "|" + role + "|" + (++_seq).ToString(System.Globalization.CultureInfo.InvariantCulture);
            _tags[tag] = new KeyValuePair<string, CarteraRole>(id, role);
            campo = tag;
            _gw.Submit(this, tag, role, id, side, qty, type, price, oco);
        }

        private void SyncSleeve(string id)
        {
            // un rechazo o fill sincrono vuelve a entrar aca; el limite corta cualquier ida y vuelta (2026-11-25: bucle de OCO reusado)
            if (_depth > 4) { _gw.Log("AVISO sincronizacion anidada cortada en " + Root + " " + id); return; }
            _depth++;
            try { SyncSleeveCore(id); }
            finally { _depth--; }
        }

        private void SyncSleeveCore(string id)
        {
            var sl = Coord.Sleeves[id];
            var e = Ex(id);
            if (sl.IsOpen)
            {
                if (sl.PendingExitReason != null || e.ExitRequested)
                {
                    if (!e.ExitRequested) { e.ExitRequested = true; e.ExitReason = sl.PendingExitReason; }
                    if (e.StopTag != null) _gw.Cancel(this, e.StopTag);
                    if (e.TargetTag != null) _gw.Cancel(this, e.TargetTag);
                    // la salida a mercado sale recien cuando el broker confirmo que no queda ninguna orden de proteccion viva:
                    // si el stop se llena mientras tanto, la estrategia ya quedo cerrada y no se manda nada (sin sobrellenado)
                    if (e.StopTag == null && e.TargetTag == null && e.ExitTag == null)
                        Submit(ref e.ExitTag, id, CarteraRole.Exit, -sl.Side, sl.Contracts, CarteraOrderType.Market, double.NaN, null);
                    return;
                }
                if (e.OcoMuerto)
                {
                    if (e.StopTag != null) { _gw.Cancel(this, e.StopTag); return; }
                    if (e.TargetTag != null) { _gw.Cancel(this, e.TargetTag); return; }
                    e.OcoMuerto = false;
                }
                // un grupo OCO nuevo por posicion: NT8 rechaza un OCO que ya termino (reusarlo era el bucle del 2026-11-25)
                if (e.StopTag == null && e.TargetTag == null) e.Oco = Root + "_" + id + "_" + (++_ocoSeq).ToString(System.Globalization.CultureInfo.InvariantCulture);
                if (!double.IsNaN(sl.StopPrice))
                {
                    double sp = Rt(sl.StopPrice);
                    if (e.StopTag == null) { e.StopPx = sp; Submit(ref e.StopTag, id, CarteraRole.Stop, -sl.Side, sl.Contracts, CarteraOrderType.Stop, sp, e.Oco); }
                    else if (Math.Abs(sp - e.StopPx) > 0.5 * TickSize) { e.StopPx = sp; _gw.Change(this, e.StopTag, sl.Contracts, sp); }
                }
                if (!double.IsNaN(sl.TargetPrice) && !e.SinObjetivo && sl.IsOpen && !e.ExitRequested)
                {
                    double tp = Rt(sl.TargetPrice);
                    if (e.TargetTag == null) { e.TargetPx = tp; Submit(ref e.TargetTag, id, CarteraRole.Target, -sl.Side, sl.Contracts, CarteraOrderType.Limit, tp, e.Oco); }
                    else if (Math.Abs(tp - e.TargetPx) > 0.5 * TickSize) { e.TargetPx = tp; _gw.Change(this, e.TargetTag, sl.Contracts, tp); }
                }
                return;
            }

            if (sl.HasPendingEntry)
            {
                bool isStop = sl.PendingEntryIsStopOrder;
                int side = sl.PendingEntrySide;
                if (e.EntryTag == null)
                {
                    double refPx = isStop ? sl.PendingEntryStopPrice : LastClose;
                    int qty = Coord.PlanEntryQty(sl, refPx);
                    if (qty <= 0) { sl.HasPendingEntry = false; sl.PendingEntryIsStopOrder = false; return; }
                    CarteraOrderType type = CarteraOrderType.Market;
                    double px = double.NaN;
                    if (isStop)
                    {
                        px = Rt(sl.PendingEntryStopPrice);
                        // stop ya atravesado por el cierre: en la simulacion virtual se llena en la apertura siguiente -> mercado
                        if (side * (LastClose - px) >= 0) { type = CarteraOrderType.Market; px = double.NaN; }
                        else type = CarteraOrderType.Stop;
                    }
                    e.EntrySide = side; e.EntryQty = qty; e.EntryType = type; e.EntryPrice = px;
                    Submit(ref e.EntryTag, id, CarteraRole.Entry, side, qty, type, px, null);
                }
                else if (isStop && e.EntryType == CarteraOrderType.Stop)
                {
                    double px = Rt(sl.PendingEntryStopPrice);
                    if (Math.Abs(px - e.EntryPrice) > 0.5 * TickSize) { e.EntryPrice = px; _gw.Change(this, e.EntryTag, e.EntryQty, px); }
                }
            }
            else if (e.EntryTag != null && e.EntryType != CarteraOrderType.Market)
            {
                _gw.Cancel(this, e.EntryTag);          // la estrategia retiro la entrada pendiente (o la cancelo una guarda)
            }
        }

        public bool Owns(string tag) { return tag != null && _tags.ContainsKey(tag); }

        /// <summary>El broker lleno (por completo) la orden `tag` a avgPx.</summary>
        public void OnFilled(string tag, double avgPx, int qty, DateTime ny)
        {
            KeyValuePair<string, CarteraRole> m;
            if (!_tags.TryGetValue(tag, out m)) return;
            _tags.Remove(tag);
            string id = m.Key; var sl = Coord.Sleeves[id]; var e = Ex(id);
            switch (m.Value)
            {
                case CarteraRole.Entry:
                    e.EntryTag = null;
                    if (sl.IsOpen) { _gw.Log("AVISO entrada llenada con la estrategia ya abierta: " + id); break; }
                    sl.PendingEntrySide = e.EntrySide;
                    Coord.ConfirmEntry(sl, avgPx, qty, ny);
                    e.ExitRequested = false; e.ExitReason = null; e.SinObjetivo = false; e.OcoMuerto = false;
                    break;
                case CarteraRole.Stop:
                    e.StopTag = null;
                    DropTag(ref e.TargetTag);
                    if (sl.IsOpen) Coord.ConfirmExit(sl, avgPx, ny, sl.OverlayBeActivated ? "BE_STOP" : "STOP");
                    e.ExitRequested = false; e.OcoMuerto = false; e.Seq++;
                    break;
                case CarteraRole.Target:
                    e.TargetTag = null;
                    DropTag(ref e.StopTag);
                    if (sl.IsOpen) Coord.ConfirmExit(sl, avgPx, ny, "TARGET");
                    e.ExitRequested = false; e.OcoMuerto = false; e.Seq++;
                    break;
                case CarteraRole.Exit:
                    e.ExitTag = null;
                    if (sl.IsOpen) Coord.ConfirmExit(sl, avgPx, ny, e.ExitReason ?? "EXIT");
                    e.ExitRequested = false; e.ExitReason = null; e.Seq++;
                    break;
            }
            SyncSleeve(id);
        }

        /// <summary>La orden `tag` termino sin llenarse (cancelada o rechazada).</summary>
        public void OnTerminal(string tag, bool rejected)
        {
            KeyValuePair<string, CarteraRole> m;
            if (!_tags.TryGetValue(tag, out m)) return;
            _tags.Remove(tag);
            string id = m.Key; var sl = Coord.Sleeves[id]; var e = Ex(id);
            switch (m.Value)
            {
                case CarteraRole.Entry:
                    e.EntryTag = null;
                    if (rejected) _gw.Log("ENTRADA RECHAZADA " + Root + " " + id);
                    sl.HasPendingEntry = false; sl.PendingEntryIsStopOrder = false;
                    break;
                case CarteraRole.Stop:
                    e.StopTag = null;
                    if (rejected && sl.IsOpen && !e.ExitRequested)
                    {
                        _gw.Log("STOP RECHAZADO " + Root + " " + id + ": salida a mercado");
                        e.ExitRequested = true; e.ExitReason = "STOP_RECHAZADO";
                    }
                    else if (!rejected && !e.ExitRequested)
                    {
                        // cancelacion no pedida = el broker cerro el grupo OCO (normalmente porque la otra pata se lleno y el aviso
                        // del fill todavia no llego). No se toca nada ahora: si llega el fill, cierra la posicion; si no, la vela
                        // siguiente cancela lo que quede y arma un grupo nuevo.
                        e.OcoMuerto = true;
                        return;
                    }
                    break;
                case CarteraRole.Target:
                    e.TargetTag = null;
                    if (rejected)
                    {
                        // no se reenvia en la misma llamada (bucle): la posicion sigue con su stop y la salida de la estrategia
                        _gw.Log("OBJETIVO RECHAZADO " + Root + " " + id + ": sigue con el stop");
                        e.SinObjetivo = true;
                    }
                    else if (!e.ExitRequested)
                    {
                        e.OcoMuerto = true;
                        return;
                    }
                    break;
                case CarteraRole.Exit:
                    e.ExitTag = null;
                    if (rejected) _gw.Log("SALIDA RECHAZADA " + Root + " " + id + ": se reintenta en la proxima vela");
                    break;
            }
            if (!(m.Value == CarteraRole.Exit && rejected)) SyncSleeve(id);
        }

        /// <summary>Cierra todo el libro (guardas del host).</summary>
        public void FlattenAll(string reason)
        {
            Coord.ForceFlattenAll(LastClose, LastNy, reason);
            Sync();
        }
    }
}
