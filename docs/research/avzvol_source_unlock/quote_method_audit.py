import json,concurrent.futures
from pathlib import Path
import numpy as np,pyarrow.parquet as pq
P=Path('/data/analysis/avzvol-source-unlock');meta=json.loads((P/'preflight.json').read_text());assert meta['global_all_six_passed']
def go(r):
 n=bad=semantic_bad=alias_count=locked=outside=0;total=unknown_vol=0
 for b in pq.ParquetFile('/data/raw/avzvol-ticks/'+r['file']).iter_batches(batch_size=262144,columns=['price_ticks','bid_ticks','ask_ticks','aggressor','volume']):
  p,bid,ask=[b.column(i).to_numpy() for i in range(3)];agg=b.column(3).to_numpy(zero_copy_only=False);v=b.column(4).to_numpy().astype(np.int64);expected=np.where(p>=ask,'buy',np.where(p<=bid,'sell','unclassified'));bad+=int(np.count_nonzero(agg!=expected));normalized=np.where(agg=='unknown','unclassified',agg);semantic_bad+=int(np.count_nonzero(normalized!=expected));alias_count+=int(np.count_nonzero((agg=='unknown')&(expected=='unclassified')));locked+=int(np.count_nonzero(bid==ask));outside+=int(np.count_nonzero((p<bid)|(p>ask)));n+=len(p);total+=int(v.sum());unknown_vol+=int(v[expected=='unclassified'].sum())
 assert n==r['rows']
 return {'contract':r['contract'],'rows_checked':n,'quote_formula_mismatches':bad,'semantic_formula_mismatches':semantic_bad,'unknown_unclassified_label_aliases':alias_count,'locked_book_rows':locked,'price_outside_current_quote_rows':outside,'total_trade_volume':total,'unclassified_quote_method_volume':unknown_vol,'classified_volume_fraction':1-unknown_vol/total,'interpretation':'quote-derived proxy only, not exchange-aggressor provenance or synchronized quote proof'}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(go,meta['files']))
(P/'quote-method-audit.json').write_text(json.dumps({'scope':'STRUCTURAL_SEMANTIC_QA_ONLY_NO_OUTCOMES','files':rows},indent=2));print('Quote method mismatches:',sum(r['quote_formula_mismatches'] for r in rows),'of',sum(r['rows_checked'] for r in rows),'rows')
