// EdgeLab Tick History: prueba y descarga de historia de ticks (trades con bid/ask vigente) desde el servidor de
// datos historicos de la conexion activa de NT8. Complementa al Replay Downloader (L2): este no pide Market Replay,
// pide barras de 1 tick con BarsRequest.
//
// Salida: <root>\<CONTRATO>\<yyyyMMdd>.Last.utc.txt, formato .Last.txt de NT8 (yyyyMMdd HHmmss fffffff;last;bid;ask;volume)
// pero con la hora en UTC DECLARADA (el export nativo de NT8 usa la zona de la UI y hubo que verificarla aparte), mas
// <root>\<CONTRATO>\manifest.jsonl con una linea por dia (ticks, primer/ultimo tick UTC, zona de NT8, sha256).
//
// Reglas: solo fechas ANTERIORES al holdout (2026-07-01, fail-closed). Escritura atomica (.partial -> rename). Un dia
// sin datos se registra como NO_DATA, nunca como archivo vacio. "Probar" pide un dia por semana y no escribe ticks.
#region Using declarations
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using NinjaTrader.Cbi;
using NinjaTrader.Core;
using NinjaTrader.Data;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
#endregion
namespace NinjaTrader.Gui.NinjaScript
{
 public class EdgeLabTickHistoryAddOn : AddOnBase
 {
  NTMenuItem item, tools;
  protected override void OnStateChange(){if(State==State.SetDefaults){Name="EdgeLab Tick History";Description="Prueba y descarga de historia de ticks pre-holdout.";}}
  protected override void OnWindowCreated(Window w){ControlCenter c=w as ControlCenter;if(c==null)return;tools=c.FindFirst("ControlCenterMenuItemTools") as NTMenuItem;if(tools==null)return;item=new NTMenuItem{Header="EdgeLab Tick History",Style=Application.Current.TryFindResource("MainMenuItem") as Style};tools.Items.Add(item);item.Click+=Open;}
  protected override void OnWindowDestroyed(Window w){if(item==null||!(w is ControlCenter))return;item.Click-=Open;if(tools!=null&&tools.Items.Contains(item))tools.Items.Remove(item);item=null;tools=null;}
  void Open(object s,RoutedEventArgs e){Globals.RandomDispatcher.BeginInvoke(new Action(()=>new EdgeLabTickHistoryWindow().Show()));}
 }

 public class EdgeLabTickHistoryWindow:NTWindow,IWorkspacePersistence
 {
  const string Build="EDGE_TICKHIST_V1";
  static readonly DateTime HoldoutStart=new DateTime(2026,7,1);
  static readonly Regex ContractRx=new Regex(@"^[A-Za-z0-9]{1,8}\s+[0-9]{2}-[0-9]{2}$",RegexOptions.Compiled);
  const int TimeoutSeconds=600;
  TextBox contracts,from,to,root,log;Button probe,download,stop;volatile bool running,cancel;
  public WorkspaceOptions WorkspaceOptions{get;set;}
  public void Restore(System.Xml.Linq.XDocument d,System.Xml.Linq.XElement e){}
  public void Save(System.Xml.Linq.XDocument d,System.Xml.Linq.XElement e){}

  public EdgeLabTickHistoryWindow()
  {
   Caption="EdgeLab Tick History";Width=720;Height=600;Content=Ui();
   Loaded+=(o,e)=>{if(WorkspaceOptions==null)WorkspaceOptions=new WorkspaceOptions("EdgeLabTickHistory-"+Guid.NewGuid().ToString("N"),this);};
  }

