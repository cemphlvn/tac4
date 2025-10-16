import pytest
import json
import pandas as pd
import sqlite3
import os
import io
from pathlib import Path
from unittest.mock import patch
from core.file_processor import (
    convert_csv_to_sqlite,
    convert_json_to_sqlite,
    convert_jsonl_to_sqlite,
    flatten_json_object,
    discover_jsonl_schema
)
from core.constants import NESTED_FIELD_DELIMITER, LIST_INDEX_DELIMITER


@pytest.fixture
def test_db():
    """Create an in-memory test database"""
    # Create in-memory database
    conn = sqlite3.connect(':memory:')
    
    # Patch the database connection to use our in-memory database
    with patch('core.file_processor.sqlite3.connect') as mock_connect:
        mock_connect.return_value = conn
        yield conn
    
    conn.close()


@pytest.fixture
def test_assets_dir():
    """Get the path to test assets directory"""
    return Path(__file__).parent.parent / "assets"


class TestFileProcessor:
    
    def test_convert_csv_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real CSV file
        csv_file = test_assets_dir / "test_users.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "users"
        result = convert_csv_to_sqlite(csv_data, table_name)
        
        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result
        
        # Test the returned data
        assert result['row_count'] == 4  # 4 users in test file
        assert len(result['sample_data']) <= 5  # Should return up to 5 samples
        
        # Verify schema has expected columns (cleaned names)
        assert 'name' in result['schema']
        assert 'age' in result['schema'] 
        assert 'city' in result['schema']
        assert 'email' in result['schema']
        
        # Verify sample data structure and content
        john_data = next((item for item in result['sample_data'] if item['name'] == 'John Doe'), None)
        assert john_data is not None
        assert john_data['age'] == 25
        assert john_data['city'] == 'New York'
        assert john_data['email'] == 'john@example.com'
    
    def test_convert_csv_to_sqlite_column_cleaning(self, test_db, test_assets_dir):
        # Test column name cleaning with real file
        csv_file = test_assets_dir / "column_names.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "test_users"
        result = convert_csv_to_sqlite(csv_data, table_name)
        
        # Verify columns were cleaned in the schema
        assert 'full_name' in result['schema']
        assert 'birth_date' in result['schema']
        assert 'email_address' in result['schema']
        assert 'phone_number' in result['schema']
        
        # Verify sample data has cleaned column names and actual content
        sample = result['sample_data'][0]
        assert 'full_name' in sample
        assert 'birth_date' in sample
        assert 'email_address' in sample
        assert sample['full_name'] == 'John Doe'
        assert sample['birth_date'] == '1990-01-15'
    
    def test_convert_csv_to_sqlite_with_inconsistent_data(self, test_db, test_assets_dir):
        # Test with CSV that has inconsistent row lengths - should raise error
        csv_file = test_assets_dir / "invalid.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "inconsistent_table"
        
        # Pandas will fail on inconsistent CSV data
        with pytest.raises(Exception) as exc_info:
            convert_csv_to_sqlite(csv_data, table_name)
        
        assert "Error converting CSV to SQLite" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real JSON file
        json_file = test_assets_dir / "test_products.json"
        with open(json_file, 'rb') as f:
            json_data = f.read()
        
        table_name = "products"
        result = convert_json_to_sqlite(json_data, table_name)
        
        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result
        
        # Test the returned data
        assert result['row_count'] == 3  # 3 products in test file
        assert len(result['sample_data']) == 3
        
        # Verify schema has expected columns
        assert 'id' in result['schema']
        assert 'name' in result['schema']
        assert 'price' in result['schema']
        assert 'category' in result['schema']
        assert 'in_stock' in result['schema']
        
        # Verify sample data structure and content
        laptop_data = next((item for item in result['sample_data'] if item['name'] == 'Laptop'), None)
        assert laptop_data is not None
        assert laptop_data['price'] == 999.99
        assert laptop_data['category'] == 'Electronics'
        assert laptop_data['in_stock'] == True
    
    def test_convert_json_to_sqlite_invalid_json(self):
        # Test with invalid JSON
        json_data = b'invalid json'
        table_name = "test_table"
        
        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)
        
        assert "Error converting JSON to SQLite" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_not_array(self):
        # Test with JSON that's not an array
        json_data = b'{"name": "John", "age": 25}'
        table_name = "test_table"
        
        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)
        
        assert "JSON must be an array of objects" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_empty_array(self):
        # Test with empty JSON array
        json_data = b'[]'
        table_name = "test_table"

        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)

        assert "JSON array is empty" in str(exc_info.value)


