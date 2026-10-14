"""Fixed continuous/context representations, no search or winner promotion."""
import numpy as np
from .phenomena_models import FEATURES
from .zone_context import DENSITY_NAMES, GEOMETRY_NAMES, ARRIVAL_NAMES

MODELS = ('PRIOR','CONTINUOUS','DENSITY','GEOMETRY_CC','GEOMETRY', 'ARRIVAL_CC','ARRIVAL')
INDEX = {name:i for i,name in enumerate(FEATURES)}


def matched_bases(x):
    """Eight outcome-free bases, fixed components and scales (not fitted knots)."""
    x=np.asarray(x,float)
    if x.ndim!=2 or x.shape[1]!=len(FEATURES) or not np.isfinite(x).all():raise ValueError('fixed continuous matrix')
    a=np.tanh(x[:,INDEX['progress:signed_log1p']]);b=np.tanh(x[:,INDEX['prior_progress:signed_log1p']])
    c=np.tanh(x[:,INDEX['pressure_ratio:log1p']]);d=np.tanh(x[:,INDEX['trade_count_ratio:log1p']])
    return np.column_stack((a*b,a*c,b*c,a*d,b*d,c*d,a*a,b*b))


def design(x, density, geometry, arrival, name):
    x=np.asarray(x,float);d=np.asarray(density,float);g=np.asarray(geometry,float);a=np.asarray(arrival,float)
    if x.ndim!=2 or x.shape[1]!=len(FEATURES) or any(v.shape!=(len(x),n) for v,n in ((d,8),(g,4),(a,4))) or not all(np.isfinite(v).all() for v in (x,d,g,a)):raise ValueError('aligned finite context matrices')
    if name=='CONTINUOUS':return x
    if name=='DENSITY':return np.column_stack((x,d))
    cc=matched_bases(x)
    if name=='GEOMETRY_CC':return np.column_stack((x,d,cc[:,:4]))
    if name=='GEOMETRY':return np.column_stack((x,d,g))
    if name=='ARRIVAL_CC':return np.column_stack((x,d,g,cc[:,4:]))
    if name=='ARRIVAL':return np.column_stack((x,d,g,a))
    raise ValueError('fixed zone design name')

FEATURE_COUNTS={ 'PRIOR':0, 'CONTINUOUS':len(FEATURES),'DENSITY':len(FEATURES)+8,
                'GEOMETRY_CC':len(FEATURES)+12,'GEOMETRY':len(FEATURES)+12,
                'ARRIVAL_CC':len(FEATURES)+16,'ARRIVAL':len(FEATURES)+16 }
