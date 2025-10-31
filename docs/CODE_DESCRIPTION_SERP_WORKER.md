# SERP Worker - Code Description

## Overview
The `SerpWorker` processes search engine results page (SERP) requests. It receives a single source and keywords, performs real search queries via SERP API, stores results in S3, and creates Perplexity queue items for the top URLs found.

## Location
**File:** `app/queues/serp/worker.py`  
**Class:** `SerpWorker(BaseWorker)`

## How SERP Queue Items are Created

### Creation Process (from RequestAcceptanceWorker)

When `RequestAcceptanceWorker` completes, it creates **one SERP queue item per source**:

```python
# In RequestAcceptanceWorker._create_next_queue_item()
for i, source in enumerate(sources):
    serp_payload = {
        'keywords': keywords,
        'source': source,  # Single source per item
        'source_index': i,
        'total_sources': len(sources),
        'search_queries': [...],
        'search_results': []
    }
    
    queue_item = QueueItemFactory.create_queue_item(
        queue_name="serp",
        project_id=project_id,
        project_request_id=request_id,
        payload=serp_payload
    )
    
    dynamodb_client.put_item("serp_queue", queue_item.dict())
```

**Result:**
- If request has 2 sources → 2 SERP queue items created
- If request has 5 sources → 5 SERP queue items created
- Each SERP item processes one source independently

## DynamoDB Table Details

### Table: `serp_queue`

**Schema:**
- **PK (Partition Key):** `{project_id}#{project_request_id}`
- **SK (Sort Key):** `serp#{timestamp}`
- **Status:** `pending` → `processing` → `completed`

**Payload Structure:**
```json
{
  "keywords": ["FDA approval", "clinical trial"],
  "source": {
    "name": "FDA",
    "type": "regulatory",
    "url": "https://www.fda.gov"
  },
  "source_index": 0,
  "total_sources": 2,
  "extraction_mode": "summary",
  "quality_threshold": 0.8,
  "search_queries": [
    "FDA approval",
    "clinical trial",
    "FDA approval site:fda.gov"
  ],
  "search_results": [],
  "s3_data_key": "raw-content/proj_123/req_456/serp/fda_123456.json",
  "processed_at": "2024-01-15T10:05:00Z",
  "total_results": 25,
  "urls_found": ["https://fda.gov/...", "..."]
}
```

**Table Creation:**
- Created via migration: `migrations/serp_migration.py`
- DynamoDB schema:
  - PK: String (HASH)
  - SK: String (RANGE)
  - BillingMode: PAY_PER_REQUEST

## Processing Flow

### Step 1: Receive Item
Worker polls `serp_queue` for items with `status = 'pending'`

### Step 2: Extract Payload Data
```python
def process_item(self, item: Dict[str, Any]) -> bool:
    payload = item.get('payload', {})
    keywords = payload.get('keywords', [])
    source = payload.get('source', {})
    search_queries = payload.get('search_queries', [])
    
    source_name = source.get('name', 'Unknown')
    logger.info(f"Processing SERP for source: {source_name} with {len(keywords)} keywords")
```

### Step 3: Get Real Search Results
```python
search_results = self._get_real_search_results(keywords, source)
```

**Method Implementation:**
```python
def _get_real_search_results(self, keywords: List[str], source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get real search results using SERP API"""
    try:
        # Run async processor in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.processor.process_search_data(keywords, source)
        )
        
        loop.close()
        
        if result['status'] == 'success':
            return result['search_results']
        else:
            logger.error(f"SERP API processing failed: {result.get('processing_metadata', {}).get('error')}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting real search results: {str(e)}")
        return []
```

**What happens:**
1. Calls `SerpProcessor.process_search_data()` (async)
2. Uses SERP API to search for keywords
3. Filters results by source URL (if applicable)
4. Returns list of search results with:
   - `url`: Result URL
   - `title`: Page title
   - `snippet`: Description snippet
   - `relevance_score`: Calculated relevance score
   - `position`: Search result position

**If no results found:**
- Returns empty list
- Item is still marked as `completed` (not failed)
- No Perplexity items created

### Step 4: Store Results in S3
```python
s3_key = s3_client.store_serp_data(project_id, request_id, {
    'source': source,
    'search_results': search_results,
    'keywords': keywords,
    'search_queries': search_queries,
    'processed_at': datetime.utcnow().isoformat(),
    'total_results': len(search_results)
})
```

**S3 Storage Path:**
- Path: `raw-content/{project_id}/{request_id}/serp/{source_name}_{timestamp}.json`
- Contains: Full search results, metadata, processing info

### Step 5: Update DynamoDB Payload
```python
updated_payload = payload.copy()
updated_payload.update({
    'search_results': search_results,
    's3_data_key': s3_key,
    'processed_at': datetime.utcnow().isoformat(),
    'total_results': len(search_results),
    'urls_found': [result.get('url') for result in search_results if result.get('url')]
})

dynamodb_client.update_item(
    table_name=self.table_name,
    key={'PK': item['PK'], 'SK': item['SK']},
    update_expression="SET payload = :payload, updated_at = :updated_at",
    expression_attribute_values={
        ':payload': updated_payload,
        ':updated_at': datetime.utcnow().isoformat()
    }
)
```

### Step 6: Trigger Perplexity Queue Creation
```python
# Create updated item for _trigger_next_queues
updated_item = item.copy()
updated_item['payload'] = updated_payload

# Manually trigger next queues with updated item
self._trigger_next_queues(updated_item)
```

