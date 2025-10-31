# Request Acceptance Worker - Code Description

## Overview
The `RequestAcceptanceWorker` is the first worker in the processing pipeline. It validates incoming market intelligence requests and creates the initial processing plan. Upon completion, it triggers SERP queue items (one per source).

## Location
**File:** `app/queues/request_acceptance/worker.py`  
**Class:** `RequestAcceptanceWorker(BaseWorker)`

## Inheritance
Extends `BaseWorker` and implements abstract methods:
- `process_item()` - Validates request and creates processing plan
- `prepare_next_queue_payload()` - Prepares payload for SERP queue

## Core Responsibilities

### 1. Request Validation
Validates the incoming market intelligence request in detail.

### 2. Processing Plan Creation
Creates a processing plan based on request configuration.

### 3. SERP Queue Creation
Creates multiple SERP queue items - one for each source specified in the request.

## Processing Flow

### Step 1: Item Processing
```python
def process_item(self, item: Dict[str, Any]) -> bool:
    payload = item.get('payload', {})
    original_request_data = payload.get('original_request', {})
    
    # Validate the request
    validation_results = self._validate_request(original_request_data)
    
    if not validation_results['is_valid']:
        return False
    
    # Create processing plan
    processing_plan = self._create_processing_plan(original_request_data)
    
    # Update payload with validation results and processing plan
    updated_payload = {
        'original_request': original_request_data,
        'validation_results': validation_results,
        'processing_plan': processing_plan,
        'accepted_at': datetime.utcnow().isoformat()
    }
    
    # Update DynamoDB
    dynamodb_client.update_item(...)
    
    return True
```

### Step 2: Request Validation Details

```python
def _validate_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the market intelligence request"""
    errors = []
    warnings = []
    
    # Required fields validation
    required_fields = ['project_id', 'project_request_id', 'user_id', 'config']
    for field in required_fields:
        if not request_data.get(field):
            errors.append(f"Missing required field: {field}")
    
    # Config validation
    config = request_data.get('config', {})
    keywords = config.get('keywords', [])
    sources = config.get('sources', [])
    
    # Keywords validation
    if not keywords:
        errors.append("No keywords provided in config")
    elif len(keywords) > 20:
        warnings.append("Large number of keywords may impact performance")
    
    # Sources validation
    if not sources:
        errors.append("No sources provided in config")
    else:
        for i, source in enumerate(sources):
            if not source.get('name'):
                errors.append(f"Source {i} missing name")
            if not source.get('url'):
                errors.append(f"Source {i} missing URL")
            if not source.get('type'):
                warnings.append(f"Source {i} missing type")
    
    # Extraction mode validation
    extraction_mode = config.get('extraction_mode', 'summary')
    valid_modes = ['summary', 'full', 'structured']
    if extraction_mode not in valid_modes:
        errors.append(f"Invalid extraction_mode: {extraction_mode}")
    
    # Quality threshold validation
    quality_threshold = config.get('quality_threshold', 0.8)
    if not isinstance(quality_threshold, (int, float)) or not (0.0 <= quality_threshold <= 1.0):
        errors.append("quality_threshold must be a number between 0.0 and 1.0")
    
    # Priority validation
    priority = request_data.get('priority', 'medium')
    valid_priorities = ['high', 'medium', 'low']
    if priority not in valid_priorities:
        errors.append(f"Invalid priority: {priority}")
    
    # Processing strategy validation
    processing_strategy = request_data.get('processing_strategy', 'table')
    valid_strategies = ['table', 'stream', 'batch']
    if processing_strategy not in valid_strategies:
        errors.append(f"Invalid processing_strategy: {processing_strategy}")
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'validated_at': datetime.utcnow().isoformat()
    }
```

**Validation Checks:**
1. **Required Fields:** project_id, project_request_id, user_id, config
2. **Keywords:** Must exist, max 20 (warning if >20)
3. **Sources:** Must exist, each must have name, url, and type
4. **Extraction Mode:** Must be one of: 'summary', 'full', 'structured'
5. **Quality Threshold:** Must be between 0.0 and 1.0
6. **Priority:** Must be one of: 'high', 'medium', 'low'
7. **Processing Strategy:** Must be one of: 'table', 'stream', 'batch'

### Step 3: Processing Plan Creation

```python
def _create_processing_plan(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create processing plan based on request configuration"""
    config = request_data.get('config', {})
    processing_strategy = request_data.get('processing_strategy', 'table')
    sources = config.get('sources', [])
    keywords = config.get('keywords', [])
    
    # Calculate expected items per queue
    expected_serp_items = len(sources)  # One per source
    expected_perplexity_items = expected_serp_items * 5  # Estimate 5 URLs per source
    expected_final_items = expected_perplexity_items * 2  # Both insight and implication
    
    plan = {
        'queues': ['serp', 'perplexity', 'insight', 'implication'],
        'strategy': processing_strategy,
        'expected_items': {
            'serp': expected_serp_items,
            'perplexity': expected_perplexity_items,
            'insight': expected_perplexity_items,
            'implication': expected_perplexity_items
        },
        'estimated_duration_minutes': self._estimate_processing_time(config, processing_strategy),
        'created_at': datetime.utcnow().isoformat()
    }
    
    return plan
```

**Processing Plan Contains:**
- **Queues:** List of queues that will be used
- **Strategy:** Processing strategy (table/stream/batch)
- **Expected Items:** Estimated number of items per queue
- **Estimated Duration:** Estimated processing time in minutes

### Step 4: SERP Queue Item Creation

**Important:** This worker overrides `_create_next_queue_item()` to create **multiple SERP items** (one per source).

