import numpy as np,pandas as pd
from pullback import detect,NS

def fixture(short=False):
 n=635;c=np.full(n,100.);l=np.full(n,99.);h=np.full(n,101.);e20=np.full(n,95.);e50=np.full(n,90.);e200=np.full(n,80.)
 if short:c=200-c;l,h=200-h,200-l;e20=200-e20;e50=200-e50;e200=200-e200
 return pd.DataFrame(dict(c=c,l=l,h=h,e20=e20,e50=e50,e200=e200,mom_atr_prev=np.ones(n)*10,bucket=np.arange(n),date=['20251007']*n,minute=[650]*n,close_ns=np.arange(n)*60*NS))
def test_touch_reclaim_previous_level():
 b=fixture();b.loc[601,'l']=94;raw,s=detect(b,'X','X',{'20251007'},1);assert len(raw)==1 and len(s)==1 and s[0]['signal_ns']==601*60*NS
def test_no_arm_no_signal():
 b=fixture();b['l']=94;raw,s=detect(b,'X','X',{'20251007'},1);assert not raw and not s
def test_short_symmetry():
 b=fixture(True);b.loc[601,'h']=106;raw,s=detect(b,'X','X',{'20251007'},1);assert len(s)==1 and s[0]['direction']==-1
def test_gap_resets():
 b=fixture();b.loc[601,'l']=94;b.loc[601,'bucket']=700;raw,s=detect(b,'X','X',{'20251007'},1);assert not s
def test_no_duplicate_episode():
 b=fixture();b.loc[601:610,'l']=94;raw,s=detect(b,'X','X',{'20251007'},1);assert len(raw)==1

def test_reserve_base_then_subset():
 b=fixture();b.loc[[601,603,633],'l']=94;raw,s=detect(b,'X','X',{'20251007'},1);assert len(raw)==3 and len(s)==2;assert all(x['separated'] for x in s)
def test_prefix_stability():
 b=fixture();b.loc[[601,633],'l']=94;raw,s=detect(b,'X','X',{'20251007'},1);_,ss=detect(b.iloc[:620],'X','X',{'20251007'},1);assert ss==[x for x in s if x['signal_ns']<=619*60*NS]
def test_ten_bar_episode_expiry():
 b=fixture();b.loc[601:612,'l']=94;b.loc[601:611,'c']=94;b['e200']=80;b['e50']=90;raw,s=detect(b,'X','X',{'20251007'},1);assert not s

def test_summary_json_serialization_both_support_cases():
 import json
 from pullback import summarize
 days=[str(i) for i in range(60)]
 for per_day,expected in [(1,False),(5,True)]:
  rows=[{'day':d,'contract':'X','separated':True} for d in days for j in range(per_day)]
  summary=summarize(rows,rows,days)
  assert type(summary['frequency_support']) is bool
  assert summary['frequency_support'] is expected
  assert json.loads(json.dumps(summary,allow_nan=False))==summary
