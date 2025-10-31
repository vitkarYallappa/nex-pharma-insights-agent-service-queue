# Insight Worker - Code Description

## Overview
The `InsightWorker` processes Perplexity responses to generate market insights. It uses AWS Bedrock (Claude model) to analyze content and extract key market intelligence, trends, patterns, and actionable insights. The results are stored in S3 and additional database tables.

## Location
**File:** `app/queues/insight/worker.py`  
**Class:** `InsightWorker(BaseWorker)`

## How Insight Queue Items are Created

### Creation Process (from PerplexityWorker)

When `PerplexityWorker` completes processing a URL, it creates **one insight queue item** along with relevance_check and implication items:

```python
# In PerplexityWorker._trigger_next_queues()
next_queues = ['relevance_check', 'insight', 'implication']

for queue_name in next_queues:
    next_payload = {
        'perplexity_response': perplexity_response,
        'url_data': url_data,
        'content_id': content_id,
        'analysis_type': 'market_insights',
        ...
    }
    
    queue_item = QueueItemFactory.create_queue_item(
        queue_name=queue_name,
        project_id=project_id,
        project_request_id=request_id,
        payload=next_payload
    )
    
    dynamodb_client.put_item("insight_queue", queue_item.dict())
```

**Result:**
- One insight item is created per Perplexity-processed URL
- Processed in parallel with relevance_check and implication items
- All three workers process the same Perplexity response independently

## DynamoDB Table Details

### Table: `insight_queue`

**Schema:**
- **PK (Partition Key):** `{project_id}#{project_request_id}`
- **SK (Sort Key):** `insight#{timestamp}`
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
  "analysis_type": "market_insights",
  "user_prompt": "Analyze the following URL about FDA approval...",
  "url_index": 1,
  "total_urls": 3,
  "insights_response": "...market insights from Bedrock...",
  "insights_success": true,
  "s3_insights_key": "processed/proj_123/req_456/insights/content_abc123.json",
  "processed_at": "2024-01-15T10:12:00Z"
}
```

**Table Creation:**
- Created via migration: `migrations/insight_migration.py`
- DynamoDB schema:
  - PK: String (HASH)
  - SK: String (RANGE)
  - BillingMode: PAY_PER_REQUEST

## Processing Flow

### Step 1: Receive Item
Worker polls `insight_queue` for items with `status = 'pending'`

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
    logger.info(f"🔍 INSIGHT PROCESSING - Content ID: {content_id} | URL {url_index}/{total_urls}: {url[:50]}...")
```

### Step 3: Process Insights (Async)
```python
insight_result = await self.processor.generate_insights(
    perplexity_response=perplexity_response,
    url_data=url_data,
    user_prompt=user_prompt,
    content_id=content_id
)
```

**Method Implementation:**
The `InsightProcessor.generate_insights()` method:
1. Uses AWS Bedrock (Claude model) to analyze content
2. Extracts market insights such as:
   - **Key Findings:** Important discoveries or data points
   - **Market Trends:** Emerging or existing market trends
   - **Industry Patterns:** Patterns across the industry
   - **Data Points:** Significant statistics or metrics
   - **Market Dynamics:** How market forces are changing
   - **Competitive Landscape:** Competitive market observations
   - **Regulatory Trends:** Regulatory pattern observations
3. Structures insights in a clear, actionable format
4. Returns formatted insights content

**Insight Analysis Focus:**
- **Market Intelligence:** What does this tell us about the market?
- **Trend Identification:** What trends are emerging?
- **Data Analysis:** What are the key data points?
- **Market Understanding:** Deeper understanding of market conditions
- **Pattern Recognition:** What patterns exist in the data?
- **Industry Context:** How does this fit into industry landscape?

### Step 4: Store Insights in S3
```python
s3_key = s3_client.store_insights(project_id, request_id, {
    'content_id': content_id,
    'insights': insight_result.get('insights', ''),
    'url_data': url_data,
    'processing_metadata': insight_result.get('processing_metadata', {}),
    'processed_at': datetime.utcnow().isoformat(),
    'url_index': url_index,
    'total_urls': total_urls
})
```

**S3 Storage Path:**
- Path: `processed/{project_id}/{request_id}/insights/{content_id}_{timestamp}.json`
- Contains: Full insights analysis, metadata, processing info

### Step 5: Update DynamoDB Payload
```python
updated_payload = payload.copy()
updated_payload.update({
    'insights_response': insight_result.get('insights', ''),
    'insights_success': insight_result.get('success', False),
    's3_insights_key': s3_key,
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
# Process additional DB operations for content_insight table
db_data = {
    'content_id': content_id,
    'project_id': project_id,
    'request_id': request_id,
    'insights_response': insight_result.get('insights', ''),
    'insights_success': insight_result.get('success', False),
    's3_insights_key': s3_key,
    'url_data': url_data,
    'processing_metadata': insight_result.get('processing_metadata', {}),
    'url_index': url_index,
    'total_urls': total_urls
}

# Call DB operations service for content_insight table
db_results = insight_db_operations_service.process_insight_completion(db_data)

if db_results.get('content_insight_result', {}).get('success'):
    logger.info(f"✅ INSIGHT DB SUCCESS - Content ID: {content_id} | Stored in content_insight table")
else:
    logger.error(f"❌ INSIGHT DB FAILED - Content ID: {content_id} | Failed to store in content_insight table")
```

**What happens:**
1. Calls `insight_db_operations_service.process_insight_completion()`
2. Creates/updates records in `content_insight` table
3. Links insights to content_id for tracking
4. Stores structured insights for retrieval and analysis

