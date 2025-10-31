# Base Worker - Code Description

## Overview
The `BaseWorker` class is an abstract base class that provides the core functionality for all queue workers in the system. It implements the common polling, processing, and error handling logic that all workers share.

## Location
**File:** `app/queues/base_worker.py`  
**Class:** `BaseWorker(ABC)`

## Architecture Pattern

The BaseWorker implements the **Template Method Pattern**:
- Defines the skeleton of the processing algorithm
- Delegates specific processing steps to subclasses via abstract methods
- Ensures consistent behavior across all workers

## Core Components

### 1. Initialization

```python
def __init__(self, queue_name: str):
    self.queue_name = queue_name
    self.table_name = QUEUE_TABLES.get(queue_name)
    self.is_running = False
    self.thread = None
    self.poll_interval = settings.queue_poll_interval  # Default: 5 seconds
    self.batch_size = settings.queue_batch_size       # Default: 10 items
    self.max_retries = settings.max_retries           # Default: 3
    self.retry_delay = settings.retry_delay            # Default: 60 seconds
```

**Key Attributes:**
- `queue_name`: Identifier for the queue (e.g., "serp", "perplexity")
- `table_name`: DynamoDB table name for this queue
- `is_running`: Flag to control worker lifecycle
- `thread`: Thread handle for background processing
- `poll_interval`: Time between polling for new items
- `batch_size`: Maximum items to process per poll cycle

### 2. Polling Loop

```python
def start_polling(self):
    """Start the worker polling loop"""
    self.is_running = True
    while self.is_running:
        pending_items = self._get_pending_items()
        if pending_items:
            for item in pending_items:
                # Add configurable delay
                task_delay = QUEUE_PROCESSING_LIMITS.get('task_delay_seconds', 3)
                if task_delay > 0:
                    time.sleep(task_delay)
                
                self._process_item(item)
        else:
            # Log heartbeat periodically
            if (now - self.last_heartbeat).total_seconds() >= self.heartbeat_interval:
                logger.info(f"💓 {self.queue_name.upper()} QUEUE HEARTBEAT")
        
        time.sleep(self.poll_interval)
```

**How it works:**
1. Continuously polls DynamoDB for items with `status = 'pending'`
2. Processes items one by one with configurable delay
3. Logs heartbeat when no items are found
4. Sleeps for `poll_interval` seconds between polls

### 3. Item Processing Flow

```python
def _process_item(self, item: Dict[str, Any]):
    """Process a single queue item"""
    # 1. Update status to 'processing'
    self._update_item_status(pk, sk, QueueStatus.PROCESSING)
    
    # 2. Call subclass-specific processing (abstract method)
    success = self.process_item(item)
    
    # 3. Handle success/failure
    if success:
        self._update_item_status(pk, sk, QueueStatus.COMPLETED)
        self._trigger_next_queues(item)  # Create items in next queues
    else:
        self._handle_processing_failure(item)
```

**Status Transitions:**
- `pending` → `processing` → `completed` (success path)
- `pending` → `processing` → `retry` → `completed` (retry path)
- `pending` → `processing` → `failed` (failure path)

### 4. Getting Pending Items

```python
def _get_pending_items(self) -> List[Dict[str, Any]]:
    """Get pending items from the queue"""
    items = dynamodb_client.scan_items(
        table_name=self.table_name,
        filter_expression='#status = :status',
        expression_attribute_values={':status': QueueStatus.PENDING.value},
        expression_attribute_names={'#status': 'status'},
        limit=self.batch_size
    )
    return items
```

**Query Details:**
- Scans DynamoDB table for items with `status = 'pending'`
- Limits results to `batch_size` items
- Returns list of item dictionaries

### 5. Status Updates

```python
def _update_item_status(self, pk: str, sk: str, status: QueueStatus, 
                       error_message: Optional[str] = None):
    """Update the status of a queue item"""
    dynamodb_client.update_item_status(
        table_name=self.table_name,
        pk=pk,
        sk=sk,
        new_status=status.value,
        error_message=error_message
    )
```

**What it updates:**
- `status`: New status value
- `updated_at`: Current timestamp
- `error_message`: Optional error message

### 6. Retry Logic

```python
def _handle_processing_failure(self, item: Dict[str, Any]):
    """Handle processing failure with retry logic"""
    retry_count = item.get('retry_count', 0)
    
    if retry_count < self.max_retries:
        # Increment retry count and set to retry status
        new_retry_count = retry_count + 1
        dynamodb_client.update_item(...)  # Update with new retry_count
        logger.warning(f"Item {pk} failed, scheduled for retry ({new_retry_count}/{self.max_retries})")
    else:
        # Max retries reached, mark as failed
        self._update_item_status(pk, sk, QueueStatus.FAILED, "Max retries exceeded")
```

**Retry Strategy:**
- Default max retries: 3
- Each failure increments `retry_count`
- Item status changes to `retry` for automatic reprocessing
- After max retries, status becomes `failed`

### 7. Workflow Triggering

```python
def _trigger_next_queues(self, completed_item: Dict[str, Any]):
    """Trigger next queues in the workflow"""
    next_queues = QUEUE_WORKFLOW.get(self.queue_name, [])
    
    for next_queue in next_queues:
        self._create_next_queue_item(next_queue, project_id, request_id, completed_item)
```

**Workflow Configuration:**
Defined in `app/config.py`:
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

