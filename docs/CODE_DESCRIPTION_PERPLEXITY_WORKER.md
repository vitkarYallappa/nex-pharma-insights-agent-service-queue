# Perplexity Worker - Code Description

## Overview
The `PerplexityWorker` processes URLs from SERP results by calling the Perplexity AI API to fetch and summarize content from each URL. It stores the Perplexity response in S3, performs additional database operations, and creates three parallel queue items: relevance_check, insight, and implication.

## Location
**File:** `app/queues/perplexity/worker.py`  
**Class:** `PerplexityWorker(BaseWorker)`

## How Perplexity Queue Items are Created

### Creation Process (from SerpWorker)

When `SerpWorker` completes processing search results, it creates **one Perplexity queue item per selected URL**:

```python
# In SerpWorker._trigger_next_queues()
selected_urls = self._select_best_urls(urls_with_data, max_urls)  # Top 3 URLs

for i, url_data in enumerate(selected_urls):
    user_prompt = self._create_url_analysis_prompt(url_data, keywords, source)
    
    perplexity_payload = {
        'user_prompt': user_prompt,
        'url_data': url_data,
        'source_info': {...},
        'url_index': i + 1,
        'total_urls': len(selected_urls),
        'url_limit_applied': True
    }
    
    queue_item = QueueItemFactory.create_queue_item(
        queue_name="perplexity",
        project_id=project_id,
        project_request_id=request_id,
        payload=perplexity_payload
    )
    
    dynamodb_client.put_item("perplexity_queue", queue_item.dict())
```

**Result:**
- If SERP found 25 URLs and limit is 3 → 3 Perplexity items created
- Each Perplexity item processes one URL independently

## DynamoDB Table Details

### Table: `perplexity_queue`

**Schema:**
- **PK (Partition Key):** `{project_id}#{project_request_id}`
- **SK (Sort Key):** `perplexity#{timestamp}`
- **Status:** `pending` → `processing` → `completed`

**Payload Structure:**
```json
{
  "user_prompt": "Analyze the following URL about FDA approval...",
  "url_data": {
    "url": "https://fda.gov/...",
    "title": "FDA Approval Process",
    "snippet": "Information about...",
    "relevance_score": 0.95,
    "position": 1
  },
  "source_info": {
    "name": "FDA",
    "type": "regulatory",
    "keywords": ["FDA approval"]
  },
  "url_index": 1,
  "total_urls": 3,
  "perplexity_response": "<div>...summary from Perplexity...</div>",
  "perplexity_success": true,
  "s3_perplexity_key": "raw-content/proj_123/req_456/content/url_123456.json",
  "main_content": "...extracted content...",
  "publish_date": "2024-01-10",
  "source_category": "regulatory",
  "content_id": "content_abc123"
}
```

## Processing Flow

### Step 1: Receive Item
Worker polls `perplexity_queue` for items with `status = 'pending'`

### Step 2: Extract Payload Data
```python
def process_item(self, item: Dict[str, Any]) -> bool:
    payload = item.get('payload', {})
    
    # Get user prompt from payload
    user_prompt = payload.get('analysis_prompt', '') or payload.get('user_prompt', '')
    url_data = payload.get('url_data', {})
    url_index = payload.get('url_index', 1)
    total_urls = payload.get('total_urls', 1)
    
    url = url_data.get('url', 'Unknown URL')
    logger.info(f"Processing Perplexity request {url_index}/{total_urls} for URL: {url[:50]}...")
```

### Step 3: Call Perplexity API
```python
perplexity_result = self._call_perplexity(user_prompt, payload)
```

**Method Implementation:**
```python
def _call_perplexity(self, user_prompt: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Call Perplexity with user prompt"""
    try:
        # Run async processor in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.processor.process_user_prompt(user_prompt, context_data)
        )
        
        loop.close()
        
        return result
            
    except Exception as e:
        logger.error(f"Error calling Perplexity: {str(e)}")
        return {
            'perplexity_response': f"<div><p>Error: {str(e)}</p></div>",
            'success': False,
            'formatted_data': {
                'main_content': f"<div><p>Error: {str(e)}</p></div>",
                'publish_date': None,
                'source_category': None
            }
        }
```

