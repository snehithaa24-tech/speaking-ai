# SAHAYAK AI Testing Guide

## Testing Strategy

SAHAYAK AI follows a comprehensive testing approach covering unit tests, integration tests, end-to-end tests, and real-user evaluation.

## Test Pyramid

```
                    ┌─────────────┐
                    │ E2E Tests   │  ← Few, critical paths
                    ├─────────────┤
                    │ Integration │  ← API, WebSocket, DB
                    ├─────────────┤
               ┌────│ Unit Tests  │────┐  ← Many, fast, isolated
               │    └─────────────┘    │
               ▼                       ▼
         Frontend                  Backend
```

## Frontend Testing

### Setup

```bash
cd frontend
npm install
npm run test        # Run tests
npm run test:ui     # Visual test runner
npm run typecheck   # TypeScript validation
npm run lint        # ESLint
```

### Unit Tests (Vitest + React Testing Library)

**Component Tests** (`src/components/**/*.test.tsx`):
```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { LanguageProvider } from '@contexts/LanguageContext';
import { MicrophoneButton } from '@components/voice/MicrophoneButton';

test('MicrophoneButton shows listening state', () => {
  render(
    <LanguageProvider>
      <MicrophoneButton status="listening" isMuted={false} onClick={jest.fn()} />
    </LanguageProvider>
  );

  expect(screen.getByLabelText('Listening...')).toBeInTheDocument();
  expect(screen.getByRole('button')).toHaveClass('mic-button-listening');
});
```

**Hook Tests** (`src/hooks/**/*.test.ts`):
```tsx
import { renderHook, act } from '@testing-library/react';
import { useVoiceSession } from '@hooks/useVoiceSession';

test('useVoiceSession starts session', async () => {
  const { result } = renderHook(() => useVoiceSession());

  await act(async () => {
    await result.current.startSession();
  });

  expect(result.current.status).toBe('connecting');
});
```

**Utility Tests** (`src/utils/**/*.test.ts`):
```tsx
import { cn, formatDuration, debounce } from '@utils/cn';

test('cn merges classes correctly', () => {
  expect(cn('base', 'override', { conditional: true })).toBe('base override conditional');
});
```

### Accessibility Tests

```tsx
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

test('Home page has no accessibility violations', async () => {
  const { container } = render(<Home />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Test Coverage Targets

| Category | Target |
|----------|--------|
| Components | 80% |
| Hooks | 90% |
| Utilities | 95% |
| Overall | 85% |

## Backend Testing

### Setup

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
pytest                # Run all tests
pytest --cov=app      # With coverage
pytest -x             # Stop on first failure
```

### Unit Tests (`tests/unit/`)

**Service Tests**:
```python
import pytest
from app.services.knowledge import KnowledgeService
from app.schemas.schemas import KnowledgeDocumentCreate, KnowledgeCategory, LanguageCode

@pytest.fixture
async def knowledge_service(db_session):
    return KnowledgeService(db_session)

async def test_create_document(knowledge_service):
    doc = KnowledgeDocumentCreate(
        title="Test",
        category=KnowledgeCategory.AGRICULTURE,
        content="Content",
        language=LanguageCode.EN_IN,
    )
    created = await knowledge_service.create_document(doc)
    assert created.id is not None
    assert created.title == "Test"
```

**API Tests** (`tests/api/`):
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

async def test_create_session(client):
    response = await client.post("/api/v1/sessions", json={
        "config": {
            "language": "en-IN",
            "voice_name": "Kore",
            "system_instruction": "Test",
            "temperature": 0.7,
            "max_output_tokens": 2048
        }
    })
    assert response.status_code == 201
    assert "session_id" in response.json()
```

### Integration Tests (`tests/integration/`)

**Database Tests**:
```python
async def test_session_lifecycle(db_session):
    # Create session
    session = Session(id="test-id", status=SessionStatus.ACTIVE)
    db_session.add(session)
    await db_session.commit()

    # Retrieve
    result = await db_session.execute(select(Session).where(Session.id == "test-id"))
    assert result.scalar_one().status == SessionStatus.ACTIVE

    # Update
    session.status = SessionStatus.COMPLETED
    await db_session.commit()
```

**Gemini Live Mock Tests**:
```python
from unittest.mock import AsyncMock, patch

@patch('app.services.gemini_live.genai.Client')
async def test_gemini_session_creation(mock_client, db_session):
    mock_session = AsyncMock()
    mock_client.return_value.aio.live.connect.return_value = mock_session

    service = GeminiLiveService()
    session = await service.create_live_session(config)

    assert session == mock_session
```

### Test Configuration (`pytest.ini`)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
filterwarnings = ignore::DeprecationWarning
```

