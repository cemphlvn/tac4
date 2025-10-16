# Feature: JSONL File Upload Support

## Feature Description
Add support for uploading JSONL (JSON Lines) files to the natural language SQL interface. JSONL files contain one JSON object per line, making them ideal for streaming large datasets and log files. The feature will parse JSONL files by scanning all records to discover the complete schema (including nested objects and arrays), flatten nested structures using a configurable delimiter, and create a single SQLite table just like CSV and JSON uploads. The UI will be updated to inform users that JSONL files are now supported.

## User Story
As a data analyst
I want to upload JSONL files containing structured data
So that I can query log files, event streams, and large datasets that are commonly distributed in JSONL format

## Problem Statement
Currently, the application only supports CSV and JSON array uploads. Many data sources provide data in JSONL format (one JSON object per line), including:
- Application logs and event streams
- Data exports from various APIs
- Large datasets that don't fit in memory as a single JSON array
- Streaming data sources

Users with JSONL files must manually convert them to JSON arrays before uploading, which is inconvenient and may not be possible for very large files.

## Solution Statement
Implement a JSONL parser that reads the file line-by-line using Python's standard library (no new dependencies). The parser will:
1. Read through the entire JSONL file to discover all possible fields across all records
2. Flatten nested objects by concatenating keys with a configurable delimiter (stored in a constants file)
3. Flatten nested arrays by indexing them with a suffix like `_0`, `_1`, etc.
4. Create a unified schema that accommodates all fields found in any record
5. Convert the data into a pandas DataFrame and store it in SQLite using the existing table creation pattern

The UI will be updated to accept `.jsonl` files and display this option to users.

## Relevant Files
Use these files to implement the feature:

**Server-side files:**
- `app/server/core/file_processor.py` - Add `convert_jsonl_to_sqlite()` function following the same pattern as CSV and JSON converters
- `app/server/server.py` - Update file type validation to accept `.jsonl` files in the upload endpoint
- `app/server/core/sql_security.py` - Existing security module (no changes needed, but will be used for validation)

**Client-side files:**
- `app/client/index.html` - Update file input accept attribute and user-facing text to include `.jsonl`
- `app/client/src/main.ts` - No changes needed (handles files generically)
- `app/client/src/api/client.ts` - No changes needed (handles file uploads generically)

**Test files:**
- `app/server/tests/assets/` - Add JSONL test files with various structures

### New Files
- `app/server/core/constants.py` - New constants file to store the nested field delimiter and list index delimiter configurations

## Implementation Plan
### Phase 1: Foundation
Create the constants file with delimiter configuration. Analyze JSONL structure requirements and design the flattening algorithm for nested objects and arrays. Set up test JSONL files with various edge cases.

### Phase 2: Core Implementation
Implement the JSONL parser that reads line-by-line, discovers all fields, flattens nested structures, and creates a unified schema. Convert the flattened data into a pandas DataFrame and store it in SQLite using the existing safe query execution patterns.

### Phase 3: Integration
Update the server endpoint to accept JSONL files. Update the client UI to display JSONL support. Add comprehensive tests for various JSONL structures including nested objects, arrays, and edge cases.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Create Constants Configuration File
- Create `app/server/core/constants.py` with delimiter configurations
- Define `NESTED_FIELD_DELIMITER = "__"` for concatenating nested object keys
- Define `LIST_INDEX_DELIMITER = "_"` for array item indexing (e.g., `items_0`, `items_1`)
- Add documentation explaining the delimiter usage and rationale
- Make delimiters configurable for future flexibility

### Create Test JSONL Files
- Create `app/server/tests/assets/test_logs.jsonl` with nested objects (e.g., log entries with nested user objects and metadata)
- Create `app/server/tests/assets/test_events.jsonl` with arrays (e.g., events with lists of tags or participants)
- Create `app/server/tests/assets/test_mixed.jsonl` with both nested objects and arrays
- Create `app/server/tests/assets/test_simple.jsonl` with flat objects (no nesting)
- Create `app/server/tests/assets/test_varying_fields.jsonl` where different records have different fields
- Include at least 5-10 records per file to test schema discovery
- Document the expected flattened schema for each test file

### Implement Schema Discovery Function
- Add `discover_jsonl_schema(jsonl_content: bytes) -> set` function to `file_processor.py`
- Read JSONL file line-by-line using standard library
- Parse each line as JSON and recursively discover all field paths
- Handle nested objects by creating flattened keys using `NESTED_FIELD_DELIMITER`
- Handle arrays by creating indexed keys using `LIST_INDEX_DELIMITER` (e.g., `tags_0`, `tags_1`)
- Return a set of all discovered field names across all records
- Handle malformed lines gracefully with try/except
- Add detailed docstring explaining the discovery algorithm