  DependencyObject Ui()
  {
   double m=(double)FindResource("MarginBase");Grid g=new Grid{Margin=new Thickness(m)};
   g.RowDefinitions.Add(new RowDefinition{Height=GridLength.Auto});g.RowDefinitions.Add(new RowDefinition{Height=GridLength.Auto});g.RowDefinitions.Add(new RowDefinition{Height=new GridLength(1,GridUnitType.Star)});
   StackPanel f=new StackPanel();
   contracts=Field(f,m,"Contratos exactos, separados por ; (ej: ES 06-25;ES 09-25):","");
   from=Field(f,m,"Desde, inclusive (yyyy-MM-dd):","");
   to=Field(f,m,"Hasta, inclusive (yyyy-MM-dd, anterior al 2026-07-01):","2026-06-30");
   root=Field(f,m,"Carpeta de salida (no usar el disco C):",@"E:\DatosNT8\tick_history");
   Grid.SetRow(f,0);g.Children.Add(f);
   StackPanel b=new StackPanel{Orientation=Orientation.Horizontal,Margin=new Thickness(m)};
   probe=new Button{Content="_Probar (1 dia por semana, sin escribir)",Padding=new Thickness(m,2,m,2),Margin=new Thickness(0,0,m,0)};
   download=new Button{Content="_Descargar",Padding=new Thickness(m,2,m,2),Margin=new Thickness(0,0,m,0)};
   stop=new Button{Content="_Parar",Padding=new Thickness(m,2,m,2),IsEnabled=false};
   probe.Click+=(o,e)=>Start(true);download.Click+=(o,e)=>Start(false);stop.Click+=(o,e)=>{cancel=true;Log("Parando despues del dia en curso...");};
   b.Children.Add(probe);b.Children.Add(download);b.Children.Add(stop);Grid.SetRow(b,1);g.Children.Add(b);
   log=new TextBox{Margin=new Thickness(m),IsReadOnly=true,AcceptsReturn=true,VerticalScrollBarVisibility=ScrollBarVisibility.Auto,HorizontalScrollBarVisibility=ScrollBarVisibility.Auto,FontFamily=new FontFamily("Consolas")};
   Grid.SetRow(log,2);g.Children.Add(log);return g;
  }

  TextBox Field(Panel p,double m,string label,string value)
  {
   p.Children.Add(new Label{Content=label,Foreground=FindResource("FontLabelBrush") as Brush,Margin=new Thickness(m,m,m,0)});
   TextBox t=new TextBox{Text=value,Margin=new Thickness(m,0,m,0)};p.Children.Add(t);return t;
  }

  void Log(string x){Dispatcher.InvokeAsync(new Action(()=>{if(log==null)return;log.AppendText(DateTime.Now.ToString("HH:mm:ss",CultureInfo.InvariantCulture)+"  "+x+Environment.NewLine);log.ScrollToEnd();}));}
  void Running(bool x){running=x;Dispatcher.InvokeAsync(new Action(()=>{probe.IsEnabled=!x;download.IsEnabled=!x;stop.IsEnabled=x;}));}

  void Start(bool probeOnly)
  {
   if(running)return;
   List<string> list=new List<string>();
   foreach(string x in contracts.Text.Split(new[]{';'},StringSplitOptions.RemoveEmptyEntries))
   {string c=x.Trim().ToUpperInvariant();if(!ContractRx.IsMatch(c)){Log("ERROR: hace falta el contrato exacto, no '"+c+"'");return;}if(!list.Contains(c))list.Add(c);}
   if(list.Count<1||list.Count>20){Log("ERROR: entre 1 y 20 contratos");return;}
   DateTime a,z;
   if(!DateTime.TryParseExact(from.Text.Trim(),"yyyy-MM-dd",CultureInfo.InvariantCulture,DateTimeStyles.None,out a)||!DateTime.TryParseExact(to.Text.Trim(),"yyyy-MM-dd",CultureInfo.InvariantCulture,DateTimeStyles.None,out z)||a>z)
   {Log("ERROR: fechas invalidas");return;}
   if(z>=HoldoutStart){Log("ERROR: 'Hasta' toca el holdout (desde 2026-07-01). Esta herramienta es solo para historia pre-holdout.");return;}
   string dir=root.Text.Trim();
   if(!probeOnly&&(dir.Length==0||!Path.IsPathRooted(dir))){Log("ERROR: la carpeta de salida tiene que ser una ruta absoluta");return;}
   if(!probeOnly&&dir.StartsWith("C:",StringComparison.OrdinalIgnoreCase)){Log("ERROR: no escribir en el disco C");return;}
   cancel=false;Running(true);
   Thread t=new Thread(()=>Run(list,a.Date,z.Date,dir,probeOnly));t.IsBackground=true;t.Start();
  }

