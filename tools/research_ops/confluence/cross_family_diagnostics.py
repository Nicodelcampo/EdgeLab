"""Finite public-code reason codes only; arbitrary exception text never exported."""
import ast,hashlib
from pathlib import Path
MODULES=('cross_family_scene','session_primitives','bt2_stream','bt2a_stream','avz_stream','detector_capture','kaggle_session_reader')
SUBSTAGES=('READ_SESSION','CLASSIFY','BUILD_PRIMITIVES','NATIVE_AVZP2','NATIVE_BT2','NATIVE_BT2A','CAPTURE','GROUP_EVENTS','DONE')

def reasons():
 out={}
 for mod in MODULES:
  tree=ast.parse((Path(__file__).parent/(mod+'.py')).read_bytes())
  for node in ast.walk(tree):
   if isinstance(node,ast.Raise) and isinstance(node.exc,ast.Call) and isinstance(node.exc.func,ast.Name) and node.exc.func.id in ('ValueError','TimeoutError') and len(node.exc.args)==1 and isinstance(node.exc.args[0],ast.Constant) and isinstance(node.exc.args[0].value,str):
    text=node.exc.args[0].value;out[text]='PUBLIC_CODE_'+hashlib.sha256(text.encode()).hexdigest()[:16]
 return out

def safe_failure(exc,progress):
 codes=reasons();code=codes.get(str(exc),'UNCLASSIFIED_STATIC_REASON') if type(exc) in (ValueError,TimeoutError) else 'UNCLASSIFIED_EXCEPTION'
 out={'exception_type':type(exc).__name__ if type(exc) in (ValueError,TimeoutError,MemoryError) else 'UNCLASSIFIED_EXCEPTION','reason_code':code,'native_substage':progress.get('substage') if progress.get('substage') in SUBSTAGES else 'UNCLASSIFIED_SUBSTAGE','profile_index':progress.get('profile_index') if type(progress.get('profile_index')) is int and 0<=progress['profile_index']<9 else None}
 for field in ('capture_records_retained','capture_records_by_kind'):
  value=progress.get(field)
  if field.endswith('by_kind'):
   out[field]={k:v for k,v in (value or {}).items() if k in ('BIRTH','REMOVE','TOUCH','CLASSIFY') and type(v) is int and 0<=v<=1000000000}
  else:out[field]=value if type(value) is int and 0<=value<=1000000000 else None
 return out