class TestFlattenJsonObject:
    """Unit tests for flatten_json_object function"""

    def test_flatten_simple_nested_object(self):
        # Test simple nested object: {"user": {"name": "John"}}
        obj = {"user": {"name": "John"}}
        result = flatten_json_object(obj)
        assert result == {"user__name": "John"}

    def test_flatten_nested_arrays(self):
        # Test nested arrays: {"tags": ["a", "b"]}
        obj = {"tags": ["a", "b", "c"]}
        result = flatten_json_object(obj)
        assert result == {"tags_0": "a", "tags_1": "b", "tags_2": "c"}

    def test_flatten_mixed_nesting(self):
        # Test objects inside arrays and arrays inside objects
        obj = {
            "data": {
                "items": [
                    {"id": 1, "name": "first"},
                    {"id": 2, "name": "second"}
                ]
            }
        }
        result = flatten_json_object(obj)
        expected = {
            "data__items_0__id": "1",
            "data__items_0__name": "first",
            "data__items_1__id": "2",
            "data__items_1__name": "second"
        }
        assert result == expected

    def test_flatten_empty_array(self):
        # Test empty array
        obj = {"tags": []}
        result = flatten_json_object(obj)
        assert result == {}

    def test_flatten_empty_object(self):
        # Test empty object
        obj = {"data": {}}
        result = flatten_json_object(obj)
        assert result == {}

    def test_flatten_null_values(self):
        # Test null values
        obj = {"name": "John", "age": None, "email": None}
        result = flatten_json_object(obj)
        assert result == {"name": "John", "age": None, "email": None}

    def test_flatten_deeply_nested_structures(self):
        # Test deeply nested structures (3+ levels)
        obj = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }
        result = flatten_json_object(obj)
        assert result == {"level1__level2__level3__value": "deep"}

    def test_flatten_primitive_types(self):
        # Test various primitive types
        obj = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None
        }
        result = flatten_json_object(obj)
        assert result["string"] == "hello"
        assert result["number"] == "42"
        assert result["float"] == "3.14"
        assert result["boolean"] == "True"
        assert result["null"] is None

    def test_flatten_array_of_primitives(self):
        # Test array with primitive values
        obj = {"numbers": [1, 2, 3, 4, 5]}
        result = flatten_json_object(obj)
        expected = {
            "numbers_0": "1",
            "numbers_1": "2",
            "numbers_2": "3",
            "numbers_3": "4",
            "numbers_4": "5"
        }
        assert result == expected


class TestDiscoverJsonlSchema:
    """Unit tests for discover_jsonl_schema function"""

    def test_discover_varying_record_structures(self):
        # Test with records that have different fields
        jsonl_data = b'''{"id": 1, "name": "Alice"}
{"id": 2, "name": "Bob", "email": "bob@example.com"}
{"id": 3, "age": 30}'''

        fields = discover_jsonl_schema(jsonl_data)
        assert "id" in fields
        assert "name" in fields
        assert "email" in fields
        assert "age" in fields
        assert len(fields) == 4

    def test_discover_identical_fields(self):
        # Test with all records having identical fields
        jsonl_data = b'''{"id": 1, "name": "Alice"}
{"id": 2, "name": "Bob"}
{"id": 3, "name": "Charlie"}'''

        fields = discover_jsonl_schema(jsonl_data)
        assert fields == {"id", "name"}

    def test_discover_empty_jsonl(self):
        # Test with empty JSONL file
        jsonl_data = b''
        fields = discover_jsonl_schema(jsonl_data)
        assert len(fields) == 0

    def test_discover_malformed_json_lines(self):
        # Test with malformed JSON lines (should skip and continue)
        jsonl_data = b'''{"id": 1, "name": "Alice"}
this is not valid json
{"id": 2, "name": "Bob"}'''

        fields = discover_jsonl_schema(jsonl_data)
        assert "id" in fields
        assert "name" in fields
        assert len(fields) == 2

    def test_discover_deeply_nested_structures(self):
        # Test with deeply nested structures
        jsonl_data = b'''{"user": {"profile": {"contact": {"email": "alice@example.com"}}}}
{"user": {"profile": {"settings": {"theme": "dark"}}}}'''

        fields = discover_jsonl_schema(jsonl_data)
        assert "user__profile__contact__email" in fields
        assert "user__profile__settings__theme" in fields

    def test_discover_with_arrays(self):
        # Test with arrays
        jsonl_data = b'''{"tags": ["python", "data"]}
{"tags": ["javascript", "web", "frontend"]}'''

        fields = discover_jsonl_schema(jsonl_data)
        # Should discover all array positions used across all records
        assert "tags_0" in fields
        assert "tags_1" in fields
        assert "tags_2" in fields

    def test_discover_empty_lines(self):
        # Test with empty lines or whitespace-only lines
        jsonl_data = b'''{"id": 1}

{"id": 2}

{"id": 3}'''

        fields = discover_jsonl_schema(jsonl_data)
        assert fields == {"id"}