  void Run(List<string> list,DateTime a,DateTime z,string dir,bool probeOnly)
  {
   TimeZoneInfo tz=Globals.GeneralOptions.TimeZoneInfo;
   Log((probeOnly?"PROBAR ":"DESCARGAR ")+string.Join(";",list)+" "+a.ToString("yyyy-MM-dd")+" -> "+z.ToString("yyyy-MM-dd")+"  (zona de NT8: "+tz.Id+"; las salidas se escriben en UTC)");
   try
   {
    foreach(string contract in list)
    {
     if(cancel)break;
     Instrument inst=Instrument.GetInstrument(contract,true);
     if(inst==null){Log("ERROR: NT8 no conoce el contrato "+contract);continue;}
     string cdir=Path.Combine(dir,contract.Replace(' ','_'));
     if(!probeOnly)Directory.CreateDirectory(cdir);
     long total=0;int withData=0,noData=0;string first=null,last=null;
     for(DateTime w0=a;w0<=z&&!cancel;w0=w0.AddDays(probeOnly?7:1))
     {
      DateTime d=w0;
      if(probeOnly)while(d.DayOfWeek==DayOfWeek.Saturday||d.DayOfWeek==DayOfWeek.Sunday)d=d.AddDays(1);   // probar siempre un dia habil
      if(d>z||d.DayOfWeek==DayOfWeek.Saturday)continue;
      string day=d.ToString("yyyyMMdd",CultureInfo.InvariantCulture);
      string outPath=Path.Combine(cdir,day+".Last.utc.txt");
      if(!probeOnly&&File.Exists(outPath)){Log("SKIP "+contract+" "+day+" (ya existe)");continue;}
      string err;List<double[]> rows;List<DateTime> times;
      if(!Fetch(inst,d,d.AddDays(1),out times,out rows,out err)){Log("ERROR "+contract+" "+day+" "+err);continue;}
      if(times.Count==0){noData++;Log("NO_DATA "+contract+" "+day);if(!probeOnly)Manifest(cdir,contract,day,"NO_DATA",0,null,null,null,tz);continue;}
      withData++;total+=times.Count;
      DateTime u0=ToUtc(times[0],tz);
      DateTime u1=ToUtc(times[times.Count-1],tz);
      if(first==null)first=day;last=day;
      if(probeOnly){Log("OK "+contract+" "+day+" ticks="+times.Count.ToString("N0",CultureInfo.InvariantCulture)+" UTC "+u0.ToString("HH:mm")+"-"+u1.ToString("HH:mm"));continue;}
      string sha=Write(outPath,times,rows,tz);
      Manifest(cdir,contract,day,"OK",times.Count,u0,u1,sha,tz);
      Log("OK "+contract+" "+day+" ticks="+times.Count.ToString("N0",CultureInfo.InvariantCulture));
     }
     Log("== "+contract+": dias con datos="+withData+", sin datos="+noData+", ticks="+total.ToString("N0",CultureInfo.InvariantCulture)+(first!=null?", primer dia con datos="+first+", ultimo="+last:""));
    }
   }
   catch(Exception ex){Log("ERROR inesperado: "+ex.Message);}
   finally{Log("-- terminado --");Running(false);}
  }

