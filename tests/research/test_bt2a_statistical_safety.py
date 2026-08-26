import json
import pandas as pd
from edgelab.research.bt2a_gate2_first_passage import summarize_scores
from edgelab.research.bt2a_gate_l2 import context_interaction_test,context_width_correlation

def test_all_timeout_summary_is_strict_json():
 value=summarize_scores([0,0]); assert value['p_tp_given_resolved'] is None; json.dumps(value,allow_nan=False)
def test_degenerate_width_is_strict_json():
 frame=pd.DataFrame({'context_group':['G-operable']*3,'zone_width_ticks':[5]*3,'context_as_of_ok':[True]*3}); value=context_width_correlation(frame); assert value['correlation'] is None and not value['passes']; json.dumps(value,allow_nan=False)
def test_context_bootstrap_clusters_shared_sessions():
 rows=[]
 for i in range(4):
  for group,a,c in [('G-operable',.6,.1),('G-stress',.2,.1)]: rows += [{'cme_session':f'S{i}','context_group':group,'arm':'K_ABS','score_fp':a},{'cme_session':f'S{i}','context_group':group,'arm':'N_RAND','score_fp':c}]
 value=context_interaction_test(pd.DataFrame(rows),minimum_sessions_per_group=4,replications=200,seed=3); assert abs(value['point']-.4)<1e-12; assert value['n_cluster_sessions']==4 and value['cluster_resampling']=='CME_SESSION'
