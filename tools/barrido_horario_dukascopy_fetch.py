"""Descarga de ticks de XAU/USD de Dukascopy (solo las horas UTC que cubren la franja 04:15 CT). Uso: python tools/barrido_horario_dukascopy_fetch.py AAAA-MM-DD AAAA-MM-DD etiqueta  (escribe en ./raw/). Límite de velocidad fuerte: pausas de 5 s y reintentos de 30 s."""
import os,sys,time,subprocess,datetime as dt
from zoneinfo import ZoneInfo
CHI=ZoneInfo('America/Chicago');UTC=dt.timezone.utc
def hours_for(d):
    b=dt.datetime(d.year,d.month,d.day,4,15,tzinfo=CHI).astimezone(UTC)   # franja 04:15 CT
    lo=(b-dt.timedelta(minutes=17)).replace(minute=0,second=0);hi=(b+dt.timedelta(minutes=2+15+1)).replace(minute=0,second=0)
    hs=[];t=lo
    while t<=hi:hs.append(t.hour);t+=dt.timedelta(hours=1)
    return hs
def run(start,end,tag):
    d=start;n=ok=0;sleep=5.0
    while d<=end:
        if d.weekday()<5:
            for h in hours_for(d):
                fn=f'raw/{d:%Y%m%d}_{h:02d}.bi5'
                if os.path.exists(fn):continue
                url=f'https://datafeed.dukascopy.com/datafeed/XAUUSD/{d.year}/{d.month-1:02d}/{d.day:02d}/{h:02d}h_ticks.bi5'
                for attempt in range(12):
                    r=subprocess.run(['curl','-sS','-m','40','-o',fn+'.tmp','-w','%{http_code}',url],capture_output=True,text=True);c=r.stdout.strip()
                    if c=='200':os.rename(fn+'.tmp',fn);ok+=1;sleep=5.0;break
                    if c=='404':open(fn,'wb').close();break
                    time.sleep(30)
                n+=1;time.sleep(sleep)
                if n%20==0:print(tag,d,'n',n,'ok',ok,'sleep',round(sleep,1),flush=True)
        d+=dt.timedelta(days=1)
    print(tag,'fin','n',n,'ok',ok,flush=True)
if __name__=='__main__':
    run(dt.date.fromisoformat(sys.argv[1]),dt.date.fromisoformat(sys.argv[2]),sys.argv[3])
