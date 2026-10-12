"""Verify metadata-only source receipts; never issue market execution permission."""
import hashlib,json
from .source_footer import validate_pin
from .build_target_free_pilot import digest


def verify(boot_raw,footer_raw,*,pin,package):
    expected_pin=validate_pin(pin);boot=json.loads(boot_raw);footer=json.loads(footer_raw)
    if boot.get('schema')!='mnq_confluence_source_probe_boot_v1' or footer.get('schema')!='mnq_confluence_source_footer_receipt_v1':raise ValueError('source probe receipt schemas')
    status='PASS_PINNED_FOOTER_ONLY_NOT_MARKET_APPROVAL'
    if any(x.get('status')!=status for x in (boot,footer)):raise ValueError('semantic footer completion missing')
    if boot.get('source_commit')!=package['source_commit'] or package['source_pin_sha256']!=expected_pin:raise ValueError('source code or package pin mismatch')
    if footer.get('pin')!=pin or footer.get('pin_sha256')!=expected_pin or footer.get('physical_bytes_sha256')!=pin['sha256']:raise ValueError('physical source pin mismatch')
    if boot.get('source_footer_receipt_sha256')!=hashlib.sha256(footer_raw).hexdigest():raise ValueError('footer bytes mismatch')
    if digest({k:v for k,v in footer.items() if k!='receipt_sha256'})!=footer.get('receipt_sha256'):raise ValueError('footer seal mismatch')
    if footer.get('rows')!=pin['rows'] or footer.get('time_max_ns')!=pin['max_ns'] or footer.get('issues')!=[] or footer.get('required_columns_missing')!=[]:raise ValueError('footer requirements mismatch')
    for obj in (boot,footer):
        for k in ('price_payload_deserialized','holdout_opened','pnl_computed','source_quality_certified','execution_allowed'):
            if obj.get(k) is not False:raise ValueError('unexpected authority/payload assertion')
        if obj.get('market_trials_executed')!=0 or obj.get('physical_bytes_hashed') is not True:raise ValueError('scope/hash evidence mismatch')
    if boot.get('raw_file_exported') is not False:raise ValueError('raw file export forbidden')
    return {'schema':'mnq_confluence_source_output_verification_v1','status':status,'source_commit':package['source_commit'],'source_pin_sha256':expected_pin,'source_sha256':pin['sha256'],'boot_file_sha256':hashlib.sha256(boot_raw).hexdigest(),'footer_file_sha256':hashlib.sha256(footer_raw).hexdigest(),'source_exact_bytes_bound':True,'required_schema_columns_present':True,'price_payload_deserialized':False,'market_trials_executed':0,'source_quality_certified':False,'execution_allowed':False,'holdout_opened':False,'raw_file_exported':False}
