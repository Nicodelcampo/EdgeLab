from edgelab.research.nq_target_free import month_slices,quantiles
def test_month_slices_non_overlapping_and_bounded():
 x=month_slices(1754078400008000000,1758288594644000000);assert x and all(a<b for _,a,b in x);assert all(x[i][2]<=x[i+1][1]for i in range(len(x)-1));assert x[0][1]==1754078400008000000
def test_month_slices_respect_discovery_end():
 x=month_slices(1765422006472000000,1774013398672000000);assert x[-1][2]==1767225600000000000
def test_quantiles_are_target_free_summary():
 q=quantiles([1,2,3]);assert q['0.5']==2 and q['0.0']==1 and q['1.0']==3