**How it works:**
1. Gets list of next queues from `QUEUE_WORKFLOW`
2. For each next queue, creates a new queue item
3. Extracts `project_id` and `request_id` from completed item's PK
4. Calls `prepare_next_queue_payload()` to get payload for next queue

### 8. Creating Next Queue Items

```python
def _create_next_queue_item(self, next_queue: str, project_id: str, 
                           request_id: str, completed_item: Dict[str, Any]):
    """Create item in next queue"""
    # Get payload from subclass (abstract method)
    next_payload = self.prepare_next_queue_payload(next_queue, completed_item)
    
    # Create queue item using factory
    queue_item = QueueItemFactory.create_queue_item(
        queue_name=next_queue,
        project_id=project_id,
        project_request_id=request_id,
        priority=completed_item.get('priority', 'medium'),
        processing_strategy=completed_item.get('processing_strategy', 'table'),
        payload=next_payload,
        metadata=completed_item.get('metadata', {})
    )
    
    # Store in DynamoDB
    dynamodb_client.put_item(next_table_name, queue_item.dict())
```

**What happens:**
1. Calls abstract method `prepare_next_queue_payload()` to get payload
2. Creates new queue item using `QueueItemFactory`
3. Preserves priority and processing_strategy from parent item
4. Stores item in DynamoDB table for next queue

## Abstract Methods (Must be implemented by subclasses)

### 1. `process_item(item) -> bool`
```python
@abstractmethod
def process_item(self, item: Dict[str, Any]) -> bool:
    """
    Process a single queue item.
    
    Args:
        item: The queue item to process
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    pass
```

**Purpose:** Performs the actual processing work for the queue item.

**Example (from SerpWorker):**
```python
def process_item(self, item: Dict[str, Any]) -> bool:
    payload = item.get('payload', {})
    keywords = payload.get('keywords', [])
    source = payload.get('source', {})
    
    # Get search results
    search_results = self._get_real_search_results(keywords, source)
    
    # Store results in S3
    s3_key = s3_client.store_serp_data(project_id, request_id, {...})
    
    # Update payload with results
    updated_payload = payload.copy()
    updated_payload.update({'search_results': search_results, ...})
    
    # Update DynamoDB
    dynamodb_client.update_item(...)
    
    return True
```

### 2. `prepare_next_queue_payload(next_queue, completed_item) -> Dict[str, Any]`
```python
@abstractmethod
def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare payload for the next queue based on completed item.
    
    Args:
        next_queue: Name of the next queue
        completed_item: The completed queue item
        
    Returns:
        Dict[str, Any]: Payload for the next queue
    """
    pass
```

**Purpose:** Transforms the completed item's data into the format expected by the next queue.

**Example (from SerpWorker):**
```python
def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
    if next_queue == "perplexity":
        payload = completed_item.get('payload', {})
        search_results = payload.get('search_results', [])
        
        return {
            'urls': [result.get('url') for result in search_results],
            'source_info': payload.get('source', {}),
            ...
        }
    return {}
```

## Thread Management

### Starting Worker Thread
```python
def start_worker_thread(self):
    """Start worker in a separate thread"""
    self.thread = threading.Thread(target=self.start_polling, daemon=True)
    self.thread.start()
    logger.info(f"🧵 WORKER THREAD STARTED for {self.queue_name.upper()}")
```

**Characteristics:**
- Runs as daemon thread (doesn't block application shutdown)
- Each worker runs in its own thread
- Multiple workers can run concurrently

### Stopping Worker
```python
def stop_polling(self):
    """Stop the worker polling loop"""
    self.is_running = False
    if self.thread and self.thread.is_alive():
        self.thread.join(timeout=10)
```

## Queue Metrics

```python
def get_queue_metrics(self) -> Dict[str, Any]:
    """Get metrics for this queue"""
    pending = len(dynamodb_client.get_queue_items_by_status(...))
    processing = len(dynamodb_client.get_queue_items_by_status(...))
    completed = len(dynamodb_client.get_queue_items_by_status(...))
    failed = len(dynamodb_client.get_queue_items_by_status(...))
    
    return {
        'queue_name': self.queue_name,
        'pending': pending,
        'processing': processing,
        'completed': completed,
        'failed': failed,
        'total': total,
        'success_rate': (completed / total * 100) if total > 0 else 0,
        'is_running': self.is_running
    }
```

## Worker Lifecycle

1. **Initialization:** Worker is created with queue name
2. **Thread Start:** `start_worker_thread()` starts background polling
3. **Polling Loop:** Continuously polls for pending items
4. **Processing:** Processes items one by one
5. **Status Updates:** Updates item status in DynamoDB
6. **Workflow Triggering:** Creates items in next queues on completion
7. **Shutdown:** `stop_polling()` gracefully stops the worker

## Error Handling

- **Processing Errors:** Caught and logged, item marked as failed
- **DynamoDB Errors:** Caught and logged, processing continues
- **Retry Logic:** Automatic retries up to max_retries
- **Graceful Degradation:** Errors don't crash the worker thread

## Configuration

All worker behavior is configured via:
- `app/config.py` - Queue tables, workflow, processing limits
- `settings` object - Poll intervals, batch sizes, retry limits

## Usage Example

```python
# In app/main.py or similar
from app.queues.serp.worker import SerpWorker

# Create and start worker
serp_worker = SerpWorker()
serp_worker.start_worker_thread()

# Worker runs in background, processing items automatically
# To stop:
serp_worker.stop_polling()
```
