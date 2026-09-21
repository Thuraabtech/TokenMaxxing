from app.toon_codec import decode_table, encode_table


def test_round_trip_simple_rows():
    rows = [
        {"id": "st-1", "tier": "low", "confidence": "0.8"},
        {"id": "st-2", "tier": "high", "confidence": "0.6"},
    ]
    encoded = decode_table(encode_table(rows))
    assert encoded == rows


def test_header_declares_row_count_and_fields():
    rows = [{"source": "a.txt", "score": "0.1"}]
    encoded = encode_table(rows)
    assert encoded.startswith("[1]{source,score}:")


def test_value_containing_comma_round_trips():
    rows = [{"text": "compare, analyze, and decide", "tier": "high"}]
    assert decode_table(encode_table(rows)) == rows


def test_empty_table():
    assert encode_table([]) == "[0]{}:"
    assert decode_table("[0]{}:") == []
