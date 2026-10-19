import base64,json,zlib,ast,hashlib
from pathlib import Path
import unittest
import subprocess,sys,tempfile
from tools.research_ops.confluence.package_synthetic_notebook import build_request,SOURCE_FILES
R=Path(__file__).resolve().parents[2]
class PackageTests(unittest.TestCase):
    def test_private_offline_and_no_market_sources(self):
        req,r=build_request(R,source_commit='a'*40);x=req['request']
        self.assertTrue(x['isPrivate']);self.assertFalse(x['enableInternet']);self.assertFalse(x['enableGpu']);self.assertNotIn('datasetDataSources',x);self.assertFalse(r['market_inputs_included']);self.assertNotIn('http',x['text'])
    def test_embedded_files_exact_and_complete(self):
        req,r=build_request(R,source_commit='a'*40);tree=ast.parse(req['request']['text'])
        enc=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DATA' for t in n.targets))
        raw=zlib.decompress(base64.b64decode(enc));self.assertEqual(hashlib.sha256(raw).hexdigest(),r['bundle_sha256']);files=json.loads(raw)
        self.assertEqual(set(files),set(SOURCE_FILES))
        for p,x in files.items():self.assertEqual(base64.b64decode(x['data']),(R/p).read_bytes())
    def test_actual_isolated_bootstrap_has_all_dependencies_and_limits(self):
        req,_=build_request(R,source_commit='a'*40)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);script=req['request']['text'].replace("'/kaggle/working/confluence-synthetic-pilot'",repr(str(path/'out'))).replace("'--sessions','25','--ticks-per-session','1200'","'--sessions','2','--ticks-per-session','65'")
            (path/'probe.py').write_text(script)
            p=subprocess.run([sys.executable,str(path/'probe.py')],capture_output=True,text=True,timeout=60)
            self.assertEqual(p.returncode,0,p.stderr)
            boot=json.loads((path/'out'/'boot-receipt.json').read_bytes());self.assertEqual(boot['status'],'SYNTHETIC_COMPLETE_NOT_MNQ_RESULTS');self.assertTrue(boot['hard_address_space_limit_applied'])
    def test_bad_commit_rejected(self):
        with self.assertRaises(ValueError):build_request(R,source_commit='main')
if __name__=='__main__':unittest.main()