**What happens:**
1. Calls `PerplexityProcessor.process_user_prompt()` (async)
2. Perplexity API fetches content from URL and generates summary
3. Returns structured response with:
   - `perplexity_response`: HTML summary from Perplexity
   - `formatted_data`: Parsed and formatted content
   - `parsed_data`: Raw parsed data
   - `processing_metadata`: Processing info

### Step 4: Store Perplexity Response in S3
```python
s3_key = s3_client.store_content_data(project_id, request_id, {
    'user_prompt': user_prompt,
    'url_data': url_data,
    'perplexity_response': perplexity_result.get('perplexity_response', ''),
    'success': perplexity_result.get('success', False),
    'processed_at': datetime.utcnow().isoformat(),
    'processing_metadata': perplexity_result.get('processing_metadata', {}),
    'parsed_data': perplexity_result.get('parsed_data', {}),
    'formatted_data': perplexity_result.get('formatted_data', {}),
    'url_index': url_index,
    'total_urls': total_urls
})
```

**S3 Storage Path:**
- Path: `raw-content/{project_id}/{request_id}/content/{url_hash}_{timestamp}.json`
- Contains: Full Perplexity response, metadata, processing info

### Step 5: Additional Database Operations
```python
# Process additional table operations
db_data = {
    'project_id': project_id,
    'request_id': request_id,
    'url_data': url_data,
    'perplexity_response': perplexity_result.get('perplexity_response', ''),
    'source_info': payload.get('source_info', {}),
    'processing_metadata': perplexity_result.get('processing_metadata', {}),
    'url_index': url_index,
    'total_urls': total_urls,
    'publish_date': formatted_data.get('publish_date'),
    'source_category': formatted_data.get('source_category')
}

# Call DB operations service for additional tables
db_results = db_operations_service.process_perplexity_completion(db_data)

# Extract content_id from DB operations result
content_id = db_results.get('content_id')
if content_id:
    updated_payload['content_id'] = content_id
    logger.info(f"Content ID {content_id} assigned for URL {url_index}/{total_urls}")
```

**What happens:**
1. Calls `db_operations_service.process_perplexity_completion()`
2. Creates/updates records in additional database tables (e.g., `content_repository`)
3. Returns `content_id` for tracking
4. Updates payload with `content_id`

### Step 6: Update DynamoDB Payload
```python
formatted_data = perplexity_result.get('formatted_data', {})
updated_payload = payload.copy()
updated_payload.update({
    'perplexity_response': perplexity_result.get('perplexity_response', ''),
    'perplexity_success': perplexity_result.get('success', False),
    's3_perplexity_key': s3_key,
    'processed_at': datetime.utcnow().isoformat(),
    'main_content': formatted_data.get('main_content', ''),
    'publish_date': formatted_data.get('publish_date'),
    'source_category': formatted_data.get('source_category'),
    'content_id': content_id  # From DB operations
})

dynamodb_client.update_item(...)
```

### Step 7: Trigger Next Queues (Relevance, Insight, Implication)
```python
# Create updated item for _trigger_next_queues
updated_item = item.copy()
updated_item['payload'] = updated_payload

# Trigger next queues manually
self._trigger_next_queues(updated_item)
```

**Note:** `PerplexityWorker` overrides `_trigger_next_queues()` to create **three parallel queue items**.

## Next Queue Creation (Relevance, Insight, Implication)

### Override: `_trigger_next_queues()`

