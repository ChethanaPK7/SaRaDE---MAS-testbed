# SaRaDE Agent Environment

SaRaDE now contains a multi-agent research-development environment rather than a set of unrelated AI buttons.

## Agent set

- **Profile Parser** — converts explicitly supplied CV/profile text into structured facts.
- **Opportunity Matcher** — estimates technical compatibility with open opportunities.
- **Learning Map** — identifies skill gaps and proposes a staged research-development path.
- **SOP Writer** — drafts opportunity-specific research statements without inventing achievements.
- **Verification Agent** — audits outputs for unsupported claims and unnecessary data exposure.
- **QMIX Coordinator** — chooses which specialist agents should contribute.

## Coordination algorithm

The research coordinator implements **QMIX** under centralized training and decentralized execution (CTDE). Each specialist has a local observation and local action-value function. A monotonic mixing network constructs a joint value:

`Q_tot(s, a_1, ..., a_n)`

The monotonic constraint lets decentralized agents select actions consistently with the learned joint policy.

QMIX is used here as the research algorithm, while the LLM agents remain application-level task specialists. This separation avoids claiming that the LLM framework itself is the learning contribution.

## Actions

Each specialist chooses one of:

- `skip`
- `run`
- `verify`

The current training environment is a reproducible synthetic coordination environment. It is intentionally separated from student data so that experiments can be repeated without training on personal information.

## Reward

The training environment combines task quality with coordination cost:

`R = quality - communication_cost - redundancy - exposure_cost`

The production API does not expose this synthetic reward as a user score. It is an internal research objective for studying orchestration.

## Data boundary

The coordinator does not read Anumati lockers, credentials, or hidden student records. A caller explicitly supplies the profile and any other context. This keeps consent/authorization outside the learned policy and preserves AnumatiDPI as a separate data-access boundary.

## API

- `GET /api/agents/`
- `POST /api/agents/profile-parser/`
- `POST /api/agents/opportunity-matcher/`
- `POST /api/agents/learning-map/`
- `POST /api/agents/sop-writer/`
- `POST /api/agents/verify/`
- `POST /api/agents/coordination-plan/`
- `POST /api/agents/orchestrate/`

All endpoints require the existing JWT authentication.

## Re-training

From `backend/`:

```bash
python -m agents.marl.train --episodes 1500
```

The resulting `agents/marl/qmix_sarade.pt` is the default coordinator checkpoint.

## Research baselines

For an experimental paper, compare:

1. single-agent LLM baseline;
2. fixed sequential pipeline;
3. independent specialist agents;
4. rule-based coordinator;
5. QMIX coordinator;
6. optionally QPLEX as a stronger value-decomposition baseline.

Measure task quality, unnecessary agent calls, token/communication cost, latency, robustness to agent failure, and amount of data exposed to agents.
