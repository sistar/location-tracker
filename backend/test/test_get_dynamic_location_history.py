import pytest
from datetime import datetime
from decimal import Decimal
from handlers.get_dynamic_location_history import parse_timestamp_safely

def test_parse_timestamp_safely_iso_format():
    timestamp = "2023-03-15T12:34:56"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromisoformat(timestamp)
    assert result == expected

def test_parse_timestamp_safely_iso_format_with_timezone():
    timestamp = "2023-03-15T12:34:56+00:00"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromisoformat(timestamp)
    assert result == expected

def test_parse_timestamp_safely_standard_format():
    timestamp = "2023-03-15T12:34:56"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    assert result == expected

def test_parse_timestamp_safely_space_separated_format():
    timestamp = "2023-03-15 12:34:56"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    assert result == expected

def test_parse_timestamp_safely_slash_separated_format():
    timestamp = "2023/03/15 12:34:56"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.strptime(timestamp, "%Y/%m/%d %H:%M:%S")
    assert result == expected

def test_parse_timestamp_safely_dot_separated_format():
    timestamp = "15.03.2023 12:34:56"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.strptime(timestamp, "%d.%m.%Y %H:%M:%S")
    assert result == expected

def test_parse_timestamp_safely_unparsable_format():
    timestamp = "invalid-timestamp"
    with pytest.raises(ValueError):
        parse_timestamp_safely(timestamp)

def test_parse_timestamp_safely_with_timezone_info():
    timestamp = "2023-03-15T12:34:56 MESZ"
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromisoformat("2023-03-15T12:34:56")
    assert result == expected

def test_parse_timestamp_safely_empty_string():
    timestamp = ""
    with pytest.raises(ValueError):
        parse_timestamp_safely(timestamp)
        
# New tests for epoch timestamp handling

def test_parse_timestamp_safely_epoch_int():
    timestamp = 1678885200  # 2023-03-15T12:00:00 UTC
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromtimestamp(timestamp)
    assert result == expected
    
def test_parse_timestamp_safely_epoch_float():
    timestamp = 1678885200.5  # 2023-03-15T12:00:00.5 UTC
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromtimestamp(timestamp)
    assert result == expected
    
def test_parse_timestamp_safely_epoch_decimal():
    timestamp = Decimal('1678885200.5')  # 2023-03-15T12:00:00.5 UTC
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromtimestamp(float(timestamp))
    assert result == expected
    
def test_parse_timestamp_safely_epoch_string():
    timestamp = "1678885200"  # 2023-03-15T12:00:00 UTC as string
    result = parse_timestamp_safely(timestamp)
    expected = datetime.fromtimestamp(float(timestamp))
    assert result == expected