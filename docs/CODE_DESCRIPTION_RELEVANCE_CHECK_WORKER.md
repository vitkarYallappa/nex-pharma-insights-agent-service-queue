# Relevance Check Worker - Code Description

## Overview
The `RelevanceCheckWorker` processes relevance checks after Perplexity has fetched and summarized content from URLs. It analyzes the Perplexity response to determine how relevant the content is to the original keywords and user prompt, then stores the relevance analysis in S3 and additional database tables.

## Location
**File:** `app/queues/relevance_check/worker.py`  
**Class:** `RelevanceCheckWorker(BaseWorker)`

## How Relevance Check Queue Items are Created

### Creation Process (from PerplexityWorker)

When `PerplexityWorker` completes processing a URL, it creates **one relevance_check queue item** along with insight and implication items:

```python
# In PerplexityWorker._trigger_next_queues()
next_queues = ['relevance_check', 'insight', 'implication']

for queue_name in next_queues:
    next_payload = {
        'perplexity_response': perplexity_response,
        'url_data': url_data,
        'content_id': content_id,
        'user_prompt': user_prompt,
        ...
    }
    
    queue_item = QueueItemFactory.create_queue_item(
        queue_name=queue_name,
        project_id=project_id,
        project_request_id=request_id,
        payload=next_payload
    )
    
    dynamodb_client.put_item("relevance_check_queue", queue_item.dict())
```

**Result:**
- One relevance_check item is created per Perplexity-processed URL
- Processed in parallel with insight and implication items
- All three workers process the same Perplexity response independently

## DynamoDB Table Details

### Table: `relevance_check_queue`

**Schema:**
- **PK (Partition Key):** `{project_id}#{project_request_id}`
- **SK (Sort Key):** `relevance_check#{timestamp}`
- **Status:** `pending` → `processing` → `completed`

**Payload Structure:**
```json
{
  "content_id": "content_abc123",
  "perplexity_response": "<div>...summary from Perplexity...</div>",
  "url_data": {
    "url": "https://fda.gov/...",
    "title": "FDA Approval Process",
    "relevance_score": 0.95
  },
  "user_prompt": "Analyze the following URL about FDA approval...",
  "url_index": 1,
  "total_urls": 3,
  "relevance_response": "...relevance analysis from Bedrock...",
  "relevance_success": true,
  "s3_relevance_key": "processed/proj_123/req_456/relevance/content_abc123.json",
  "processed_at": "2024-01-15T10:10:00Z"
}
```

**Table Creation:**
- Created via migration: `migrations/relevance_check_migration.py`
- DynamoDB schema:
  - PK: String (HASH)
  - SK: String (RANGE)
  - BillingMode: PAY_PER_REQUEST

## Processing Flow

### Step 1: Receive Item
Worker polls `relevance_check_queue` for items with `status = 'pending'`

### Step 2: Extract Payload Data
```python
async def process_item(self, item: Dict[str, Any]) -> bool:
    payload = item.get('payload', {})
    
    # Extract key information
    content_id = payload.get('content_id', 'Unknown')
    perplexity_response = payload.get('perplexity_response', '')
    url_data = payload.get('url_data', {})
    url_index = payload.get('url_index', 1)
    total_urls = payload.get('total_urls', 1)
    user_prompt = payload.get('user_prompt', '')
    
    if not perplexity_response:
        logger.error(f"No Perplexity response found for content ID: {content_id}")
        return False
    
    url = url_data.get('url', 'Unknown URL')
    logger.info(f"🔍 RELEVANCE CHECK - Content ID: {content_id} | URL {url_index}/{total_urls}: {url[:50]}...")
```

### Step 3: Process Relevance Check (Async)
```python
relevance_result = await self.processor.check_relevance(
    perplexity_response=perplexity_response,
    url_data=url_data,
    user_prompt=user_prompt,
    content_id=content_id,
    project_id=project_id,
    request_id=request_id
)
```

**Method Implementation:**
The `RelevanceCheckProcessor.check_relevance()` method:
1. Uses AWS Bedrock (Claude model) to analyze relevance
2. Compares Perplexity response against:
   - Original user prompt
   - Original keywords from request
   - Source requirements
3. Returns relevance analysis with:
   - Relevance score (0.0 to 1.0)
   - Relevance explanation
   - Key points matching/not matching
   - Overall relevance determination

**Relevance Analysis Criteria:**
- **Content Match:** Does the content address the keywords/topic?
- **Source Alignment:** Does it match the expected source type?
- **Information Quality:** Is the information useful and relevant?
- **Completeness:** Does it provide sufficient detail?

### Step 4: Store Relevance Analysis in S3
```python
s3_key = s3_client.store_insights(project_id, request_id, {
    'content_id': content_id,
    'relevance_analysis': relevance_result.get('relevance_analysis', ''),
    'url_data': url_data,
    'processing_metadata': relevance_result.get('processing_metadata', {}),
    'processed_at': datetime.utcnow().isoformat(),
    'url_index': url_index,
    'total_urls': total_urls
})
```

**S3 Storage Path:**
- Path: `processed/{project_id}/{request_id}/relevance/{content_id}_{timestamp}.json`
- Contains: Full relevance analysis, metadata, processing info

