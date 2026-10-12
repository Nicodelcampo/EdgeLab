"""Closed engineering diagnostics: no exception text, locals, prices or paths."""
SITES={
 'tools.research_ops.confluence.market_pilot':'MARKET_RUNNER',
 'tools.research_ops.confluence.geometry_replay':'GEOMETRY_REPLAY',
 'tools.research_ops.confluence.episodes':'EPISODES',
 'tools.research_ops.confluence.asof_intersections':'ASOF_JOIN',
 'tools.research_ops.confluence.racimo_asof':'RACIMO',
 'tools.research_ops.confluence.kaggle_session_reader':'SESSION_READER',
 'tools.research_ops.confluence.session_primitives':'SESSION_PRIMITIVES',
 'tools.research_ops.confluence.bt2_stream':'BT2_STREAM',
 'tools.research_ops.confluence.bt2a_stream':'BT2A_STREAM',
 'tools.research_ops.confluence.avz_stream':'AVZ_STREAM'}
MESSAGES={
 'private capture budget; no truncation':'PRIVATE_CAPTURE_RECORD_BUDGET',
 'private storage budget; no truncation':'PRIVATE_CAPTURE_STORAGE_BUDGET',
 'full range exceeds tick budget; no silent prefix truncation':'TOTAL_TICK_BUDGET',
 'natural session exceeds memory budget; no reset/truncation':'SESSION_TICK_BUDGET',
 'stream state budget exceeded; no pruning beyond native rule':'AVZ_STATE_BUDGET',
 'known zone budget exceeded':'KNOWN_ZONE_BUDGET',
 'history budget exceeded; do not discard old state silently':'RACIMO_HISTORY_BUDGET',
 'valid quotes/volume required; no quote fabrication':'INPUT_QUOTE_VOLUME_FORMAT',
 'cooperative pilot deadline':'COOPERATIVE_DEADLINE',
 'active pair budget exceeded; no partial output':'ACTIVE_PAIR_BUDGET',
 'candidate triple budget exceeded; no truncation':'CANDIDATE_TRIPLE_BUDGET',
 'active triple budget exceeded; no partial output':'ACTIVE_TRIPLE_BUDGET',
 'capacity exceeded; shard/spill explicitly, never truncate':'JOIN_CAPACITY_BUDGET',
 'pair budget exceeded; no partial output':'JOIN_PAIR_BUDGET',
 'atomic capture budget':'ATOMIC_CAPTURE_BUDGET',
 'strict batch/bar order':'RACIMO_BATCH_ORDER',
 'one atomic detector bar/clock/session batch':'RACIMO_ATOMIC_BATCH',
 'duplicate/conflicting batch mutation':'JOIN_MUTATION_CONFLICT',
 'unknown removal; no silent drop':'JOIN_UNKNOWN_REMOVAL',
 'mutation without birth':'MUTATION_WITHOUT_BIRTH',
 'duplicate birth':'DUPLICATE_BIRTH'}
TYPES={'ValueError','RuntimeError','MemoryError','TimeoutError','KeyError','TypeError','AssertionError','OverflowError','OperationalError','RecursionError'}
CATEGORIES=set(MESSAGES.values())|{'MEMORY_ERROR','UNCLASSIFIED_ENGINE_ERROR'}

def diagnostic(exc):
    # Exception text is used only for exact lookup; it never leaves this function.
    category=MESSAGES.get(str(exc),'MEMORY_ERROR' if isinstance(exc,MemoryError) else 'UNCLASSIFIED_ENGINE_ERROR')
    site='UNCLASSIFIED_SITE';line=None;tb=exc.__traceback__
    while tb:
        name=tb.tb_frame.f_globals.get('__name__')
        if name in SITES:site=SITES[name];line=tb.tb_lineno
        tb=tb.tb_next
    name=type(exc).__name__
    return {'failure_category':category,'exception_type':name if name in TYPES else 'OTHER_EXCEPTION','exception_site':site,'exception_line':line}
