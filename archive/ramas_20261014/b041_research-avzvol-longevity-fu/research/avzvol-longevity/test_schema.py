import ast,csv,io,json
from pathlib import Path
from feature_schema import attach_features,FEATURE_NAMES,validate
P=Path('/data/analysis/avzvol-longevity');tree=ast.parse((P/'run.py').read_text());head=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='HEAD' for t in n.targets));assert head[15:31]==list(FEATURE_NAMES)
checks=0
for hour in range(24):
 v=[7,3,4,.37,41.,9.,2,1.7,8.,.25,.7,-.4,.9,20,2031,730.];r={k:0 for k in head if k not in FEATURE_NAMES};r['hour']=hour;r['status']='TARGET_FIRST';r['source_trigger_sequence']=901
 attach_features(r,v);out=io.StringIO();w=csv.DictWriter(out,fieldnames=head);w.writeheader();w.writerow(r);out.seek(0);read=next(csv.DictReader(out));assert int(read['hour'])==hour and read['status']=='TARGET_FIRST' and int(read['source_trigger_sequence'])==901
 for name,value in zip(FEATURE_NAMES,v):assert float(read[name])==value;checks+=1
for key,value in [('hour',24),('visits1',-1),('proxy_coverage',1.1),('age_bars',.5)]:
 r={'hour':12};attach_features(r,v);r[key]=value
 try:validate(r)
 except AssertionError:checks+=1
 else:raise AssertionError((key,'INVALID_ACCEPTED'))
assert 'HEAD[16:32]' not in (P/'run.py').read_text()
(P/'schema-test-evidence.json').write_text(json.dumps({'status':'PASS','named_feature_checks':checks,'csv_roundtrip_all_hours':True,'metadata_not_overwritten':True,'invalid_ranges_rejected':True},indent=2)+'\n');print('SCHEMA_PASS',checks)
