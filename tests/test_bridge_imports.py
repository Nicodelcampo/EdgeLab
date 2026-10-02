def test_advanced_bridge_imports():
    from edgelab.bridge.indicators import avolclusterpoi,bigtrap2,bigtrap2absorption,hftzones2,hftzones_nq,hftzones_universal
    from edgelab.research import avolclusterpoi_funnel
    assert callable(avolclusterpoi.run) and callable(bigtrap2.run) and callable(hftzones2.run)
