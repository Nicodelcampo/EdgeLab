"""Create a review copy ONLY. Fail closed if the active viewer differs from audited base."""
from pathlib import Path
import argparse,hashlib
EXPECTED='9d302f0ad0ce6624a283978723070174b040b39f85b6adc018a993b97791c2d4'
MODULES=['four_pass_sparse.js','four_pass_sparse_worker.js','four_pass_sparse_viewer.js']
HOOK='    drawTrades(ctx, vr, w, hCanvas);'
TAIL='})();\n</script>\n</body>\n</html>'
BRIDGE='''
  // FP4 bridge in review copy only. Existing REAL-time mapping retained.
  window.__EDGELAB_FP4_BRIDGE__ = {
    context: function(){ var m=state.data&&state.data.meta; return m?{asset:state.currentAssetId,instrument:m.instrument,contract:m.contract,tick_size:m.tick_size}:null; },
    x: function(t){return barTimeToX(t,activeCandlesArr()||[]);},
    y: function(p){return series.priceToCoordinate(p);}, redraw: requestDraw
  };
'''
def install(source,out):
 source=Path(source).resolve();out=Path(out).resolve();content=source.read_text(encoding='utf-8')
 if hashlib.sha256(source.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('ABSTAIN_DIRTY_OR_DIFFERENT_VIEWER: use an audited clean copy; do not overwrite local edits')
 if out==source or out.parent!=source.parent:raise ValueError('SEPARATE_REVIEW_COPY_IN_SAME_DIRECTORY_REQUIRED')
 if out.exists():raise ValueError('REVIEW_COPY_ALREADY_EXISTS_NO_OVERWRITE')
 if content.count(HOOK)!=1 or content.count(TAIL)!=1:raise ValueError('BRIDGE_ANCHOR_MISMATCH')
 here=Path(__file__).parent
 for n in MODULES:
  target=source.parent/n
  if target.exists() and target.read_bytes()!=(here/n).read_bytes():raise ValueError('ABSTAIN_OTHER_WRITER_'+n)
 new=content.replace(HOOK,HOOK+'\n    if(window.__EDGELAB_FP4_OVERLAY__) window.__EDGELAB_FP4_OVERLAY__.draw(ctx,vr,w,hCanvas);')
 new=new.replace(TAIL,BRIDGE+'})();\n</script>\n<script src="four_pass_sparse.js"></script>\n<script src="four_pass_sparse_viewer.js"></script>\n</body>\n</html>')
 for n in MODULES:
  if not (source.parent/n).exists():(source.parent/n).write_bytes((here/n).read_bytes())
 out.write_text(new,encoding='utf-8');return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--viewer',required=True);p.add_argument('--out');z=p.parse_args();f=Path(z.viewer);print(install(f,z.out or f.with_name('index_four_pass_review.html')))
