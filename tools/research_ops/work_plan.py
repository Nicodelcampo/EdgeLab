"""Frozen longevity work-unit inventory. Metadata planning only, not execution.
Matches the current 18 detector/geometry families without changing scientific
rules. No outputs, source certification, authorization or completion inferred.
"""
from dataclasses import dataclass,asdict
import hashlib,itertools,json,re

@dataclass(frozen=True)
class CampaignIdentity:
    contract: str
    source_sha256: str
    selection_sha256: str
    code_sha256: str
    protocol_sha256: str
    authorization_sha256: str
    risk_review_sha256: str
    def validate(self):
        if not isinstance(self.contract,str) or not re.fullmatch(r'MNQ_(03|06|09|12)-[0-9]{2}',self.contract):raise ValueError('explicit MNQ contract required')
        for key,value in asdict(self).items():
            if key=='contract':continue
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ValueError('external fixed identity hashes required')

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def build_work_plan(identity,*,max_attempts,seconds_per_attempt,memory_bytes_per_worker):
    identity.validate()
    for value,minimum,maximum in [(max_attempts,18,36),(seconds_per_attempt,1,86400),(memory_bytes_per_worker,1,16*1024**3)]:
        if type(value) is not int or not minimum<=value<=maximum:raise ValueError('explicit bounded resource budget required')
    # Physical preparation and existing analysis dependencies remain separate.
    # Fingerprints may identify future checkpoints, but hashes don't approve jobs.
    units=[]
    for (percentile,width),(minimum,window) in itertools.product([(80,5),(90,5),(80,10)],itertools.product([8,18],[1000,2000,3000])):
        family=f'P{percentile}_W{width}_R{minimum}_{window}_20'
        content=dict(schema='longevity_family_v1',identity=asdict(identity),family=family,percentile=percentile,detection_window=width,min_zones=minimum,racimo_window=window,height_ticks=20)
        fingerprint=digest(content)
        units.append(dict(unit_id=identity.contract+'-'+family,fingerprint=fingerprint,spec=content,status='PLANNED_UNAUTHORIZED',complete=False))
    plan=dict(schema='research_ops_frozen_work_plan_v1',identity=asdict(identity),units=units,unit_count=18,max_attempts=max_attempts,seconds_per_attempt=seconds_per_attempt,maximum_reserved_seconds=max_attempts*seconds_per_attempt,memory_bytes_per_worker=memory_bytes_per_worker,maximum_concurrent_workers=1,execution_allowed=False,source_certified=False,holdout_opened=False,promotion_allowed=False,automatic_retry=False,legacy_log_is_not_checkpoint=True,required_before_execution=['separate approved exploratory adapter','actual source/selection/code verification','budget authority','external durable receipt store','whole-engine parity for any optimization'])

    plan['plan_sha256']=digest(plan)
    return plan

def validate_work_plan(plan):
    if type(plan) is not dict:raise ValueError('work plan object required')
    try:
        rebuilt=build_work_plan(CampaignIdentity(**plan['identity']),max_attempts=plan['max_attempts'],seconds_per_attempt=plan['seconds_per_attempt'],memory_bytes_per_worker=plan['memory_bytes_per_worker'])
        if digest(plan)!=digest(rebuilt):raise ValueError('modified work plan')
    except (KeyError,TypeError) as exc:raise ValueError('invalid work plan schema') from exc
    return dict(status='VERIFIED_METADATA_PLAN_ONLY',execution_allowed=False,authority_authenticated=False)

def validate_checkpoint_identity(plan,receipt):
    """Check identity only, never completeness or output existence/content.
    A legacy FAMILY log or an unsigned completion string is not a receipt.
    """
    validate_work_plan(plan)
    if type(receipt) is not dict or set(receipt)!={'unit_id','fingerprint','output_sha256'}:raise ValueError('closed checkpoint identity schema required')
    matches=[u for u in plan['units'] if u['unit_id']==receipt['unit_id']]
    if len(matches)!=1 or matches[0]['fingerprint']!=receipt['fingerprint']:raise ValueError('checkpoint identity mismatch')
    value=receipt['output_sha256']
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ValueError('explicit output digest required')
    return dict(status='IDENTITY_ONLY_NOT_COMPLETION',unit_id=receipt['unit_id'],output_verified=False,completion_verified=False,skip_allowed=False,execution_allowed=False)