### Implement Field Flattening Function
- Add `flatten_json_object(obj: dict, parent_key: str = '', delimiter: str = NESTED_FIELD_DELIMITER) -> dict` function
- Recursively flatten nested dictionaries by concatenating keys
- Flatten arrays by enumerating items with index suffix (e.g., `items_0`, `items_1`)
- Handle primitive types (strings, numbers, booleans, null) as leaf values
- Convert all values to strings for consistent storage
- Handle edge cases: empty objects, empty arrays, null values
- Add comprehensive docstring with examples
- Write unit tests for various nesting scenarios

### Implement JSONL to SQLite Converter
- Add `convert_jsonl_to_sqlite(jsonl_content: bytes, table_name: str) -> Dict[str, Any]` function to `file_processor.py`
- Sanitize table name using existing `sanitize_table_name()` function
- Call `discover_jsonl_schema()` to get all possible fields
- Read JSONL file line-by-line and flatten each record using `flatten_json_object()`
- Ensure all records have all discovered fields (fill missing fields with None)
- Create pandas DataFrame from flattened records
- Clean column names (lowercase, replace spaces/hyphens with underscores)
- Write DataFrame to SQLite using `df.to_sql()` with `if_exists='replace'`
- Extract schema using safe `PRAGMA table_info` query
- Get sample data using safe `SELECT LIMIT 5` query
- Get row count using safe `SELECT COUNT(*)` query
- Return dict matching the pattern used by CSV/JSON converters
- Add comprehensive error handling with descriptive messages

### Update Server File Upload Endpoint
- Modify `app/server/server.py` line 76-78 to accept `.jsonl` files
- Update validation: `if not file.filename.endswith(('.csv', '.json', '.jsonl')):`
- Update error message: `"Only .csv, .json, and .jsonl files are supported"`
- Add routing logic to call `convert_jsonl_to_sqlite()` when file extension is `.jsonl`
- Ensure consistent error handling across all file types
- Add logging for JSONL file uploads

### Update Client UI File Input
- Modify `app/client/index.html` line 81 to accept `.jsonl` files
- Update accept attribute: `accept=".csv,.json,.jsonl"`
- Update user-facing text on line 80: `"Drag and drop .csv, .json, or .jsonl files here"`
- Ensure no other client-side changes are needed (file upload is handled generically)

### Write Unit Tests for Flattening Logic
- Create test cases for `flatten_json_object()` in test suite
- Test simple nested object: `{"user": {"name": "John"}}` → `{"user__name": "John"}`
- Test nested arrays: `{"tags": ["a", "b"]}` → `{"tags_0": "a", "tags_1": "b"}`
- Test mixed nesting: objects inside arrays and arrays inside objects
- Test empty arrays and objects
- Test null values and missing fields
- Test deeply nested structures (3+ levels)
- Test special characters in keys

### Write Unit Tests for Schema Discovery
- Test `discover_jsonl_schema()` with varying record structures
- Test with records that have different fields
- Test with all records having identical fields
- Test with empty JSONL file
- Test with malformed JSON lines (should skip and continue)
- Test with deeply nested structures
- Verify all discovered fields are returned

### Write Integration Tests for JSONL Upload
- Test full upload flow with simple JSONL file
- Test upload with nested objects
- Test upload with arrays
- Test upload with varying fields across records
- Test that flattened columns are queryable via SQL
- Test that table creation follows security best practices
- Test error handling for invalid JSONL files
- Verify schema, sample data, and row count are correct

### Test Security and SQL Injection Protection
- Verify that flattened column names pass `validate_identifier()` checks
- Test JSONL files with malicious field names containing SQL keywords
- Test field names with special characters
- Ensure all database operations use safe query execution
- Run existing SQL injection test suite to ensure no regressions

### Test Edge Cases
- Test JSONL file with one very long line (large object)
- Test JSONL file with 1000+ records to verify performance
- Test JSONL with unicode characters in field names and values
- Test JSONL with very deeply nested structures (10+ levels)
- Test JSONL with arrays containing 100+ items
- Test JSONL with empty lines or whitespace-only lines
- Test JSONL where some records are empty objects `{}`
- Test JSONL with inconsistent data types for same field across records

