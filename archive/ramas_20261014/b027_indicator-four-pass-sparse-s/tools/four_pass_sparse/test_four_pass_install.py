from pathlib import Path
import unittest,tempfile,hashlib,shutil
from install_four_pass_sparse import install,EXPECTED,MODULES
SOURCE=Path(__file__).parent.parent/'source/index_reference.html'
if not SOURCE.exists():SOURCE=Path(__file__).resolve().parents[2]/'viewer/nt8_bridge/index.html'
class InstallTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name);self.src=self.d/'index.html';self.src.write_bytes(SOURCE.read_bytes());self.out=self.d/'index_four_pass_review.html'
 def tearDown(self):self.tmp.cleanup()
 def test_copy_leaves_source_untouched(self):
  original=self.src.read_bytes();install(self.src,self.out);self.assertEqual(self.src.read_bytes(),original);self.assertEqual(self.out.read_text().count('window.__EDGELAB_FP4_BRIDGE__ ='),1);self.assertEqual(self.out.read_text().count('window.__EDGELAB_FP4_OVERLAY__.draw'),1)
 def test_never_overwrites_source(self):
  with self.assertRaises(ValueError):install(self.src,self.src)
 def test_dirty_viewer_failclosed_no_partial(self):
  self.src.write_text(self.src.read_text()+'\n')
  with self.assertRaises(ValueError):install(self.src,self.out)
  self.assertFalse(self.out.exists());self.assertFalse((self.d/MODULES[0]).exists())
 def test_foreign_module_not_overwritten(self):
  f=self.d/MODULES[-1];f.write_text('foreign_writer')
  with self.assertRaises(ValueError):install(self.src,self.out)
  self.assertEqual(f.read_text(),'foreign_writer');self.assertFalse((self.d/MODULES[0]).exists())
 def test_existing_output_not_overwritten(self):
  self.out.write_text('keep')
  with self.assertRaises(ValueError):install(self.src,self.out)
  self.assertEqual(self.out.read_text(),'keep')
 def test_keep_relative_paths(self):
  with self.assertRaises(ValueError):install(self.src,self.d/'other'/'index.html')
if __name__=='__main__':unittest.main()
