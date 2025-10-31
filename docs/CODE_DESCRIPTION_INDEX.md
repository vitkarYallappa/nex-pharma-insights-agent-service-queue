# Market Intelligence Queue System - Architecture & Code Description Index

## Overview

This system is a **queue-based pharmaceutical market intelligence processing pipeline** that processes market intelligence requests through multiple stages using DynamoDB queues and AWS services. It transforms raw requests into actionable insights and implications through a series of specialized workers.

## System Architecture

### High-Level Flow

```
API Request → Request Acceptance → SERP → Perplexity → [Relevance Check, Insight, Implication] → Results
```

### Core Components

1. **API Layer** (`app/api/v1/routes.py`)
   - FastAPI endpoints for receiving requests
   - Request validation and queue initialization

2. **Queue Workers** (`app/queues/`)
   - Specialized workers for each processing stage
   - All inherit from `BaseWorker` for consistent behavior

3. **DynamoDB Tables** (Queue Storage)
   - Each queue has its own DynamoDB table
   - Items tracked by `PK` (partition key) and `SK` (sort key)

4. **S3 Storage** (`app/database/s3_client.py`)
   - Stores processed results (SERP data, Perplexity responses, insights, implications)
   - Organized by project_id and request_id

5. **External Services**
   - **SERP API:** Search engine results page queries
   - **Perplexity AI:** Content summarization and analysis
   - **AWS Bedrock (Claude):** Relevance checking, insight generation, implication extraction

## Queue Pipeline Architecture

### Queue Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    POST /market-intelligence-requests            │
│                    (creates request_acceptance item)              │
└────────────────────────────┬──────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────────┐
                    │ RequestAcceptance  │
                    │      Worker        │
                    │  (validates &      │
                    │   creates plan)    │
                    └──────────┬─────────┘
                               │
                    ┌──────────┴──────────┐
                    │  Creates N items    │
                    │  (1 per source)      │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │   SERP    │  │   SERP    │  │   SERP    │
        │  Worker   │  │  Worker   │  │  Worker   │
        │ (Source 1)│  │ (Source 2)│  │ (Source N)│
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
              │  ┌───────────┴────────────┐
              │  │  Creates M items       │
              │  │  (1 per URL, max 3)     │
              └──┴───────────┬────────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
                ▼            ▼            ▼
        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
        │ Perplexity  │ │ Perplexity  │ │ Perplexity  │
        │   Worker    │ │   Worker    │ │   Worker    │
        │  (URL 1)    │ │  (URL 2)    │ │  (URL M)    │
        └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
               │               │               │
               │  ┌────────────┴─────────────┐
               │  │  Creates 3 items per URL │
               │  │  (relevance, insight,     │
               │  │   implication)            │
               └──┴────────────┬─────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
    │  Relevance      │ │   Insight   │ │   Implication   │
    │  Check Worker    │ │   Worker    │ │    Worker       │
    │  (analyzes       │ │ (extracts   │ │  (generates     │
    │   relevance)     │ │  insights)  │ │  implications)  │
    └─────────────────┘ └─────────────┘ └─────────────────┘
