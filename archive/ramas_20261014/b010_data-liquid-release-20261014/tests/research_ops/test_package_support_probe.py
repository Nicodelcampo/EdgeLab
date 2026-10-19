import unittest,ast
from tools.research_ops.confluence.package_support_probe import BOOT
class SupportPackageTests(unittest.TestCase):
 def test_standard_private_temp_root_no_kaggle_temp_assumption(self):
  t=ast.parse(BOOT);calls=[n for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='mkdtemp'];self.assertEqual(len(calls),1);self.assertNotIn('dir',[k.arg for k in calls[0].keywords]);self.assertNotIn('/kaggle/temp',BOOT)
 def test_static_stage_diagnostics_no_arbitrary_exception_export(self):
  self.assertIn('CREATE_PRIVATE_ROOT',BOOT);self.assertIn('RUN_BOUNDED_SUPPORT',BOOT);self.assertNotIn('str(e)',BOOT);self.assertIn('support_receipt_sha256',BOOT);compile(BOOT,'support_boot','exec')
