# Market Intelligence Request Route - Code Description

## Overview
This document describes the `/market-intelligence-requests` POST endpoint that initiates the entire queue-based processing pipeline.

## Endpoint Details

**Route:** `POST /api/v1/market-intelligence-requests`  
**Response Model:** `RequestResponse`  
**Location:** `app/api/v1/routes.py` (lines 101-173)

## Function Flow

### 1. Request Validation
```python
@router.post("/market-intelligence-requests", response_model=RequestResponse)
async def create_market_intelligence_request(
    request: MarketIntelligenceRequest,
    background_tasks: BackgroundTasks
):
```

**What happens:**
- Receives a `MarketIntelligenceRequest` object containing:
  - `project_id`: Unique project identifier
  - `project_request_id`: Unique request identifier
  - `user_id`: User identifier
  - `priority`: Processing priority (high/medium/low)
  - `processing_strategy`: Processing strategy (table/stream/batch)
  - `config`: Request configuration with keywords and sources

### 2. Request Validation Process
```python
validation_errors = _validate_request(request)
```

**Validation checks:**
- Ensures at least one keyword is provided
- Ensures at least one source is provided
- Validates each source has `name`, `url`, and `type`
- Limits keywords to maximum 20
- Limits sources to maximum 10

**Error handling:**
- Returns HTTP 400 with detailed error messages if validation fails

### 3. Queue Item Creation
```python
queue_item = QueueItemFactory.create_queue_item(
    queue_name="request_acceptance",
    project_id=request.project_id,
    project_request_id=request.project_request_id,
    priority=request.priority,
    processing_strategy=request.processing_strategy,
    payload={
        'original_request': request.dict(),
        'validation_results': {},
        'processing_plan': {}
    },
    metadata={
        'user_id': request.user_id,
        'submitted_at': datetime.utcnow().isoformat(),
        'api_version': settings.app_version
    }
)
```

**Key Components:**
- **Queue Name:** `request_acceptance` (first queue in the pipeline)
- **PK (Partition Key):** `{project_id}#{project_request_id}`
- **SK (Sort Key):** `request_acceptance#{timestamp}`
- **Status:** Automatically set to `pending`
- **Payload:** Contains the original request, validation results, and processing plan (filled later)

### 4. DynamoDB Storage
```python
table_name = QUEUE_TABLES["request_acceptance"]  # "request_queue_acceptance_queue"
success = dynamodb_client.put_item(table_name, queue_item.dict())
```

**Table Details:**
- **Table Name:** `request_queue_acceptance_queue`
- **Schema:**
  - PK: Partition Key (String) - `{project_id}#{project_request_id}`
  - SK: Sort Key (String) - `request_acceptance#{timestamp}`
  - Other fields: status, priority, processing_strategy, payload, metadata, etc.

### 5. Estimated Completion Time Calculation
```python
estimated_completion = _calculate_estimated_completion(request)
```

**Calculation Factors:**
- **Base time:** 15 minutes
- **Keyword factor:** 2 minutes per keyword
- **Source factor:** 3 minutes per source
- **Strategy multipliers:**
  - `stream`: 0.7x (faster)
  - `table`: 1.0x (standard)
  - `batch`: 1.3x (slower but thorough)
- **Priority multipliers:**
  - `high`: 0.8x (higher resource allocation)
  - `medium`: 1.0x (standard)
  - `low`: 1.4x (lower priority)

### 6. Response
```python
return RequestResponse(
    status="accepted",
    request_id=request.project_request_id,
    estimated_completion=estimated_completion,
    tracking_url=f"{settings.api_prefix}/requests/{request.project_request_id}/status"
)
```

## Workflow After Route Execution

After the route creates the queue item in `request_acceptance` queue:

1. **RequestAcceptanceWorker** picks up the item (status: `pending`)
2. Worker validates the request in detail
3. Worker creates processing plan
4. Worker creates SERP queue items (one per source)
5. SERP workers process search queries
6. Perplexity workers process URLs from SERP results
7. Relevance check, Insight, and Implication workers process Perplexity responses in parallel
8. Final results are stored in DynamoDB and S3

## Error Handling

1. **Validation Errors:** HTTP 400 with detailed error messages
2. **DynamoDB Errors:** HTTP 500 with "Failed to queue request for processing"
3. **General Errors:** HTTP 500 with "Internal server error while processing request"

## Status Tracking

Users can track request status via:
- `GET /api/v1/requests/{request_id}/status` - Get processing status across all queues
- `GET /api/v1/requests/{request_id}/results` - Get final results when completed

## Example Request

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
      {
        "name": "FDA",
        "type": "regulatory",
        "url": "https://www.fda.gov"
      }
    ],
    "extraction_mode": "summary",
    "quality_threshold": 0.8
  }
}
```

## Example Response

```json
{
  "status": "accepted",
  "request_id": "req_456",
  "estimated_completion": "2024-01-15T10:30:00Z",
  "tracking_url": "/api/v1/requests/req_456/status"
}
```

## Related Configuration

- **Queue Table:** Defined in `app/config.py` as `QUEUE_TABLES["request_acceptance"]`
- **Queue Workflow:** Defined in `QUEUE_WORKFLOW` - `request_acceptance` → `serp`
- **Processing Limits:** Defined in `QUEUE_PROCESSING_LIMITS`