## WebSocket Testing

```python
import pytest
from fastapi.testclient import TestClient

def test_websocket_connection(client):
    with client.websocket_connect("/ws/live/test-session?token=valid_token") as ws:
        # Send setup
        ws.send_json({
            "type": "setup",
            "payload": {"language": "en-IN", "voice_name": "Kore"}
        })

        # Receive confirmation
        data = ws.receive_json()
        assert data["type"] == "connected"
```

## End-to-End Testing (Playwright)

### Setup

```bash
cd frontend
npm install -D @playwright/test
npx playwright install
```

### E2E Tests (`e2e/`)

```typescript
import { test, expect } from '@playwright/test';

test('complete voice conversation flow', async ({ page }) => {
  await page.goto('/');

  // Select language
  await page.click('button:has-text("English (India)")');

  // Navigate to conversation
  await page.click('a[href="/conversation"]');

  // Start conversation
  await page.click('button[aria-label="Start conversation"]');

  // Wait for listening state
  await expect(page.locator('text=Listening...')).toBeVisible();

  // Simulate speech (would need audio injection in real test)
  // ...

  // Verify transcript appears
  await expect(page.locator('[role="log"]')).toContainText('You said');
});
```

## Real-User Evaluation

### Protocol Overview

See `docs/user-testing-protocol.md` for detailed protocol.

### Metrics Collection

```python
# Automated metrics during testing
metrics = {
    "wer": calculate_wer(reference, hypothesis),
    "latency": {
        "connection": connection_time,
        "first_token": first_token_time,
        "full_response": full_response_time
    },
    "task_completion": task_success_rate,
    "recovery_rate": recovery_success_rate
}
```

### Word Error Rate Calculation

```python
def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate using Levenshtein distance"""
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    # Dynamic programming for edit distance
    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i-1] == hyp_words[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                d[i][j] = min(
                    d[i-1][j] + 1,    # deletion
                    d[i][j-1] + 1,    # insertion
                    d[i-1][j-1] + 1   # substitution
                )

    return d[len(ref_words)][len(hyp_words)] / len(ref_words)
```

## Continuous Integration

### GitHub Actions (`.github/workflows/test.yml`)

```yaml
name: Test

on: [push, pull_request]

jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm ci
      - run: cd frontend && npm run typecheck
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run test -- --run

  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
      - run: cd backend && pytest --cov=app --cov-fail-under=80
```

## Performance Testing

### Load Testing (k6)

```javascript
// load-test.js
import http from 'k6/http';
import ws from 'k6/ws';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
};

export default function() {
  // HTTP API test
  const res = http.post('http://localhost:8000/api/v1/sessions', JSON.stringify({
    config: { language: 'en-IN', voice_name: 'Kore', system_instruction: 'Test', temperature: 0.7, max_output_tokens: 2048 }
  }), { headers: { 'Content-Type': 'application/json' } });
  check(res, { 'session created': (r) => r.status === 201 });

  sleep(1);
}
```

## Test Data Management

### Fixtures

```python
# tests/fixtures/sample_documents.py
SAMPLE_DOCUMENTS = [
    {
        "title": "Test Scheme",
        "category": "government_schemes",
        "content": "Test content",
        "language": "en-IN"
    }
]
```

### Database Seeding for Tests

```python
@pytest.fixture(autouse=True)
async def seed_test_data(db_session):
    # Clean slate
    await db_session.execute(delete(KnowledgeDocument))
    await db_session.commit()

    # Seed
    for doc in SAMPLE_DOCUMENTS:
        db_session.add(KnowledgeDocument(**doc))
    await db_session.commit()
```

## Debugging Tests

### Frontend
```bash
# Debug specific test
npm run test -- --test-name-pattern="MicrophoneButton"

# With browser debug
npm run test:ui
```

### Backend
```bash
# Debug with pdb
pytest tests/unit/test_knowledge.py::test_create_document -xvs --pdb

# Verbose output
pytest -xvs
```

## Test Reporting

### Coverage Reports
```bash
# Frontend
npm run test -- --coverage

# Backend
pytest --cov=app --cov-report=html
```

### JUnit XML for CI
```bash
pytest --junitxml=report.xml
```

## Accessibility Testing Checklist

- [ ] All interactive elements keyboard accessible
- [ ] Focus indicators visible
- [ ] ARIA labels on all controls
- [ ] Live regions for dynamic content
- [ ] Color contrast ratios (4.5:1 normal, 3:1 large)
- [ ] Text scaling up to 200%
- [ ] Reduced motion respected
- [ ] Screen reader tested (NVDA/VoiceOver)