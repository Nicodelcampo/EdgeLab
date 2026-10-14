"""Fixed equal-capacity controls; no model/threshold search or winner promotion."""
import numpy as np
from .phenomena_models import FEATURES
from .zone_model_design import matched_bases
MODELS=('DENSITY','GEOMETRY_CC','GEOMETRY','ARRIVAL_CC','ARRIVAL','INTERACTION_CC','INTERACTION','MIRROR_FULL')
COUNTS={'PRIOR':0,'CONTINUOUS':len(FEATURES),'DENSITY':42,'GEOMETRY_CC':59,'GEOMETRY':59,'ARRIVAL_CC':73,'ARRIVAL':73,'INTERACTION_CC':77,'INTERACTION':77,'MIRROR_FULL':77}

def continuous_bases(x):
    """35 deterministic smooth bases, fixed pre-run; not independent information."""
    x=np.asarray(x,float)
    a=np.tanh(x[:,FEATURES.index('progress:signed_log1p')]);b=np.tanh(x[:,FEATURES.index('prior_progress:signed_log1p')]);c=np.tanh(x[:,FEATURES.index('pressure_ratio:log1p')]);d=np.tanh(x[:,FEATURES.index('trade_count_ratio:log1p')]);e=np.tanh(x[:,FEATURES.index('context_range:log1p')]);f=np.tanh(x[:,FEATURES.index('total_volume_ratio:log1p')])
    cols=[a,b,c,d,e,f]
    terms=[cols[i]*cols[j] for i in range(6) for j in range(i,6)]+[v**3 for v in cols]+[a*b*c,a*b*d,a*c*d,b*c*d,a*e*f,b*e*f,c*e*f,d*e*f]
    return np.column_stack(terms)

def design(x,z,name):
    x=np.asarray(x,float);z=np.asarray(z,float)
    if x.ndim!=2 or x.shape[1]!=len(FEATURES) or z.shape!=(len(x),2,43) or not np.isfinite(x).all() or not np.isfinite(z).all():raise ValueError('aligned finite actual and mirror pair matrices')
    if name=='MIRROR_FULL':return np.column_stack((x,z[:,1]))
    d=z[:,0,:8];g=z[:,0,8:25];a=z[:,0,25:39];interaction=z[:,0,39:]
    if name=='DENSITY':return np.column_stack((x,d))
    cc=continuous_bases(x)
    if name=='GEOMETRY_CC':return np.column_stack((x,d,cc[:,:17]))
    if name=='GEOMETRY':return np.column_stack((x,d,g))
    if name=='ARRIVAL_CC':return np.column_stack((x,d,g,cc[:,17:31]))
    if name=='ARRIVAL':return np.column_stack((x,d,g,a))
    if name=='INTERACTION_CC':return np.column_stack((x,d,g,a,cc[:,31:35]))
    if name=='INTERACTION':return np.column_stack((x,d,g,a,interaction))
    raise ValueError('fixed crossfamily design only')