**Note:** `SerpWorker` overrides `_trigger_next_queues()` to create multiple Perplexity items.

## Perplexity Queue Creation

### Override: `_trigger_next_queues()`

```python
def _trigger_next_queues(self, completed_item: Dict[str, Any]):
    """Override to create multiple Perplexity items - one for each URL (with limit)"""
    payload = completed_item.get('payload', {})
    search_results = payload.get('search_results', [])
    source = payload.get('source', {})
    keywords = payload.get('keywords', [])
    
    # Get URLs from search results
    urls_with_data = []
    for result in search_results:
        url = result.get('url')
        if url:
            urls_with_data.append({
                'url': url,
                'title': result.get('title', ''),
                'snippet': result.get('snippet', ''),
                'source': result.get('source', source.get('name', '')),
                'relevance_score': result.get('relevance_score', 0.5),
                'position': result.get('position', 999)
            })
    
    # Apply URL limit from configuration
    max_urls = QUEUE_PROCESSING_LIMITS.get('max_perplexity_urls_per_serp', 3)
    
    if len(urls_with_data) > max_urls:
        # Select best URLs using smart selection logic
        selected_urls = self._select_best_urls(urls_with_data, max_urls)
    else:
        selected_urls = urls_with_data
    
    # Create one Perplexity queue item for each selected URL
    for i, url_data in enumerate(selected_urls):
        user_prompt = self._create_url_analysis_prompt(url_data, keywords, source)
        
        perplexity_payload = {
            'user_prompt': user_prompt,
            'url_data': url_data,
            'source_info': {
                'name': source.get('name', ''),
                'type': source.get('type', ''),
                'keywords': keywords
            },
            'url_index': i + 1,
            'total_urls': len(selected_urls),
            'total_found_urls': len(urls_with_data),
            'url_limit_applied': len(urls_with_data) > max_urls
        }
        
        queue_item = QueueItemFactory.create_queue_item(
            queue_name="perplexity",
            project_id=project_id,
            project_request_id=request_id,
            payload=perplexity_payload
        )
        
        dynamodb_client.put_item("perplexity_queue", queue_item.dict())
```

**Key Points:**
- Creates **one Perplexity item per URL** (not one item with all URLs)
- **URL Limit:** Configurable via `QUEUE_PROCESSING_LIMITS['max_perplexity_urls_per_serp']` (default: 3)
- **URL Selection:** Uses `_select_best_urls()` to choose top URLs by relevance score
- **Prompt Generation:** Creates unique prompt for each URL

### URL Selection Logic

```python
def _select_best_urls(self, urls_with_data: List[Dict[str, Any]], max_urls: int) -> List[Dict[str, Any]]:
    """Select the best URLs for Perplexity processing - simple relevance-based selection"""
    
    # Sort by relevance score (highest first) and take top URLs
    sorted_urls = sorted(urls_with_data, key=lambda x: x.get('relevance_score', 0.0), reverse=True)
    selected = sorted_urls[:max_urls]
    
    logger.info(f"URL Selection Summary:")
    for i, url in enumerate(selected):
        logger.info(f"  {i+1}. Relevance: {url.get('relevance_score', 0.0):.2f} - {url['url'][:60]}...")
    
    if len(urls_with_data) > max_urls:
        logger.info(f"Skipped {len(urls_with_data) - max_urls} lower-relevance URLs")
    
    return selected
```

**Selection Criteria:**
- Sorts URLs by `relevance_score` (highest first)
- Takes top `max_urls` URLs
- Logs selection summary for debugging

## Configuration

**Processing Limits:**
```python
QUEUE_PROCESSING_LIMITS = {
    "max_perplexity_urls_per_serp": 3,  # Maximum URLs per SERP result
    "max_serp_results": 50,              # Maximum search results to process
    ...
}
```

**Workflow:**
```python
QUEUE_WORKFLOW = {
    "serp": ["perplexity"],  # SERP triggers Perplexity queue
    ...
}
```

## Example Processing Flow

**Input (SERP Queue Item):**
```json
{
  "PK": "proj_123#req_456",
  "SK": "serp#1705315200",
  "status": "pending",
  "payload": {
    "keywords": ["FDA approval", "clinical trial"],
    "source": {
      "name": "FDA",
      "type": "regulatory",
      "url": "https://www.fda.gov"
    },
    "search_queries": ["FDA approval", "clinical trial", "FDA approval site:fda.gov"]
  }
}
```

**Processing Steps:**
1. Worker picks up item, status → `processing`
2. Calls SERP API with keywords and source
3. Receives 25 search results
4. Stores results in S3: `raw-content/proj_123/req_456/serp/fda_123456.json`
5. Updates payload with search results
6. Selects top 3 URLs by relevance score
7. Creates 3 Perplexity queue items (one per URL)
8. Status → `completed`

**Output:**
- 1 completed item in `serp_queue`
- 3 pending items in `perplexity_queue` (one per selected URL)

## Error Handling

- **SERP API Errors:** Logged, item marked as `failed`
- **No Results Found:** Item marked as `completed`, no Perplexity items created
- **Partial URL Creation:** If some Perplexity items fail to create, others still proceed
- **S3 Storage Errors:** Item marked as `failed`, no Perplexity items created

## Status Transitions

- `pending` → `processing` → `completed` (success)
- `pending` → `processing` → `failed` (error)
- `pending` → `processing` → `retry` → `completed` (retry success)
