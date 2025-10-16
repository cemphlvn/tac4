"""
Constants configuration for file processing.

This module defines configuration constants used across the application,
particularly for handling nested data structures in JSON and JSONL files.
"""

# Delimiter used to concatenate nested object keys when flattening JSON structures
# Example: {"user": {"name": "John"}} becomes {"user__name": "John"}
NESTED_FIELD_DELIMITER = "__"

# Delimiter used for array item indexing when flattening JSON arrays
# Example: {"tags": ["a", "b", "c"]} becomes {"tags_0": "a", "tags_1": "b", "tags_2": "c"}
LIST_INDEX_DELIMITER = "_"

"""
Delimiter Usage Rationale:

NESTED_FIELD_DELIMITER ("__"):
- Double underscore is chosen as it rarely appears in typical field names
- Clearly distinguishes nested structure from regular underscores in field names
- Compatible with SQL identifiers and pandas DataFrame column names
- Easily reversible if needed for reconstruction

LIST_INDEX_DELIMITER ("_"):
- Single underscore is compact and readable
- Natural convention for indexed items (e.g., item_0, item_1)
- Compatible with SQL identifiers and pandas DataFrame column names
- Makes it clear which fields originated from arrays

Future Flexibility:
These delimiters can be made configurable via environment variables if needed.
Any changes to these values should be tested thoroughly as they affect schema generation.
"""