### Step 5: Update DynamoDB Payload
```python
updated_payload = payload.copy()
updated_payload.update({
    'relevance_response': relevance_result.get('relevance_analysis', ''),
    'relevance_success': relevance_result.get('success', False),
    's3_relevance_key': s3_key,
    'processed_at': datetime.utcnow().isoformat()
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

### Step 6: Additional Database Operations
```python
# Process additional DB operations for content_relevance table
db_data = {
    'content_id': content_id,
    'project_id': project_id,
    'request_id': request_id,
    'relevance_response': relevance_result.get('relevance_analysis', ''),
    'relevance_success': relevance_result.get('success', False),
    's3_relevance_key': s3_key,
    'url_data': url_data,
    'processing_metadata': relevance_result.get('processing_metadata', {}),
    'url_index': url_index,
    'total_urls': total_urls
}

# Call DB operations service for content_relevance table
db_results = relevance_check_db_operations_service.process_relevance_completion(db_data)

if db_results.get('content_relevance_result', {}).get('success'):
    logger.info(f"✅ RELEVANCE DB SUCCESS - Content ID: {content_id} | Stored in content_relevance table")
else:
    logger.error(f"❌ RELEVANCE DB FAILED - Content ID: {content_id} | Failed to store in content_relevance table")
```

**What happens:**
1. Calls `relevance_check_db_operations_service.process_relevance_completion()`
2. Creates/updates records in `content_relevance` table
3. Links relevance analysis to content_id
4. Stores relevance score and analysis for later filtering/ranking

## Async Processing

**Important:** `RelevanceCheckWorker` processes items **asynchronously**:

```python
def _process_item(self, item: Dict[str, Any]):
    """Override base worker's _process_item to handle async processing"""
    # Update status to processing
    self._update_item_status(pk, sk, QueueStatus.PROCESSING)
    
    # Process the item asynchronously
    success = asyncio.run(self.process_item(item))
    
    if success:
        self._update_item_status(pk, sk, QueueStatus.COMPLETED)
    else:
        self._handle_processing_failure(item)
```

**Why Async:**
- Bedrock API calls are async by nature
- Allows concurrent processing of multiple items
- Better resource utilization

## Next Queue Creation

**Relevance checks typically don't trigger next queues** - they are a final step in the pipeline:

```python
def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare payload for next queue (if any)"""
    # Relevance checks can trigger further processing based on relevance score
    return {}
```

**Workflow:**
```python
QUEUE_WORKFLOW = {
    "relevance_check": [],  # No next queues - final step
    ...
}
```

**Future Enhancement:**
- Could trigger additional processing based on relevance score
- Could filter out low-relevance content before insight/implication processing
- Currently processes independently of insight/implication workers

## Configuration

**Workflow:**
```python
QUEUE_WORKFLOW = {
    "relevance_check": [],  # Relevance check is a final step
    ...
}
```

**Processing:**
- Uses AWS Bedrock (Claude model) for relevance analysis
- Async processing for better performance
- Stores results in both DynamoDB and S3

## Example Processing Flow

**Input (Relevance Check Queue Item):**
```json
{
  "PK": "proj_123#req_456",
  "SK": "relevance_check#1705315400",
  "status": "pending",
  "payload": {
    "content_id": "content_abc123",
    "perplexity_response": "<div>...FDA approval process summary...</div>",
    "url_data": {
      "url": "https://fda.gov/approvals/drug-123",
      "title": "FDA Drug Approval",
      "relevance_score": 0.95
    },
    "user_prompt": "Analyze URL about FDA approval and clinical trials",
    "url_index": 1,
    "total_urls": 3
  }
}
```

**Processing Steps:**
1. Worker picks up item, status → `processing`
2. Calls Bedrock API to analyze relevance
3. Bedrock analyzes:
   - Content vs keywords ("FDA approval", "clinical trial")
   - Content vs user prompt
   - Source type alignment
   - Information quality
4. Receives relevance analysis with score (e.g., 0.92)
5. Stores analysis in S3: `processed/proj_123/req_456/relevance/content_abc123.json`
6. Updates `content_relevance` table with relevance data
7. Updates payload with relevance response
8. Status → `completed`

**Output:**
- 1 completed item in `relevance_check_queue`
- Relevance analysis stored in S3
- Relevance data in `content_relevance` table
- Content can be filtered/ranked by relevance score

## Error Handling

- **Bedrock API Errors:** Logged, item marked as `failed`, error analysis stored
- **DB Operations Errors:** Logged but doesn't fail main process, continues without DB update
- **Missing Perplexity Response:** Item marked as `failed`, no relevance check possible
- **S3 Storage Errors:** Item marked as `failed`, relevance analysis lost

## Status Transitions

- `pending` → `processing` → `completed` (success)
- `pending` → `processing` → `failed` (error)
- `pending` → `processing` → `retry` → `completed` (retry success)

## Integration with Other Workers

**Parallel Processing:**
- Relevance check processes **in parallel** with insight and implication workers
- All three receive the same Perplexity response
- All three can use relevance score for filtering/prioritization

**Data Flow:**
```
PerplexityWorker
    ↓
    ├─→ RelevanceCheckWorker → content_relevance table
    ├─→ InsightWorker → content_insight table
    └─→ ImplicationWorker → content_implication table
```

**Use Cases:**
- Filter low-relevance content before final analysis
- Rank content by relevance for insights/implications
- Track relevance metrics for quality assurance
