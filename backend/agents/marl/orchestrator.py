"""SaRaDE multi-agent coordinator.

The coordinator uses QMIX when a checkpoint is present and falls back to a
transparent deterministic policy otherwise. It never reads Anumati lockers.
Only the data explicitly passed to it is available to the agents.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import torch

from .env import AGENT_NAMES, ACTION_NAMES, STATE_DIM, SaRaDECoordinationEnv
from .qmix import QMIX


CHECKPOINT = Path(__file__).resolve().parent / "qmix_sarade.pt"


def state_from_context(profile: Dict, matches=None, learning_map=None, sop=None, consent_scope=None):
    skills = profile.get("skills") or []
    interests = profile.get("research_interests") or []
    education = profile.get("education") or []
    matches = matches or []
    lm = learning_map or {}
    sop_text = (sop or {}).get("draft", "") if isinstance(sop, dict) else ""
    gaps = lm.get("gaps") or lm.get("skill_gaps") or []
    consent_ok = 1.0 if consent_scope else 0.75
    return np.array([
        min(1.0, (len(skills) + len(interests) + len(education)) / 18.0),
        min(1.0, max([float(m.get("score", 0)) for m in matches] or [0]) / 100.0),
        max(0.0, 1.0 - min(1.0, len(gaps) / 8.0)),
        min(1.0, len(sop_text) / 1800.0),
        0.85 if (matches and sop_text) else 0.35,
        consent_ok,
        0.25 * bool(profile) + 0.25 * bool(matches) + 0.25 * bool(lm) + 0.25 * bool(sop_text),
        0.0,
        1.0,
        0.0,
    ], dtype=np.float32)


def _fallback_actions(state):
    # Transparent policy used if no learned checkpoint is supplied.
    actions = np.zeros(4, dtype=int)
    if state[0] < 0.85:
        actions[0] = 1
    if state[1] < 0.75:
        actions[1] = 1
    if state[2] < 0.75:
        actions[2] = 1
    if state[3] < 0.75 and state[1] > 0.20:
        actions[3] = 1
    if state[6] > 0.60:
        actions[np.argmax(state[:4])] = 2
    return actions


def choose_actions(state, checkpoint: str | Path | None = None):
    checkpoint = Path(checkpoint or CHECKPOINT)
    if checkpoint.exists():
        try:
            model = QMIX.load(checkpoint)
            env = SaRaDECoordinationEnv()
            obs = env.local_observations(np.asarray(state, dtype=np.float32))
            with torch.no_grad():
                actions = model.greedy_actions(torch.tensor(obs[None], dtype=torch.float32))[0].cpu().numpy()
            actions = actions.astype(int)
            # Safety guard: a learned policy must not produce an empty workflow when
            # the task is materially incomplete. The guard is deterministic and is
            # reported explicitly so experiments can distinguish pure QMIX from the
            # production-safe hybrid policy.
            if not actions.any() and (state[0] < 0.85 or state[1] < 0.75 or state[2] < 0.75 or state[3] < 0.75):
                return _fallback_actions(np.asarray(state, dtype=np.float32)), "qmix_guarded"
            return actions, "qmix"
        except Exception:
            pass
    return _fallback_actions(np.asarray(state, dtype=np.float32)), "fallback"


def plan(state, checkpoint=None):
    actions, policy = choose_actions(state, checkpoint)
    return {
        "policy": policy,
        "actions": {name: {"action_id": int(a), "action": ACTION_NAMES[int(a)]} for name, a in zip(AGENT_NAMES, actions)},
        "selected_agents": [name for name, a in zip(AGENT_NAMES, actions) if a != 0],
    }