class TestConvertJsonlToSqlite:
    """Integration tests for convert_jsonl_to_sqlite function"""

    def test_convert_simple_jsonl(self, test_db, test_assets_dir):
        # Test with simple flat JSONL file
        jsonl_file = test_assets_dir / "test_simple.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "simple_data"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result

        # Test the returned data
        assert result['row_count'] == 5
        assert len(result['sample_data']) == 5

        # Verify schema has expected columns
        assert 'id' in result['schema']
        assert 'name' in result['schema']
        assert 'email' in result['schema']
        assert 'age' in result['schema']

    def test_convert_nested_objects(self, test_db, test_assets_dir):
        # Test with nested objects
        jsonl_file = test_assets_dir / "test_logs.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "logs"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify flattened column names exist
        schema_keys = [k.lower() for k in result['schema'].keys()]

        # Check for flattened nested fields (user.id -> user__id)
        assert any('user__id' in k for k in schema_keys)
        assert any('user__name' in k for k in schema_keys)
        assert any('metadata__ip' in k or 'metadata__memory_percent' in k for k in schema_keys)

        # Verify row count
        assert result['row_count'] == 7

    def test_convert_with_arrays(self, test_db, test_assets_dir):
        # Test with arrays
        jsonl_file = test_assets_dir / "test_events.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "events"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify flattened array columns exist (tags_0, tags_1, etc.)
        schema_keys = [k.lower() for k in result['schema'].keys()]
        assert any('tags_0' in k for k in schema_keys)
        assert any('tags_1' in k for k in schema_keys)
        assert any('participants_0' in k for k in schema_keys)

        # Verify row count
        assert result['row_count'] == 6

    def test_convert_varying_fields(self, test_db, test_assets_dir):
        # Test with varying fields across records
        jsonl_file = test_assets_dir / "test_varying_fields.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "varying_data"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify all possible fields are in schema
        schema_keys = [k.lower() for k in result['schema'].keys()]
        assert 'id' in schema_keys
        assert 'type' in schema_keys
        assert 'title' in schema_keys
        assert 'author' in schema_keys

        # Some records have different optional fields
        # The schema should include all fields found across all records
        assert len(result['schema']) >= 7  # At least 7 unique fields across all records

        # Verify row count
        assert result['row_count'] == 7

    def test_convert_mixed_nesting(self, test_db, test_assets_dir):
        # Test with both nested objects and arrays
        jsonl_file = test_assets_dir / "test_mixed.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "mixed_data"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify both nested objects and arrays are flattened
        schema_keys = [k.lower() for k in result['schema'].keys()]

        # Check for nested object flattening
        assert any('customer__' in k for k in schema_keys)

        # Check for array flattening
        assert any('items_0' in k or 'items_1' in k for k in schema_keys)

        # Verify row count
        assert result['row_count'] == 5

    def test_convert_empty_jsonl(self):
        # Test with empty JSONL file
        jsonl_data = b''
        table_name = "test_table"

        with pytest.raises(Exception) as exc_info:
            convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert "empty" in str(exc_info.value).lower()

    def test_convert_invalid_jsonl(self):
        # Test with completely invalid JSONL
        jsonl_data = b'this is not json at all'
        table_name = "test_table"

        with pytest.raises(Exception) as exc_info:
            convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert "Error converting JSONL to SQLite" in str(exc_info.value)

    def test_queryable_data(self, test_db, test_assets_dir):
        # Test that flattened data is queryable
        jsonl_file = test_assets_dir / "test_simple.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "queryable_data"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify we can query the sample data
        assert len(result['sample_data']) > 0
        first_row = result['sample_data'][0]

        # Verify the data structure is a dictionary with the expected keys
        assert isinstance(first_row, dict)
        assert 'id' in first_row or 'name' in first_row