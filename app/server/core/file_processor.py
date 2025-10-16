import json
import pandas as pd
import sqlite3
import io
import re
from typing import Dict, Any, List, Set
from .sql_security import (
    execute_query_safely,
    validate_identifier,
    SQLSecurityError
)
from .constants import NESTED_FIELD_DELIMITER, LIST_INDEX_DELIMITER

def sanitize_table_name(table_name: str) -> str:
    """
    Sanitize table name for SQLite by removing/replacing bad characters
    and validating against SQL injection
    """
    # Remove file extension if present
    if '.' in table_name:
        table_name = table_name.rsplit('.', 1)[0]
    
    # Replace bad characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', table_name)
    
    # Ensure it starts with a letter or underscore
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'table'
    
    # Validate the sanitized name
    try:
        validate_identifier(sanitized, "table")
    except SQLSecurityError:
        # If validation fails, use a safe default
        sanitized = f"table_{hash(table_name) % 100000}"
    
    return sanitized

def convert_csv_to_sqlite(csv_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert CSV file content to SQLite table
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)
        
        # Read CSV into pandas DataFrame
        df = pd.read_csv(io.BytesIO(csv_content))
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()
        
        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type
        
        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]
        
        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]
        
        conn.close()
        
        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }
        
    except Exception as e:
        raise Exception(f"Error converting CSV to SQLite: {str(e)}")

def convert_json_to_sqlite(json_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert JSON file content to SQLite table
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)
        
        # Parse JSON
        data = json.loads(json_content.decode('utf-8'))
        
        # Ensure it's a list of objects
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects")
        
        if not data:
            raise ValueError("JSON array is empty")
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data)
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()
        
        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type
        
        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]
        
        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]
        
        conn.close()
        
        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }
        
    except Exception as e:
        raise Exception(f"Error converting JSON to SQLite: {str(e)}")

def flatten_json_object(obj: Any, parent_key: str = '', delimiter: str = NESTED_FIELD_DELIMITER) -> Dict[str, str]:
    """
    Recursively flatten a nested JSON object into a flat dictionary.

    This function handles nested dictionaries by concatenating keys with a delimiter,
    and handles arrays by enumerating items with an index suffix.

    Args:
        obj: The JSON object to flatten (dict, list, or primitive value)
        parent_key: The parent key path (used in recursion)
        delimiter: The delimiter to use for concatenating nested keys (default: NESTED_FIELD_DELIMITER)

    Returns:
        A flat dictionary with concatenated keys and string values

    Examples:
        >>> flatten_json_object({"user": {"name": "John"}})
        {"user__name": "John"}

        >>> flatten_json_object({"tags": ["a", "b", "c"]})
        {"tags_0": "a", "tags_1": "b", "tags_2": "c"}

        >>> flatten_json_object({"data": {"items": [{"id": 1}, {"id": 2}]}})
        {"data__items_0__id": "1", "data__items_1__id": "2"}
    """
    items = {}

    if isinstance(obj, dict):
        # Handle nested dictionaries
        for key, value in obj.items():
            new_key = f"{parent_key}{delimiter}{key}" if parent_key else key
            items.update(flatten_json_object(value, new_key, delimiter))

    elif isinstance(obj, list):
        # Handle arrays by indexing each item
        for i, item in enumerate(obj):
            new_key = f"{parent_key}{LIST_INDEX_DELIMITER}{i}"
            items.update(flatten_json_object(item, new_key, delimiter))

    else:
        # Handle primitive types (strings, numbers, booleans, null)
        # Convert everything to string for consistent storage
        if obj is None:
            items[parent_key] = None
        else:
            items[parent_key] = str(obj)

    return items

def discover_jsonl_schema(jsonl_content: bytes) -> Set[str]:
    """
    Discover all unique field names across all records in a JSONL file.

    This function reads through the entire JSONL file to discover the complete schema,
    including all nested fields from all records. This ensures a unified schema that
    accommodates all fields found in any record.

    Args:
        jsonl_content: The JSONL file content as bytes

    Returns:
        A set of all discovered field names (flattened) across all records

    Examples:
        For a JSONL file with records:
        {"id": 1, "user": {"name": "Alice"}}
        {"id": 2, "user": {"name": "Bob", "email": "bob@example.com"}}

        Returns: {"id", "user__name", "user__email"}

    Note:
        Malformed JSON lines are skipped gracefully with a warning,
        allowing the function to continue processing valid records.
    """
    all_fields = set()

    # Read JSONL file line by line
    content_str = jsonl_content.decode('utf-8')
    lines = content_str.strip().split('\n')

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        try:
            # Parse JSON object
            obj = json.loads(line)

            # Flatten the object and collect field names
            flattened = flatten_json_object(obj)
            all_fields.update(flattened.keys())

        except json.JSONDecodeError as e:
            # Skip malformed lines gracefully
            print(f"Warning: Skipping malformed JSON on line {line_num}: {e}")
            continue

    return all_fields

def convert_jsonl_to_sqlite(jsonl_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert JSONL (JSON Lines) file content to SQLite table.

    JSONL files contain one JSON object per line, making them ideal for streaming
    large datasets. This function:
    1. Discovers all fields across all records (schema discovery)
    2. Flattens nested objects and arrays
    3. Creates a unified schema
    4. Converts to pandas DataFrame
    5. Stores in SQLite

    Args:
        jsonl_content: The JSONL file content as bytes
        table_name: The desired table name (will be sanitized)

    Returns:
        A dictionary containing:
        - table_name: The sanitized table name
        - schema: Dictionary mapping column names to data types
        - row_count: Total number of rows
        - sample_data: List of first 5 rows as dictionaries

    Raises:
        Exception: If the JSONL file is empty, malformed, or database operations fail

    Example JSONL input:
        {"id": 1, "user": {"name": "Alice"}, "tags": ["python", "data"]}
        {"id": 2, "user": {"name": "Bob"}, "tags": ["javascript"]}

    Resulting table columns:
        id, user__name, tags_0, tags_1
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)

        # Step 1: Discover schema across all records
        all_fields = discover_jsonl_schema(jsonl_content)

        if not all_fields:
            raise ValueError("JSONL file is empty or contains no valid records")

        # Step 2: Read and flatten all records
        content_str = jsonl_content.decode('utf-8')
        lines = content_str.strip().split('\n')

        flattened_records = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
                flattened = flatten_json_object(obj)

                # Ensure all fields are present (fill missing with None)
                complete_record = {field: flattened.get(field) for field in all_fields}
                flattened_records.append(complete_record)

            except json.JSONDecodeError:
                # Skip malformed lines (already warned in schema discovery)
                continue

        if not flattened_records:
            raise ValueError("No valid records found in JSONL file")

        # Step 3: Create pandas DataFrame
        df = pd.DataFrame(flattened_records)

        # Clean column names (lowercase, replace special chars)
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]

        # Step 4: Connect to SQLite database
        conn = sqlite3.connect("db/database.db")

        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        # Step 5: Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()

        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type

        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]

        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]

        conn.close()

        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }

    except Exception as e:
        raise Exception(f"Error converting JSONL to SQLite: {str(e)}")