```python
def _trigger_next_queues(self, completed_item: Dict[str, Any]):
    """Override to create BOTH relevance_check, insight and implication queue items for this URL"""
    project_id, request_id = self._extract_ids_from_pk(completed_item.get('PK', ''))
    payload = completed_item.get('payload', {})
    
    url_data = payload.get('url_data', {})
    url_index = payload.get('url_index', 1)
    total_urls = payload.get('total_urls', 1)
    perplexity_response = payload.get('perplexity_response', '')
    content_id = payload.get('content_id', '')
    
    # Create relevance_check, insight and implication queue items for this URL
    next_queues = ['relevance_check', 'insight', 'implication']
    logger.info(f"Creating relevance_check + insight + implication queue items for URL {url_index}/{total_urls}")
    
    for queue_name in next_queues:
        # Create payload for next queue
        next_payload = {
            'perplexity_response': perplexity_response,
            'perplexity_success': payload.get('perplexity_success', False),
            's3_perplexity_key': payload.get('s3_perplexity_key', ''),
            'url_data': url_data,
            'analysis_type': 'market_insights' if queue_name == 'insight' else 'business_implications',
            'user_prompt': payload.get('user_prompt', ''),
            'source_info': payload.get('source_info', {}),
            'url_index': url_index,
            'total_urls': total_urls,
            'content_id': content_id,  # Pass content ID to next queues
            'main_content': payload.get('main_content', ''),
            'publish_date': payload.get('publish_date'),
            'source_category': payload.get('source_category')
        }
        
        # Create queue item
        queue_item = QueueItemFactory.create_queue_item(
            queue_name=queue_name,
            project_id=project_id,
            project_request_id=request_id,
            priority=completed_item.get('priority', 'medium'),
            processing_strategy=completed_item.get('processing_strategy', 'table'),
            payload=next_payload,
            metadata={
                **completed_item.get('metadata', {}),
                'url': url_data.get('url', ''),
                'url_index': url_index,
                'total_urls': total_urls,
                'analysis_type': next_payload['analysis_type'],
                'created_from': 'perplexity'
            }
        )
        
        # Store in DynamoDB
        table_name = QUEUE_TABLES[queue_name]
        success = dynamodb_client.put_item(table_name, queue_item.dict())
```

**Key Points:**
- Creates **three separate queue items**:
  1. **relevance_check** - Checks content relevance
  2. **insight** - Generates market insights
  3. **implication** - Generates business implications
- All three items process **the same Perplexity response** in parallel
- Each item receives:
  - `content_id` for tracking
  - `perplexity_response` (full HTML)
  - `url_data` (original URL info)
  - `source_info` (source metadata)

## Conditions and Decision Points

### Condition 1: Perplexity API Success/Failure
- **If success:** Continue to next queues (relevance, insight, implication)
- **If failure:** Mark item as `failed`, no next queues created

### Condition 2: Content ID Assignment
- **If content_id assigned:** Passed to next queues for tracking
- **If content_id not assigned:** Next queues still proceed, but tracking may be incomplete

### Condition 3: URL Processing
- Each URL is processed independently
- Multiple URLs from same SERP result are processed in parallel (separate Perplexity items)

### Condition 4: Parallel Queue Creation
- All three next queues (relevance, insight, implication) are created regardless of each other
- They process independently and in parallel

## Configuration

**Workflow:**
```python
QUEUE_WORKFLOW = {
    "perplexity": ["relevance_check", "insight", "implication"],
    ...
}
```

**Note:** The code creates all three queues regardless of workflow config (overridden behavior).

## Example Processing Flow

**Input (Perplexity Queue Item):**
```json
{
  "PK": "proj_123#req_456",
  "SK": "perplexity#1705315300",
  "status": "pending",
  "payload": {
    "user_prompt": "Analyze URL: https://fda.gov/approvals...",
    "url_data": {
      "url": "https://fda.gov/approvals/drug-123",
      "title": "FDA Drug Approval",
      "relevance_score": 0.95
    },
    "url_index": 1,
    "total_urls": 3
  }
}
```

**Processing Steps:**
1. Worker picks up item, status → `processing`
2. Calls Perplexity API with user prompt
3. Receives HTML summary from Perplexity
4. Stores response in S3: `raw-content/proj_123/req_456/content/url_123456.json`
5. Calls DB operations service → gets `content_id: "content_abc123"`
6. Updates payload with Perplexity response and content_id
7. Creates 3 next queue items:
   - relevance_check queue item
   - insight queue item
   - implication queue item
8. Status → `completed`

**Output:**
- 1 completed item in `perplexity_queue`
- 3 pending items in `relevance_check_queue`
- 3 pending items in `insight_queue`
- 3 pending items in `implication_queue`

## Error Handling

- **Perplexity API Errors:** Logged, item marked as `failed`, error response stored
- **DB Operations Errors:** Logged but doesn't fail main process, continues without content_id
- **Partial Queue Creation:** If some next queues fail to create, others still proceed
- **S3 Storage Errors:** Item marked as `failed`, no next queues created

## Status Transitions

- `pending` → `processing` → `completed` (success)
- `pending` → `processing` → `failed` (error)
- `pending` → `processing` → `retry` → `completed` (retry success)