  // Un dia calendario en la zona de NT8: [d, d+1). Se filtra por hora para no duplicar ticks del borde.
  bool Fetch(Instrument inst,DateTime d0,DateTime d1,out List<DateTime> times,out List<double[]> rows,out string err)
  {
   times=new List<DateTime>();rows=new List<double[]>();err=null;
   List<DateTime> tt=times;List<double[]> rr=rows;string e2=null;bool done=false;
   ManualResetEventSlim ev=new ManualResetEventSlim(false);
   BarsRequest req=new BarsRequest(inst,d0,d1);
   req.BarsPeriod=new BarsPeriod{BarsPeriodType=BarsPeriodType.Tick,Value=1};
   req.TradingHours=TradingHours.Get("Default 24 x 7");
   req.MergePolicy=MergePolicy.DoNotMerge;
   try
   {
    req.Request((r,code,msg)=>
    {
     try
     {
      if(code!=ErrorCode.NoError){e2=code+" "+msg;return;}
      Bars bars=r.Bars;
      for(int i=0;i<bars.Count;i++)
      {
       DateTime t=bars.GetTime(i);
       if(t<d0||t>=d1)continue;
       tt.Add(t);rr.Add(new[]{bars.GetClose(i),bars.GetBid(i),bars.GetAsk(i),(double)bars.GetVolume(i)});
      }
      done=true;
     }
     catch(Exception ex){e2=ex.Message;}
     finally{ev.Set();}
    });
    if(!ev.Wait(TimeSpan.FromSeconds(TimeoutSeconds))){err="TIMEOUT";return false;}
   }
   finally{req.Dispose();}   // ev no se libera: si hubo timeout, el callback tardio todavia puede llamar a Set()
   if(e2!=null){err=e2;return false;}
   if(!done){err="sin respuesta";return false;}
   return true;
  }

  // Hora de NT8 -> UTC restando el offset de su zona. No usa ConvertTimeToUtc, que lanza excepcion en la hora que no
  // existe al pasar a horario de verano.
  static DateTime ToUtc(DateTime t,TimeZoneInfo tz){return new DateTime(t.Ticks-tz.GetUtcOffset(t).Ticks,DateTimeKind.Utc);}

  static string Write(string path,List<DateTime> times,List<double[]> rows,TimeZoneInfo tz)
  {
   string part=path+".partial";
   using(StreamWriter w=new StreamWriter(part,false,new UTF8Encoding(false)))
   {
    for(int i=0;i<times.Count;i++)
    {
     DateTime u=ToUtc(times[i],tz);
     long frac=u.Ticks%TimeSpan.TicksPerSecond;
     double[] v=rows[i];
     w.Write(u.ToString("yyyyMMdd HHmmss",CultureInfo.InvariantCulture));w.Write(' ');w.Write(frac.ToString("0000000",CultureInfo.InvariantCulture));
     w.Write(';');w.Write(v[0].ToString("R",CultureInfo.InvariantCulture));w.Write(';');w.Write(v[1].ToString("R",CultureInfo.InvariantCulture));
     w.Write(';');w.Write(v[2].ToString("R",CultureInfo.InvariantCulture));w.Write(';');w.Write(((long)v[3]).ToString(CultureInfo.InvariantCulture));w.Write('\n');
    }
   }
   if(File.Exists(path))File.Delete(path);
   File.Move(part,path);
   using(SHA256 h=SHA256.Create())using(FileStream fs=File.OpenRead(path)){return BitConverter.ToString(h.ComputeHash(fs)).Replace("-","").ToLowerInvariant();}
  }

  static void Manifest(string cdir,string contract,string day,string status,int ticks,DateTime? u0,DateTime? u1,string sha,TimeZoneInfo tz)
  {
   string line="{\"build\":\""+Build+"\",\"observed_at_utc\":\""+DateTime.UtcNow.ToString("o",CultureInfo.InvariantCulture)+"\",\"contract\":\""+contract+"\",\"day_nt_local\":\""+day
    +"\",\"nt_timezone\":\""+tz.Id+"\",\"output_timezone\":\"UTC\",\"status\":\""+status+"\",\"ticks\":"+ticks.ToString(CultureInfo.InvariantCulture)
    +",\"first_utc\":"+(u0.HasValue?"\""+u0.Value.ToString("o",CultureInfo.InvariantCulture)+"\"":"null")
    +",\"last_utc\":"+(u1.HasValue?"\""+u1.Value.ToString("o",CultureInfo.InvariantCulture)+"\"":"null")
    +",\"sha256\":"+(sha!=null?"\""+sha+"\"":"null")+"}";
   File.AppendAllText(Path.Combine(cdir,"manifest.jsonl"),line+"\n",new UTF8Encoding(false));
  }
 }
}
