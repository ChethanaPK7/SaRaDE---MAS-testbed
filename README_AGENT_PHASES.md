# SaRaDE — completed agent-environment implementation

This branch upgrades the original three-agent prototype into a coordinated research-development agent environment.

### Phase 1 — specialist agents
Profile parsing, opportunity matching, learning map, SOP generation, and verification.

### Phase 2 — coordination environment
A domain-specific CTDE environment defines state, local observations, actions, reward, communication cost and data-exposure pressure.

### Phase 3 — QMIX
A PyTorch implementation of QMIX learns joint coordination from the synthetic environment. A checkpoint is included.

### Phase 4 — application orchestration
The Django API exposes a coordination planner and one-shot orchestrated workflow. The learned coordinator chooses which specialists should run.

### Phase 5 — UI
The React agent page exposes the individual specialists, verification, coordinator planning, and coordinated workflow.

### Phase 6 — consent/data boundary
No agent code directly reads Anumati lockers. Only request-scoped data explicitly supplied by the caller is sent to an agent. The API returns this boundary in workflow responses.

### Phase 7 — reproducibility
Training is deterministic given the seed and uses a synthetic environment independent of student records. The environment and training script are included under `backend/agents/marl/`.

## Important interpretation

QMIX is an established cooperative MARL algorithm from ICML 2018. Microsoft AutoGen is a multi-agent application framework and can be used as an orchestration reference, but it is not the learning algorithm in this implementation. The current code deliberately keeps those layers separate.
