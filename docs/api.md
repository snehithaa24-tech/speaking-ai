# SAHAYAK AI API Reference

## Base URL

- Development: `http://localhost:8000`
- Production: `https://api.sahayak.ai`

## Authentication

Most endpoints require no authentication for core functionality. Optional Google OAuth for user accounts.

## Sessions

### Create Session

Creates a new Gemini Live session and returns a temporary token for WebSocket connection.

**Endpoint**: `POST /api/v1/sessions`

**Request Body**:
```json
{
  "config": {
    "language": "en-IN",
    "voice_name": "Kore",
    "system_instruction": "You are Sahayak AI...",
    "temperature": 0.7,
    "max_output_tokens": 2048
  }
}
```

**Response** (201):
```json
{
  "session_id": "uuid",
  "token": "base64_encoded_token",
  "status": "active",
  "language": "en-IN"
}
```

**Token Payload** (decoded):
```json
{
  "session_id": "uuid",
  "config": { ... },
  "expires_at": "2024-01-01T12:00:00Z",
  "nonce": "random_string"
}
```

### Get Session

**Endpoint**: `GET /api/v1/sessions/{session_id}`

**Response** (200):
```json
{
  "id": "uuid",
  "user_id": "uuid|null",
  "started_at": "2024-01-01T12:00:00Z",
  "ended_at": "2024-01-01T12:30:00Z|null",
  "status": "completed",
  "language": "en-IN",
  "message_count": 15
}
```

### End Session

**Endpoint**: `DELETE /api/v1/sessions/{session_id}`

**Response**: 204 No Content

### Submit Feedback

**Endpoint**: `POST /api/v1/feedback`

**Request Body**:
```json
{
  "sessionId": "uuid",
  "rating": 5,
  "comment": "Very clear Hindi voice guidance."
}
```

**Response** (201):
```json
{
  "id": "uuid",
  "sessionId": "uuid",
  "rating": 5,
  "comment": "Very clear Hindi voice guidance.",
  "createdAt": "2024-01-01T12:05:00Z"
}
```

### Get Session Messages

**Endpoint**: `GET /api/v1/sessions/{session_id}/messages`

**Response** (200):
```json
[
  {
    "id": "uuid",
    "speaker": "user",
    "transcript": "नमस्ते",
    "language": "hi-IN",
    "timestamp": "2024-01-01T12:01:00Z"
  }
]
```

## Knowledge

### Search Knowledge

Search the knowledge base for relevant documents.

**Endpoint**: `POST /api/v1/knowledge/search`

**Request Body**:
```json
{
  "query": "PM-KISAN scheme eligibility",
  "category": "government_schemes",
  "language": "en-IN",
  "limit": 10
}
```

**Response** (200):
```json
{
  "documents": [
    {
      "id": "uuid",
      "title": "PM-KISAN Scheme Overview",
      "category": "government_schemes",
      "source_url": "https://pmkisan.gov.in/",
      "content": "PM-KISAN provides income support...",
      "language": "en-IN",
      "published_at": "2024-01-01T00:00:00Z",
      "verified_at": "2024-01-15T00:00:00Z",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "query": "PM-KISAN scheme eligibility",
  "language": "en-IN",
  "total_results": 1
}
```

### Get Categories

**Endpoint**: `GET /api/v1/knowledge/categories`

**Response** (200):
```json
["agriculture", "government_schemes", "transport", "hospital_assistance", "general"]
```

### Create Document (Admin)

**Endpoint**: `POST /api/v1/knowledge`

**Request Body**:
```json
{
  "title": "New Scheme",
  "category": "government_schemes",
  "source_url": "https://example.com",
  "content": "Scheme details...",
  "language": "en-IN",
  "published_at": "2024-01-01T00:00:00Z",
  "verified_at": "2024-01-01T00:00:00Z"
}
```

### Get Document

**Endpoint**: `GET /api/v1/knowledge/{doc_id}`

### Update Document (Admin)

**Endpoint**: `PUT /api/v1/knowledge/{doc_id}`

### Delete Document (Admin)

**Endpoint**: `DELETE /api/v1/knowledge/{doc_id}`