### Manual End-to-End Testing
- Start the application using `./scripts/start.sh`
- Upload each test JSONL file through the UI
- Verify tables are created with correct flattened schema
- Query the tables using natural language to verify data is accessible
- Verify sample data display shows flattened fields correctly
- Test uploading JSONL with same filename twice (should overwrite)
- Test uploading all three file types (CSV, JSON, JSONL) in sequence
- Verify no regressions in existing CSV and JSON upload functionality

### Documentation and Code Comments
- Add detailed docstrings to all new functions
- Document the flattening algorithm with examples in code comments
- Add inline comments explaining complex logic
- Document delimiter configuration in constants file
- Add examples of JSONL structure → flattened schema in docstrings

### Run All Validation Commands
- Execute all validation commands to ensure zero regressions
- Fix any issues discovered during validation
- Verify all tests pass
- Verify application starts without errors
- Confirm UI displays JSONL option correctly

## Testing Strategy
### Unit Tests
- Test `flatten_json_object()` with all nesting scenarios
- Test `discover_jsonl_schema()` with varying record structures
- Test `convert_jsonl_to_sqlite()` with simple and complex JSONL files
- Test delimiter configuration and usage
- Test error handling for malformed JSONL
- Test column name sanitization for flattened fields

### Integration Tests
- Test full upload flow from UI to database
- Test querying flattened JSONL data via natural language
- Test JSONL uploads alongside CSV and JSON uploads
- Test table overwrite behavior with JSONL files
- Test schema extraction and sample data display
- Test concurrent JSONL uploads

### Edge Cases
- Empty JSONL file (no records)
- JSONL file with only one record
- JSONL with inconsistent schemas across records
- JSONL with deeply nested structures (10+ levels)
- JSONL with very long arrays (100+ items)
- JSONL with unicode and special characters
- JSONL with malformed lines (invalid JSON)
- JSONL with empty objects `{}`
- JSONL with null values at various nesting levels
- JSONL with field names containing delimiter characters
- JSONL with numeric field names or keys starting with numbers
- Very large JSONL files (1000+ records)

## Acceptance Criteria
- Users can upload `.jsonl` files through the drag-and-drop interface
- UI displays `.jsonl` as a supported file type
- JSONL files are parsed line-by-line without loading entire file into memory
- All fields across all records are discovered and included in the schema
- Nested objects are flattened using `__` delimiter (e.g., `user.name` → `user__name`)
- Nested arrays are flattened with index suffix (e.g., `tags[0]` → `tags_0`)
- Delimiter configuration is stored in a constants file and easily modifiable
- One JSONL file creates one SQLite table, matching CSV/JSON behavior
- Flattened data is queryable via natural language interface
- Sample data display shows flattened columns correctly
- Schema extraction includes all flattened fields with correct types
- No new external libraries are added (use Python standard library only)
- All existing CSV and JSON upload functionality continues to work
- SQL injection protection applies to flattened field names
- Error messages are clear when JSONL parsing fails
- Performance is acceptable for JSONL files with 1000+ records

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/server && uv run pytest tests/core/test_file_processor.py -v` - Run specific file processor tests
- `cd app/server && uv run pytest tests/test_sql_injection.py -v` - Ensure SQL injection protection still works
- `cd scripts && ./start.sh` - Start the application and manually test:
  - Upload `test_simple.jsonl` and verify table creation
  - Upload `test_logs.jsonl` with nested objects and verify flattening
  - Upload `test_events.jsonl` with arrays and verify indexing
  - Upload `test_mixed.jsonl` and verify complex flattening
  - Upload `test_varying_fields.jsonl` and verify schema discovery
  - Query uploaded JSONL data using natural language
  - Verify existing CSV and JSON uploads still work
  - Check that flattened column names are displayed correctly in the UI
  - Test uploading the same JSONL file twice to verify overwrite behavior
- `cd app/client && npm run build` - Ensure client builds without errors
- Manual security test: Upload JSONL with malicious field names and verify they're sanitized

## Notes
- The line-by-line parsing approach makes this memory-efficient for large files
- The two-pass approach (schema discovery, then data processing) ensures consistent schema
- Using standard library only (json, io) means no dependency additions
- The delimiter configuration in constants file makes it easy to change if needed
- Consider adding a future enhancement to limit array flattening depth (e.g., max 10 items)
- Future improvement: Add progress indicator for large JSONL file processing
- Future improvement: Support for NDJSON format (newline-delimited JSON, same as JSONL)
- Consider documenting the delimiter choices in user-facing help text
- The flattening approach may create many columns for deeply nested data - monitor for performance
- If a JSONL file has extreme nesting or very large arrays, consider adding warnings
- Future: Allow users to configure delimiters via environment variables
- The pandas DataFrame approach maintains consistency with existing CSV/JSON processing
