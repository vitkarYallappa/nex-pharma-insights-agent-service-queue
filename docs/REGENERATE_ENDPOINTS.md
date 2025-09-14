# Regenerate Endpoints Documentation

## Overview
Simple endpoints for processing text input through AWS Bedrock to generate insights and implications.

## Endpoints

### POST /regenerate/insights
Process text input to generate insights using Bedrock.

**Request:**
```json
{
  "content_id": "string",
  "text_input": "string", 
  "metadata": {}
}
```

**Response:**
```json
{
  "success": true,
  "content_id": "string",
  "regenerated_content": "string"
}
```

### POST /regenerate/implications  
Process text input to generate implications using Bedrock.

**Request:**
```json
{
  "content_id": "string",
  "text_input": "string",
  "metadata": {}
}
```

**Response:**
```json
{
  "success": true,
  "content_id": "string", 
  "regenerated_content": "string"
}
```

## How It Works

1. **User sends** large text input with content ID
2. **Service calls** AWS Bedrock directly with the text
3. **Bedrock processes** the text and returns results
4. **User receives** the processed content immediately

## Features

- ✅ Direct Bedrock processing
- ✅ No database storage
- ✅ Simple request/response
- ✅ Mock mode for testing
- ✅ Minimal complexity

## Example Usage

```bash
curl -X POST "http://localhost:8000/regenerate/insights" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "test123",
    "text_input": "Analyze this pharmaceutical market data...",
    "metadata": {}
  }'
```

## Configuration

Set `BEDROCK_MOCK_MODE=true` in environment for testing with mock responses. 