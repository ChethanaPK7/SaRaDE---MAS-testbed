# SaRaDE AI Agent Layer

The initial environment contains three agents:

1. **AI Profile Parser** — extracts a structured research profile from user-supplied CV/profile text.
2. **Opportunity Matcher** — compares that profile with open SRIP postings and returns compatibility reasons/gaps.
3. **Student SOP Writer** — drafts a research-specific SOP for a selected posting.

## Provider configuration

The agents use an OpenAI-compatible `/chat/completions` endpoint. Configure in `backend/.env`:

```env
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
```

No Anumati locker is queried directly by the agents. The first implementation deliberately processes only data explicitly supplied to an agent. This is the consent boundary to preserve as the environment expands.

## API

- `GET /api/agents/`
- `POST /api/agents/profile-parser/` — `{ "text": "..." }`
- `POST /api/agents/opportunity-matcher/` — `{ "profile": {...}, "limit": 8 }`
- `POST /api/agents/sop-writer/` — `{ "profile": {...}, "posting_id": 1, "constraints": "..." }`
