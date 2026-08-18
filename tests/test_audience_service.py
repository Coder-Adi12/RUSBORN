from services.audience_service import (
    guess_column_mapping,
    normalize_phone,
    parse_csv_preview,
)


def test_guess_column_mapping():
    headers = ["First Name", "Cell Number", "Email Address", "Org", "Notes"]
    mapping = guess_column_mapping(headers)

    assert mapping["name"] == "First Name"
    assert mapping["phone"] == "Cell Number"
    assert mapping["email"] == "Email Address"
    assert mapping["company"] == "Org"
    assert mapping["context"] == "Notes"
    assert mapping["description"] == ""

def test_normalize_phone():
    assert normalize_phone("123-456-7890") == "+1234567890"
    assert normalize_phone("(555) 123 4567") == "+5551234567"
    assert normalize_phone("+1 555-123-4567") == "+15551234567"
    assert normalize_phone("invalid") is None
    assert normalize_phone("") is None
    assert normalize_phone(None) is None

def test_parse_csv_preview():
    csv_content = b"name,phone,email\nJohn Doe,1234567890,test@example.com\nJane Smith,0987654321,jane@example.com"
    result = parse_csv_preview(csv_content)

    assert result["headers"] == ["name", "phone", "email"]
    assert result["mapping"]["name"] == "name"
    assert result["mapping"]["phone"] == "phone"
    assert len(result["preview"]) == 2
    assert result["total_rows"] == 2
    assert result["preview"][0]["name"] == "John Doe"
