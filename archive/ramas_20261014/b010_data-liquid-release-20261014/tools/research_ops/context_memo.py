"""Bounded sequential memo for trusted, immutable causal context readers.
No queue action or generated code. Callbacks belong to the existing trusted runner;
source/selection/clock/window identity must be fixed for this instance's lifetime.
Hour key is the exact trigger timestamp, NEVER just the bar (bars may cross hours).
"""
from collections import OrderedDict
from dataclasses import dataclass

@dataclass(frozen=True)
class ContextIdentity:
    source_sha256: str
    selection_sha256: str
    code_sha256: str
    timezone: str='America/Chicago'
    window: int=256
    def validate(self):
        for value in (self.source_sha256,self.selection_sha256,self.code_sha256):
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value): raise ValueError('fixed lowercase identity hashes required')
        if self.timezone!='America/Chicago' or type(self.window) is not int or self.window!=256: raise ValueError('only existing Chicago/prior256 semantics supported')

class ContextMemo:
    def __init__(self,identity,range_for_closed_bar,hour_for_trigger_ns,capacity=8192):
        identity.validate()
        if type(capacity) is not int or not 1<=capacity<=65536: raise ValueError('bounded cache capacity required')
        if not callable(range_for_closed_bar) or not callable(hour_for_trigger_ns): raise ValueError('trusted readers required')
        self._identity=identity;self._range_reader=range_for_closed_bar;self._hour_reader=hour_for_trigger_ns;self._capacity=capacity
        self._ranges=OrderedDict();self._hours=OrderedDict();self._hits={'range':0,'hour':0};self._misses={'range':0,'hour':0}
    @property
    def identity(self): return self._identity
    def _read(self,cache,key,reader,label):
        if key in cache:
            self._hits[label]+=1;cache.move_to_end(key);return cache[key]
        value=reader(key)
        if value is not None and type(value) is not int: raise ValueError('reader must return Python int or None')
        if label=='range' and value is not None and value<0: raise ValueError('negative range')
        if label=='hour' and (value is None or not 0<=value<=23): raise ValueError('invalid Chicago hour')
        self._misses[label]+=1;cache[key]=value
        if len(cache)>self._capacity: cache.popitem(last=False)
        return value
    def context(self,bar_id,trigger_ns):
        if type(bar_id) is not int or bar_id<0 or type(trigger_ns) is not int: raise ValueError('explicit integer bar/timestamp required')
        return (self._read(self._ranges,bar_id,self._range_reader,'range'),self._read(self._hours,trigger_ns,self._hour_reader,'hour'))
    def stats(self):
        return dict(range_hits=self._hits['range'],hour_hits=self._hits['hour'],range_misses=self._misses['range'],hour_misses=self._misses['hour'],range_entries=len(self._ranges),hour_entries=len(self._hours),capacity_per_cache=self._capacity)
