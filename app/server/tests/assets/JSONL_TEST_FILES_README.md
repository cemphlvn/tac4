# JSONL Test Files Documentation

This directory contains test JSONL files for validating the JSONL upload feature. Each file demonstrates different aspects of JSONL parsing and schema flattening.

## Delimiter Configuration

- **Nested Object Delimiter**: `__` (double underscore)
- **Array Index Delimiter**: `_` (single underscore)

## Test Files

### 1. `test_simple.jsonl`
**Purpose**: Test basic JSONL parsing with flat objects (no nesting)

**Structure**: 5 records with simple key-value pairs

**Example Record**:
```json
{"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "age": 28}
```

**Expected Flattened Schema**:
- `id` (INTEGER)
- `name` (TEXT)
- `email` (TEXT)
- `age` (INTEGER)

**Notes**: Should work exactly like a JSON array upload, serving as a baseline test.

---

### 2. `test_logs.jsonl`
**Purpose**: Test nested object flattening

**Structure**: 7 log records with nested `user` and `metadata` objects

**Example Record**:
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "message": "User login successful",
  "user": {
    "id": 101,
    "name": "Alice",
    "role": "admin"
  },
  "metadata": {
    "ip": "192.168.1.1",
    "browser": "Chrome"
  }
}
```

**Expected Flattened Schema**:
- `timestamp` (TEXT)
- `level` (TEXT)
- `message` (TEXT)
- `user__id` (INTEGER) - nested field flattened with `__`
- `user__name` (TEXT)
- `user__role` (TEXT)
- `metadata__ip` (TEXT) - different metadata fields across records
- `metadata__browser` (TEXT)
- `metadata__memory_percent` (REAL)
- `metadata__cpu_percent` (REAL)
- `metadata__error_code` (TEXT)
- `metadata__retry_count` (INTEGER)
- `metadata__file_size` (INTEGER)
- `metadata__file_type` (TEXT)
- `metadata__query_time_ms` (INTEGER)
- `metadata__rows_returned` (INTEGER)
- `metadata__session_duration` (INTEGER)
- `metadata__pages_viewed` (INTEGER)
- `metadata__endpoint` (TEXT)
- `metadata__limit` (INTEGER)

**Notes**: Tests that all fields from all records are discovered, even when not present in every record.

---

### 3. `test_events.jsonl`
**Purpose**: Test array flattening with indexing

**Structure**: 6 event records with arrays of tags and participants

**Example Record**:
```json
{
  "event_id": "evt_001",
  "event_type": "purchase",
  "amount": 99.99,
  "tags": ["electronics", "sale", "featured"],
  "participants": ["user_123", "user_456"],
  "timestamp": "2025-01-15T09:00:00Z"
}
```

**Expected Flattened Schema**:
- `event_id` (TEXT)
- `event_type` (TEXT)
- `amount` (REAL)
- `tags_0` (TEXT) - first tag
- `tags_1` (TEXT) - second tag
- `tags_2` (TEXT) - third tag (only in some records)
- `participants_0` (TEXT) - first participant
- `participants_1` (TEXT) - second participant (only in some records)
- `timestamp` (TEXT)

**Notes**: Tests array flattening where arrays have different lengths across records. Schema discovery should find the maximum array length.

---

### 4. `test_mixed.jsonl`
**Purpose**: Test complex structures with both nested objects and nested arrays of objects

**Structure**: 5 order records with nested customer objects and arrays of item objects

**Example Record**:
```json
{
  "order_id": "ORD-001",
  "customer": {
    "id": 1001,
    "name": "John Doe",
    "tier": "gold"
  },
  "items": [
    {"sku": "LAPTOP-001", "price": 999.99},
    {"sku": "MOUSE-042", "price": 29.99}
  ],
  "total": 1029.98,
  "status": "completed"
}
```

**Expected Flattened Schema**:
- `order_id` (TEXT)
- `customer__id` (INTEGER)
- `customer__name` (TEXT)
- `customer__tier` (TEXT)
- `items_0__sku` (TEXT) - nested object inside array
- `items_0__price` (REAL)
- `items_1__sku` (TEXT)
- `items_1__price` (REAL)
- `items_2__sku` (TEXT) - only in records with 3+ items
- `items_2__price` (REAL)
- `total` (REAL)
- `status` (TEXT)

**Notes**: Tests the most complex scenario: arrays containing objects. Delimiter pattern is `arrayname_index__fieldname`.

---

### 5. `test_varying_fields.jsonl`
**Purpose**: Test schema discovery with highly variable record structures

**Structure**: 7 content records where each has different optional fields

**Example Records**:
```json
{"id": 1, "type": "article", "title": "...", "author": "Alice", "published": true, "views": 1500}
{"id": 2, "type": "video", "title": "...", "author": "Bob", "duration_minutes": 45, "views": 3200}
{"id": 4, "type": "podcast", "title": "...", "guests": ["Eve", "Frank"], "views": 5000}
```

**Expected Flattened Schema**:
- `id` (INTEGER)
- `type` (TEXT)
- `title` (TEXT)
- `author` (TEXT)
- `published` (BOOLEAN) - only in some records
- `views` (INTEGER)
- `duration_minutes` (INTEGER) - only in video/podcast
- `word_count` (INTEGER) - only in articles
- `guests_0` (TEXT) - only in podcast
- `guests_1` (TEXT)
- `likes` (INTEGER) - only in some records
- `comments` (INTEGER) - only in some records
- `steps` (INTEGER) - only in tutorial
- `difficulty` (TEXT) - only in tutorial

**Notes**: Critical test for schema discovery. Verifies that all fields across all records are discovered, and missing fields are filled with NULL/None.

---

## Testing Checklist

When testing JSONL upload functionality, verify:

1. **Schema Discovery**:
   - [ ] All fields from all records are discovered
   - [ ] Fields missing in some records are included with NULL values
   - [ ] Nested objects are properly flattened with `__` delimiter
   - [ ] Arrays are properly indexed with `_N` suffix

2. **Data Integrity**:
   - [ ] All records are imported successfully
   - [ ] NULL values are correctly represented for missing fields
   - [ ] Data types are correctly inferred by pandas/SQLite
   - [ ] Nested values are correctly flattened and stored

3. **Column Naming**:
   - [ ] Flattened column names pass SQL identifier validation
   - [ ] Column names are lowercase with underscores
   - [ ] No SQL injection vulnerabilities in generated column names

4. **Query Functionality**:
   - [ ] Flattened data is queryable via SQL
   - [ ] Natural language queries work on flattened columns
   - [ ] Sample data display shows correct flattened structure

5. **Edge Cases**:
   - [ ] Empty arrays are handled gracefully
   - [ ] Empty objects are handled gracefully
   - [ ] Null values at various nesting levels are handled correctly
   - [ ] Very long arrays don't cause issues
   - [ ] Deeply nested structures are fully flattened

## Example Queries

After uploading these files, test with natural language queries like:

**test_logs.jsonl**:
- "Show me all ERROR level logs"
- "Which users have role 'admin'?"
- "What are the unique browsers used?"

**test_events.jsonl**:
- "Show all purchase events"
- "What tags appear most frequently?"
- "Which events have more than one participant?"

**test_mixed.jsonl**:
- "Show orders from gold tier customers"
- "What's the most expensive item ordered?"
- "How many orders are in 'completed' status?"

**test_varying_fields.jsonl**:
- "Show all published articles"
- "What's the average duration of videos?"
- "List content with more than 1000 views"
