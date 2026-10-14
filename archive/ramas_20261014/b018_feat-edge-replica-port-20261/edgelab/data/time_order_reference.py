"""Independent quote-side/time-order reference; NEVER broker execution proof.
No TP/SL added. Source must already be custody/embargo/quality bounded.
"""

def first_quote_fill(ticks,*,order_ns,information_key,direction,is_exit,max_lateness_ns):
    if type(order_ns)!=int or order_ns<=0 or type(max_lateness_ns)!=int or max_lateness_ns<0:
        raise ValueError('explicit integer order time and lateness budget required')
    if direction not in (-1,1) or type(direction)!=int or type(is_exit)!=bool:
        raise ValueError('explicit direction/entry-exit semantics required')
    if not isinstance(information_key,tuple) or len(information_key)!=2 or any(type(v)!=int for v in information_key):
        raise ValueError('last observable event key required')
    if information_key[0]>order_ns:raise ValueError('order precedes information')
    prior=None
    for t in ticks:
        ts,seq,bid,ask=(t[k] for k in ('ts_utc_ns','sequence','bid_ticks','ask_ticks'))
        if any(type(v)!=int for v in (ts,seq,bid,ask)) or ts<=0 or seq<0 or not 0<bid<=ask:
            raise ValueError('invalid canonical quote event')
        key=(ts,seq)
        if prior is not None and key<=prior:raise ValueError('unordered/duplicate quote event')
        prior=key
        if ts<order_ns or key<=information_key:continue
        if ts-order_ns>max_lateness_ns:break
        buy=(direction==1) != is_exit
        return {'status':'MODELLED_FILL_NOT_BROKER_VERIFIED','order_ns':order_ns,'fill_ns':ts,
                'sequence':seq,'price_ticks':ask if buy else bid,'side':'BUY' if buy else 'SELL',
                'lateness_ns':ts-order_ns,'observed_broker_fill':False}
    return {'status':'DATA_INCOMPLETE','order_ns':order_ns,'fill_ns':None,
            'price_ticks':None,'observed_broker_fill':False,'reason':'NO_EXECUTABLE_TICK_WITHIN_LATENESS'}