## Authentication

### Google OAuth

**Endpoint**: `POST /api/v1/auth/google`

**Request Body**:
```json
{
  "code": "oauth_authorization_code",
  "redirect_uri": "http://localhost:5173/auth/callback"
}
```

**Response** (200):
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Get Current User

**Endpoint**: `GET /api/v1/auth/me`

**Headers**: `Authorization: Bearer <jwt_token>`

**Response** (200):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "picture": "https://...",
  "preferred_language": "en-IN",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## WebSocket

### Connection

```
ws://localhost:8000/ws/live/{session_id}?token={session_token}
```

### Message Types

#### Client → Server

**Setup** (sent immediately after connection):
```json
{
  "type": "setup",
  "payload": {
    "language": "en-IN",
    "voice_name": "Kore",
    "system_instruction": "You are Sahayak AI...",
    "sample_rate": 16000
  }
}
```

**Audio** (streamed continuously):
```json
{
  "type": "audio",
  "payload": {
    "data": "base64_encoded_pcm16",
    "mime_type": "audio/pcm;rate=16000"
  }
}
```

**Function Response**:
```json
{
  "type": "function_response",
  "payload": {
    "functionCallId": "call_123",
    "result": { "documents": [...] }
  }
}
```

**Interrupt**:
```json
{
  "type": "interrupt"
}
```

#### Server → Client

**Audio Response**:
```json
{
  "type": "audio",
  "payload": {
    "data": "base64_encoded_pcm16_24khz"
  }
}
```

**Text/Transcript**:
```json
{
  "type": "text",
  "payload": {
    "text": "Hello, how can I help?",
    "is_final": true,
    "speaker": "assistant"
  }
}
```

**Function Call**:
```json
{
  "type": "function_call",
  "payload": {
    "id": "call_123",
    "name": "search_knowledge",
    "args": { "query": "wheat cultivation", "language": "en-IN" }
  }
}
```

**Error**:
```json
{
  "type": "error",
  "payload": "Connection timeout"
}
```

**Close**:
```json
{
  "type": "close"
}
```

## Function Calling

The following functions are available to the Gemini model:

### search_knowledge
```json
{
  "name": "search_knowledge",
  "description": "Search the knowledge base for relevant information",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "Search query" },
      "category": { "type": "string", "enum": ["agriculture", "government_schemes", "transport", "hospital_assistance", "general"] },
      "language": { "type": "string", "enum": ["en-IN", "hi-IN"] }
    },
    "required": ["query"]
  }
}
```

### get_scheme_details
```json
{
  "name": "get_scheme_details",
  "description": "Get detailed information about a specific government scheme",
  "parameters": {
    "type": "object",
    "properties": {
      "schemeId": { "type": "string" }
    },
    "required": ["schemeId"]
  }
}
```

### find_nearby_hospital
```json
{
  "name": "find_nearby_hospital",
  "description": "Find hospitals near a location",
  "parameters": {
    "type": "object",
    "properties": {
      "location": { "type": "string", "description": "City or pincode" },
      "specialty": { "type": "string" }
    }
  }
}
```

### get_transport_information
```json
{
  "name": "get_transport_information",
  "description": "Get transport routes and schedules",
  "parameters": {
    "type": "object",
    "properties": {
      "from": { "type": "string" },
      "to": { "type": "string" },
      "mode": { "type": "string", "enum": ["bus", "train", "metro"] }
    }
  }
}
```

### repeat_last_answer
```json
{
  "name": "repeat_last_answer",
  "description": "Repeat the last assistant response",
  "parameters": { "type": "object", "properties": {} }
}
```

## Error Responses

All endpoints may return errors in this format:

```json
{
  "error": "Error type",
  "detail": "Human-readable description",
  "code": "ERROR_CODE"
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |
| 501 | Not Implemented |

## Rate Limiting

- Session creation: 10/minute per IP
- Knowledge search: 30/minute per IP
- WebSocket connections: 5 concurrent per session

## Versioning

API version is in the URL path: `/api/v1/`

Breaking changes will result in a new version (`/api/v2/`).