```python
def _create_next_queue_item(self, next_queue: str, project_id: str, 
                           request_id: str, completed_item: Dict[str, Any]):
    """Override to create multiple SERP items (one per source)"""
    if next_queue != "serp":
        return super()._create_next_queue_item(next_queue, project_id, request_id, completed_item)
    
    # For SERP queue, create one item per source
    payload = completed_item.get('payload', {})
    original_request = payload.get('original_request', {})
    config = original_request.get('config', {})
    keywords = config.get('keywords', [])
    sources = config.get('sources', [])
    
    logger.info(f"Creating {len(sources)} SERP queue items for {len(keywords)} keywords")
    
    for i, source in enumerate(sources):
        # Create SERP payload for this specific source
        serp_payload = {
            'keywords': keywords,
            'source': source,  # Single source per SERP item
            'source_index': i,
            'total_sources': len(sources),
            'extraction_mode': config.get('extraction_mode', 'summary'),
            'quality_threshold': config.get('quality_threshold', 0.8),
            'search_queries': self._generate_search_queries_for_source(keywords, source),
            'search_results': []
        }
        
        # Create queue item
        queue_item = QueueItemFactory.create_queue_item(
            queue_name="serp",
            project_id=project_id,
            project_request_id=request_id,
            priority=completed_item.get('priority', 'medium'),
            processing_strategy=completed_item.get('processing_strategy', 'table'),
            payload=serp_payload,
            metadata={
                **completed_item.get('metadata', {}),
                'source_name': source.get('name', ''),
                'source_type': source.get('type', ''),
                'created_from': 'request_acceptance'
            }
        )
        
        # Store in DynamoDB
        table_name = QUEUE_TABLES["serp"]  # "serp_queue"
        success = dynamodb_client.put_item(table_name, queue_item.dict())
```

**Key Points:**
- Creates **one SERP item per source** (not one item with all sources)
- Each SERP item has:
  - All keywords
  - Single source
  - Source index (for tracking)
  - Generated search queries specific to that source
- Preserves priority and processing_strategy from parent request

### Step 5: Search Query Generation

```python
def _generate_search_queries_for_source(self, keywords: List[str], source: Dict[str, Any]) -> List[str]:
    """Generate search queries for a specific source"""
    queries = []
    source_url = source.get('url', '')
    source_name = source.get('name', '')
    
    # Basic keyword queries
    for keyword in keywords:
        queries.append(keyword)
    
    # Source-specific queries
    if source_url:
        for keyword in keywords[:3]:  # Limit to first 3 keywords
            queries.append(f"{keyword} site:{source_url}")
    
    # Source name + keyword combinations
    if source_name:
        for keyword in keywords[:2]:  # Limit to first 2 keywords
            queries.append(f"{keyword} {source_name}")
    
    # Remove duplicates and limit
    unique_queries = list(set(queries))
    return unique_queries[:8]  # Limit to 8 queries per source
```

**Query Types Generated:**
1. **Basic queries:** Each keyword as-is
2. **Site-specific queries:** `{keyword} site:{source_url}` (max 3 keywords)
3. **Name-specific queries:** `{keyword} {source_name}` (max 2 keywords)
4. **Limit:** Maximum 8 unique queries per source

## DynamoDB Table Details

### Table: `request_queue_acceptance_queue`

**Schema:**
- **PK (Partition Key):** `{project_id}#{project_request_id}`
- **SK (Sort Key):** `request_acceptance#{timestamp}`
- **Status:** `pending` → `processing` → `completed`
- **Payload Structure:**
  ```json
  {
    "original_request": {...},
    "validation_results": {
      "is_valid": true,
      "errors": [],
      "warnings": []
    },
    "processing_plan": {
      "queues": ["serp", "perplexity", ...],
      "strategy": "table",
      "expected_items": {...},
      "estimated_duration_minutes": 45
    },
    "accepted_at": "2024-01-15T10:00:00Z"
  }
  ```

## Workflow After Completion

After `RequestAcceptanceWorker` completes:

1. **Status Updated:** Item status becomes `completed`
2. **SERP Items Created:** Multiple SERP queue items created (one per source)
3. **SERP Workers Start:** SERP workers pick up items and begin processing
4. **Next Phase:** SERP → Perplexity → Relevance/Insight/Implication

## Example Processing

**Input Request:**
```json
{
  "project_id": "proj_123",
  "project_request_id": "req_456",
  "user_id": "user_789",
  "priority": "high",
  "processing_strategy": "table",
  "config": {
    "keywords": ["FDA approval", "clinical trial"],
    "sources": [
      {"name": "FDA", "type": "regulatory", "url": "https://www.fda.gov"},
      {"name": "NIH", "type": "research", "url": "https://www.nih.gov"}
    ]
  }
}
```

**Processing Steps:**
1. Validates request (passes)
2. Creates processing plan:
   - Expected 2 SERP items (one per source)
   - Estimated 45 minutes
3. Creates 2 SERP queue items:
   - SERP item 1: FDA source + keywords
   - SERP item 2: NIH source + keywords
4. Updates status to `completed`

**Output:**
- 1 completed item in `request_queue_acceptance_queue`
- 2 pending items in `serp_queue` (one per source)

## Error Handling

- **Validation Failures:** Item marked as `failed`, no SERP items created
- **DynamoDB Errors:** Logged, item marked as `failed`
- **Partial Failures:** If some SERP items fail to create, others still proceed

## Configuration

- **Queue Table:** `QUEUE_TABLES["request_acceptance"]` = `"request_queue_acceptance_queue"`
- **Next Queue:** `QUEUE_WORKFLOW["request_acceptance"]` = `["serp"]`
- **Retry Logic:** Inherited from BaseWorker (max 3 retries)