## Async Processing

**Important:** `InsightWorker` processes items **asynchronously**:

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
- Can process insights in parallel with implications

## Next Queue Creation

**Insights are typically a final step** - they don't trigger next queues:

```python
def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare payload for next queue (if any)"""
    # Insights are typically final, but can be extended if needed
    return {}
```

**Workflow:**
```python
QUEUE_WORKFLOW = {
    "insight": [],  # No next queues - final step
    ...
}
```

**Future Enhancement:**
- Could trigger report generation based on insights
- Could aggregate insights across multiple URLs
- Could trigger alerts for critical insights
- Could feed into dashboard or visualization systems

## Configuration

**Workflow:**
```python
QUEUE_WORKFLOW = {
    "insight": [],  # Final step in pipeline
    ...
}
```

**Processing:**
- Uses AWS Bedrock (Claude model) for insight generation
- Async processing for better performance
- Stores results in both DynamoDB and S3
- Uses `insight_db_operations_service` for database operations

## Example Processing Flow

**Input (Insight Queue Item):**
```json
{
  "PK": "proj_123#req_456",
  "SK": "insight#1705315450",
  "status": "pending",
  "payload": {
    "content_id": "content_abc123",
    "perplexity_response": "<div>...FDA approval process summary...</div>",
    "url_data": {
      "url": "https://fda.gov/approvals/drug-123",
      "title": "FDA Drug Approval",
      "relevance_score": 0.95
    },
    "analysis_type": "market_insights",
    "user_prompt": "Analyze URL about FDA approval and clinical trials",
    "url_index": 1,
    "total_urls": 3
  }
}
```

**Processing Steps:**
1. Worker picks up item, status → `processing`
2. Calls Bedrock API (Claude model) to generate insights
3. Bedrock analyzes content and extracts:
   - Key findings about FDA approval process
   - Market trends in pharmaceutical approvals
   - Industry patterns in regulatory compliance
   - Data points on approval timelines
   - Market dynamics affecting approvals
   - Competitive landscape observations
   - Regulatory trend insights
4. Receives structured insights content
5. Stores insights in S3: `processed/proj_123/req_456/insights/content_abc123.json`
6. Updates `content_insight` table with insights data
7. Updates payload with insights response
8. Status → `completed`

**Example Insights Output:**
```
Key Findings:
- Average FDA approval time decreased by 15% in 2024
- Priority review designations increased by 30%
- Breakthrough therapy designations show significant growth

Market Trends:
- Accelerated approval pathway usage increased
- More companies leveraging real-world evidence
- Digital health tools integration in trials rising

Industry Patterns:
- Smaller biotech companies achieving faster approvals
- Orphan drug designations seeing increased utilization
- Collaboration between FDA and industry improving

Data Points:
- Median approval time: 12.5 months (down from 14.7 months)
- First-cycle approval rate: 68% (up from 62%)
- Supplemental approval volume: +25% year-over-year

Market Dynamics:
- Regulatory environment becoming more supportive
- Increased focus on patient-centered approaches
- Growing importance of real-world evidence

Competitive Landscape:
- Top 10 pharma companies account for 45% of approvals
- Biotech companies represent 55% of new approvals
- Strategic partnerships critical for success

Regulatory Trends:
- Adaptive trial designs gaining acceptance
- Real-world evidence playing larger role
- Digital endpoints being incorporated
```

**Output:**
- 1 completed item in `insight_queue`
- Insights analysis stored in S3
- Insights data in `content_insight` table
- Market intelligence ready for analysis and decision-making

## Error Handling

- **Bedrock API Errors:** Logged, item marked as `failed`, error content stored
- **DB Operations Errors:** Logged but doesn't fail main process, continues without DB update
- **Missing Perplexity Response:** Item marked as `failed`, no insights possible
- **S3 Storage Errors:** Item marked as `failed`, insights analysis lost

## Status Transitions

- `pending` → `processing` → `completed` (success)
- `pending` → `processing` → `failed` (error)
- `pending` → `processing` → `retry` → `completed` (retry success)

## Integration with Other Workers

**Parallel Processing:**
- Insight worker processes **in parallel** with relevance_check and implication workers
- All three receive the same Perplexity response
- All three analyze different aspects:
  - **Relevance Check:** Is it relevant?
  - **Insight:** What are the key insights?
  - **Implication:** What are the business implications?

**Data Flow:**
```
PerplexityWorker
    ↓
    ├─→ RelevanceCheckWorker → content_relevance table
    ├─→ InsightWorker → content_insight table
    └─→ ImplicationWorker → content_implication table
```

**Use Cases:**
- Market intelligence gathering
- Trend analysis and identification
- Competitive landscape assessment
- Regulatory pattern recognition
- Data-driven decision making
- Industry analysis and reporting

## Differences from Implication Worker

**Insight Worker focuses on:**
- **Market intelligence:** What does this mean for the market?
- **Data analysis:** Key patterns and trends
- **Market observations:** Market-level insights
- **Trend identification:** Emerging trends
- **Market understanding:** Deeper market knowledge

**Implication Worker focuses on:**
- **Business actions:** What should we do?
- **Strategic recommendations:** Actionable strategies
- **Business impact:** How this affects business
- **Risk/opportunity:** Risks and opportunities
- **Decision support:** Information for decision-making

Both complement each other for comprehensive market intelligence - insights provide the "what" and implications provide the "so what" and "what to do about it."
