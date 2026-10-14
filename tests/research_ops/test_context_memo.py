"""Synthetic trusted readers only, no generated code or market files."""
import unittest
from dataclasses import replace
from tools.research_ops.context_memo import ContextMemo,ContextIdentity

class ContextMemoTests(unittest.TestCase):
    def identity(self):return ContextIdentity('a'*64,'b'*64,'c'*64)
    def make(self,capacity=2):return ContextMemo(self.identity(),lambda b: b,lambda t:t%24,capacity)
    def test_exact_key_hit(self):
        c=self.make();self.assertEqual(c.context(3,7),(3,7));self.assertEqual(c.context(3,7),(3,7));self.assertEqual(c.stats()['range_hits'],1)
    def test_hour_not_keyed_by_bar(self):
        c=self.make();self.assertEqual(c.context(3,7),(3,7));self.assertEqual(c.context(3,8),(3,8));self.assertEqual(c.stats()['hour_hits'],0)
    def test_none_cached(self):
        c=ContextMemo(self.identity(),lambda b:None,lambda t:0);self.assertEqual(c.context(0,0),(None,0));c.context(0,0);self.assertEqual(c.stats()['range_hits'],1)
    def test_eviction(self):
        c=self.make();c.context(0,0);c.context(1,1);c.context(2,2);c.context(0,0);self.assertEqual(c.stats()['range_misses'],4);self.assertEqual(c.stats()['range_entries'],2)
    def test_lru_refresh(self):
        c=self.make();c.context(0,0);c.context(1,1);c.context(0,0);c.context(2,2);c.context(0,0);self.assertEqual(c.stats()['range_hits'],2)
    def test_source_isolation(self):
        a=self.make();b=ContextMemo(replace(self.identity(),source_sha256='d'*64),lambda b:99,lambda t:0);self.assertEqual(a.context(1,0),(1,0));self.assertEqual(b.context(1,0),(99,0))
    def test_identity_immutable(self):
        c=self.make()
        with self.assertRaises(AttributeError):c.identity=replace(c.identity,source_sha256='d'*64)
    def test_invalid_hash(self):
        with self.assertRaises(ValueError):ContextMemo(replace(self.identity(),code_sha256='bad'),lambda b:1,lambda t:0)
    def test_other_window_rejected(self):
        with self.assertRaises(ValueError):ContextMemo(replace(self.identity(),window=128),lambda b:1,lambda t:0)
    def test_timezone_rejected(self):
        with self.assertRaises(ValueError):ContextMemo(replace(self.identity(),timezone='UTC'),lambda b:1,lambda t:0)
    def test_capacity(self):
        for n in (0,65537,True):
            with self.assertRaises(ValueError):self.make(n)
    def test_integer_keys(self):
        c=self.make()
        for b,t in [(True,1),(-1,1),(1,True),(1,1.0)]:
            with self.assertRaises(ValueError):c.context(b,t)
    def test_negative_range(self):
        with self.assertRaises(ValueError):ContextMemo(self.identity(),lambda b:-1,lambda t:0).context(0,0)
    def test_invalid_hour(self):
        for h in (-1,24,None,True):
            with self.assertRaises(ValueError):ContextMemo(self.identity(),lambda b:1,lambda t:h).context(0,0)
    def test_failed_reader_not_cached(self):
        c=ContextMemo(self.identity(),lambda b:1/0,lambda t:0)
        with self.assertRaises(ZeroDivisionError):c.context(0,0)
        self.assertEqual(c.stats()['range_entries'],0)
    def test_input_reader_not_recalled_on_hit(self):
        seen=[];c=ContextMemo(self.identity(),lambda b:seen.append(b) or b,lambda t:0);c.context(1,0);c.context(1,0);self.assertEqual(seen,[1])
