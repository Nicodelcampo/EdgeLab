"""Experimental exact session-resample counts; no RNG or scientific policy changes.
Input is an already frozen draw-index matrix. Local helper, not wired into jobs.
"""
import numpy as np
MAX_ELEMENTS=4_000_000

def multiplicities(draw_indices, sessions):
    if type(sessions) is not int or not 1<=sessions<=2048:raise ValueError('bounded session count required')
    x=np.asarray(draw_indices)
    if x.ndim!=2 or x.shape[1]!=sessions or not 1<=x.shape[0]<=20000 or x.size>MAX_ELEMENTS:raise ValueError('bounded whole-session draws required')
    if x.dtype.kind not in 'iu' or (x<0).any() or (x>=sessions).any():raise ValueError('integer session indices in range required')
    # Independent count of each session's occurrences in each already-chosen draw.
    offsets=np.arange(x.shape[0],dtype=np.int64)[:,None]*sessions
    return np.bincount((x.astype(np.int64)+offsets).ravel(),minlength=x.size).reshape(x.shape).astype(np.int64)

def resampled_counts(weights, daily_counts):
    w=np.asarray(weights);d=np.asarray(daily_counts)
    if w.ndim!=2 or d.ndim!=2 or w.shape[1]!=d.shape[0] or w.size>MAX_ELEMENTS or not 1<=d.shape[1]<=8 or not 1<=w.shape[1]<=2048:raise ValueError('compatible bounded count matrices required')
    if w.dtype.kind not in 'iu' or d.dtype.kind not in 'iu' or (w<0).any() or (d<0).any():raise ValueError('nonnegative integer counts required')
    sessions=w.shape[1]
    # Bound before cast, sums and multiply; avoid uint/int wraparound.
    limit=np.iinfo(np.int64).max//sessions
    if w.size==0 or (w>sessions).any() or (d>limit).any():raise ValueError('count overflow or invalid weights')
    w=w.astype(np.int64,copy=False);d=d.astype(np.int64,copy=False)
    if not np.all(w.sum(axis=1)==sessions):raise ValueError('whole-session draw mass required')
    return w@d
