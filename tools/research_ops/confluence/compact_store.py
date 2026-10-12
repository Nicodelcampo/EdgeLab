"""Candidate only: one clustered B-tree, no redundant rowid+secondary index.
Same logical payload/hashes/order/census as baseline. Not selected for market.
"""
from .market_pilot import PrivateStore
class ClusteredPrivateStore(PrivateStore):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.db.execute('drop table caps')
        self.db.execute('create table caps(cfg integer,ns integer,seq integer,ord integer,payload text,primary key(cfg,ns,seq,ord)) without rowid')
        self.db.commit()
    def ready(self):self.flush()