```

## Queue System Details

### Queue Hierarchy

| Queue Name | Purpose | Input | Output | Next Queues |
|------------|---------|-------|--------|-------------|
| **request_acceptance** | Validates request & creates plan | API request | Validation results, processing plan | `serp` |
| **serp** | Search engine queries | Source + keywords | Search results (URLs) | `perplexity` |
| **perplexity** | Content summarization | URL + prompt | HTML summary | `relevance_check`, `insight`, `implication` |
| **relevance_check** | Relevance analysis | Perplexity response | Relevance score & analysis | None (final) |
| **insight** | Market insight extraction | Perplexity response | Market insights | None (final) |
| **implication** | Business implication extraction | Perplexity response | Strategic implications | None (final) |

### Queue Item Structure

All queue items follow this structure:

```json
{
  "PK": "{project_id}#{project_request_id}",
  "SK": "{queue_name}#{timestamp}",
  "status": "pending|processing|completed|failed|retry",
  "priority": "high|medium|low",
  "processing_strategy": "table|stream|batch",
  "payload": {
    // Queue-specific data
  },
  "metadata": {
    // Context information
  },
  "retry_count": 0,
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

### DynamoDB Table Structure

Each queue has its own DynamoDB table:

- **Table Naming:** `{queue_name}_queue` (e.g., `serp_queue`, `perplexity_queue`)
- **Schema:**
  - **PK (Partition Key):** `{project_id}#{project_request_id}` (String)
  - **SK (Sort Key):** `{queue_name}#{timestamp}` (String)
  - **Billing Mode:** `PAY_PER_REQUEST`
- **Key Pattern:**
  - Enables querying all items for a request: `PK = {project_id}#{request_id}`
  - Enables querying specific queue items by timestamp

## Processing Strategy

### BaseWorker Pattern

All workers inherit from `BaseWorker`, which provides:

1. **Polling Loop:** Continuously polls DynamoDB for pending items
2. **Status Management:** Updates item status (pending → processing → completed)
3. **Retry Logic:** Automatic retries up to max_retries (default: 3)
4. **Workflow Triggering:** Creates items in next queues on completion
5. **Error Handling:** Graceful error handling with logging

### Worker Lifecycle

```
1. Initialization → Worker created with queue name
2. Thread Start → Background polling thread started
3. Polling → Continuously polls for pending items
4. Processing → Processes items one by one
5. Status Updates → Updates DynamoDB status
6. Workflow → Creates items in next queues
7. Shutdown → Graceful shutdown on stop
```

### Item Processing Flow

```
pending → processing → completed (success path)
         ↓
       retry → processing → completed (retry success)
         ↓
       failed (max retries exceeded)
```

## Key Concepts

### 1. Request Flow Multiplicity

**Request Acceptance → SERP:**
- **1 request** → **N SERP items** (one per source)
- If request has 5 sources → 5 SERP queue items created

**SERP → Perplexity:**
- **1 SERP item** → **M Perplexity items** (one per URL, max 3)
- If SERP finds 25 URLs → 3 Perplexity items created (top 3 by relevance)

**Perplexity → Final Queues:**
- **1 Perplexity item** → **3 final items** (relevance, insight, implication)
- All three process the same Perplexity response in parallel

### 2. Parallel Processing

Three final queues process **in parallel**:
- **Relevance Check:** Determines if content is relevant
- **Insight:** Extracts market insights
- **Implication:** Generates business implications

All three:
- Receive the same Perplexity response
- Process independently
- Store results in separate tables
- Can be used together for comprehensive analysis

### 3. Content ID Tracking

After Perplexity processing:
- `content_id` is assigned (from DB operations)
- All subsequent workers (relevance, insight, implication) receive `content_id`
- Used for linking results across tables
- Enables content-based queries and aggregations

### 4. S3 Storage Organization

Results stored in S3 with this structure:

```
s3://bucket/
  ├── raw-content/
  │   └── {project_id}/
  │       └── {request_id}/
  │           ├── serp/
  │           │   └── {source_name}_{timestamp}.json
  │           └── content/
  │               └── {url_hash}_{timestamp}.json
  └── processed/
      └── {project_id}/
          └── {request_id}/
              ├── insights/
              │   └── {content_id}_{timestamp}.json
              ├── implications/
              │   └── {content_id}_{timestamp}.json
              └── relevance/
                  └── {content_id}_{timestamp}.json
```

## Detailed Documentation

### Entry Point & API
- **[Market Intelligence Route](CODE_DESCRIPTION_MARKET_INTELLIGENCE_ROUTE.md)**
  - POST `/market-intelligence-requests` endpoint
  - Request validation
  - Queue item creation
  - Response handling

### Core Infrastructure
- **[Base Worker](CODE_DESCRIPTION_BASE_WORKER.md)**
  - BaseWorker class architecture
  - Polling mechanism
  - Status management
  - Retry logic
  - Workflow triggering
  - Abstract methods

### Queue Workers

1. **[Request Acceptance Worker](CODE_DESCRIPTION_REQUEST_ACCEPTANCE_WORKER.md)**
   - Request validation
   - Processing plan creation
   - SERP queue item creation (one per source)

2. **[SERP Worker](CODE_DESCRIPTION_SERP_WORKER.md)**
   - Search query execution
   - SERP API integration
   - Result storage
   - Perplexity queue item creation (one per URL, limited)

3. **[Perplexity Worker](CODE_DESCRIPTION_PERPLEXITY_WORKER.md)**
   - Perplexity AI API calls
   - Content summarization
   - Content ID assignment
   - Parallel queue creation (relevance, insight, implication)

4. **[Relevance Check Worker](CODE_DESCRIPTION_RELEVANCE_CHECK_WORKER.md)**
   - Relevance analysis using Bedrock
   - Relevance scoring
   - Content filtering support

5. **[Insight Worker](CODE_DESCRIPTION_INSIGHT_WORKER.md)**
   - Market insight extraction using Bedrock
   - Trend identification
   - Pattern recognition

6. **[Implication Worker](CODE_DESCRIPTION_IMPLICATION_WORKER.md)**
   - Business implication extraction using Bedrock
   - Strategic recommendations
   - Risk/opportunity analysis

## Configuration

### Queue Tables

```python
QUEUE_TABLES = {
    "request_acceptance": "request_queue_acceptance_queue",
    "serp": "serp_queue",
    "perplexity": "perplexity_queue",
    "relevance_check": "relevance_check_queue",
    "insight": "insight_queue",
    "implication": "implication_queue"
}
```

### Queue Workflow

```python
QUEUE_WORKFLOW = {
    "request_acceptance": ["serp"],
    "serp": ["perplexity"],
    "perplexity": ["relevance_check", "insight", "implication"],
    "relevance_check": [],
    "insight": [],
    "implication": []
}
```

### Processing Limits

```python
QUEUE_PROCESSING_LIMITS = {
    "max_perplexity_urls_per_serp": 3,  # Max URLs per SERP result
    "max_serp_results": 50,              # Max search results
    "max_insight_items": 10,             # Max insight items per request
    "max_implication_items": 10,         # Max implication items per request
    "task_delay_seconds": 3              # Delay between processing items
}
```

## Data Flow Example

### Complete Request Processing

**Input Request:**
```json
{
  "project_id": "proj_123",
  "project_request_id": "req_456",
  "config": {
    "keywords": ["FDA approval", "clinical trial"],
    "sources": [
      {"name": "FDA", "type": "regulatory", "url": "https://fda.gov"},
      {"name": "NIH", "type": "research", "url": "https://nih.gov"}
    ]
  }
}
```

**Processing Steps:**

1. **Request Acceptance:**
   - 1 item created in `request_queue_acceptance_queue`
   - Validates request
   - Creates processing plan
   - **Output:** 2 items in `serp_queue` (one per source)

2. **SERP Processing:**
   - 2 SERP workers process independently
   - Each finds ~25 search results
   - Top 3 URLs selected per SERP item
   - **Output:** 6 items in `perplexity_queue` (2 sources × 3 URLs)

3. **Perplexity Processing:**
   - 6 Perplexity workers process independently
   - Each calls Perplexity API for URL summary
   - Content IDs assigned
   - **Output:** 18 items total:
     - 6 items in `relevance_check_queue`
     - 6 items in `insight_queue`
     - 6 items in `implication_queue`

4. **Final Processing:**
   - All 18 workers process in parallel
   - Relevance: 6 relevance analyses
   - Insights: 6 market insight extractions
   - Implications: 6 business implication extractions
   - **Output:** All items marked as `completed`
   - Results stored in S3 and DynamoDB

**Total Items Created:**
- 1 request_acceptance
- 2 serp
- 6 perplexity
- 6 relevance_check
- 6 insight
- 6 implication
- **Total: 27 queue items**

## Key Design Patterns

### 1. Template Method Pattern
- `BaseWorker` defines algorithm structure
- Subclasses implement specific processing steps

### 2. Factory Pattern
- `QueueItemFactory` creates queue items
- Handles different queue types uniformly

### 3. Strategy Pattern
- Processing strategies (table/stream/batch)
- Priority levels (high/medium/low)
- Configurable per request

### 4. Observer Pattern
- Workers observe queue tables for new items
- Event-driven processing

### 5. Chain of Responsibility
- Queue workflow defines processing chain
- Each worker completes and triggers next

## Error Handling & Resilience

### Retry Mechanism
- Default max retries: 3
- Exponential backoff (configurable)
- Status transitions: `failed` → `retry` → `processing`

### Error States
- **Failed:** Max retries exceeded
- **Retry:** Temporary failure, will retry
- **Processing:** Currently being processed
- **Completed:** Successfully processed

### Graceful Degradation
- Individual item failures don't crash workers
- Partial processing allowed
- Errors logged for debugging

## Monitoring & Metrics

### Queue Metrics
Each worker can provide:
- Pending count
- Processing count
- Completed count
- Failed count
- Success rate
- Processing time

### Status Tracking
- Request status across all queues
- Individual queue progress
- Error messages
- Completion timestamps

## API Endpoints

### Request Management
- `POST /market-intelligence-requests` - Submit request
- `GET /requests/{request_id}/status` - Get status
- `GET /requests/{request_id}/results` - Get results
- `GET /requests` - List requests
- `DELETE /requests/{request_id}` - Cancel request

### Configuration
- `GET /processing-limits` - Get limits
- `POST /processing-limits` - Update limits

## Storage Architecture

### DynamoDB (Queue Storage)
- Queue items
- Status tracking
- Metadata storage

### S3 (Result Storage)
- Raw SERP data
- Perplexity responses
- Processed insights
- Processed implications
- Relevance analyses

### Additional Tables (via DB Operations)
- `content_repository` - Content metadata
- `content_relevance` - Relevance scores
- `content_insight` - Insight data
- `content_implication` - Implication data

## Scalability Considerations

### Horizontal Scaling
- Workers can run on multiple instances
- DynamoDB handles concurrent access
- S3 provides distributed storage

### Processing Limits
- Configurable limits prevent overload
- URL limits control Perplexity API usage
- Batch processing for efficiency

### Performance Optimization
- Parallel processing where possible
- Async operations for API calls
- Efficient DynamoDB queries
- S3 storage for large payloads

## Security & Compliance

### Data Isolation
- Data organized by project_id
- Request-level isolation
- Secure S3 bucket access

### API Key Management
- Environment-based configuration
- Secure storage of API keys
- Access control per queue

## Future Enhancements

### Potential Additions
- Aggregation workers for cross-URL analysis
- Report generation workers
- Alert workers for critical findings
- Dashboard integration
- Real-time status updates via WebSockets

### Optimization Opportunities
- Caching layer for frequent queries
- Batch processing optimizations
- Intelligent URL selection improvements
- Content deduplication

## Summary

This system provides a **robust, scalable, queue-based pipeline** for processing pharmaceutical market intelligence requests. It transforms raw requests through multiple stages using specialized workers, external APIs, and AI services to produce actionable insights and implications. The architecture ensures reliability through retry mechanisms, parallel processing for efficiency, and comprehensive error handling.

**Key Strengths:**
- ✅ Modular worker architecture
- ✅ Scalable queue system
- ✅ Comprehensive error handling
- ✅ Parallel processing capabilities
- ✅ Flexible configuration
- ✅ Full traceability and monitoring

For detailed information about each component, refer to the specific documentation files linked above.
