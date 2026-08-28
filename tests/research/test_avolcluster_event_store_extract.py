from diag.tasa_senales.avolcluster_event_store_extract import direction_of


def test_direction_off_price_short():
    assert direction_of({"kind": "OFF_PRICE", "direction": -1}) == -1


def test_direction_off_price_long():
    assert direction_of({"kind": "OFF_PRICE", "direction": 1}) == 1


def test_direction_at_price_es_neutral_cero():
    assert direction_of({"kind": "AT_PRICE", "direction": None}) == 0
