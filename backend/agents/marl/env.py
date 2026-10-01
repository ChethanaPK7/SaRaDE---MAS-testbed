"""Small deterministic SaRaDE coordination environment for QMIX research.

This environment is deliberately domain-specific but LLM-free: it models whether
invoking each specialized agent improves an ecosystem state enough to justify its
cost. It is used for reproducible training/evaluation of the coordinator.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

AGENT_NAMES = ["profile", "matcher", "learning_map", "sop"]
ACTION_NAMES = ["skip", "run", "verify"]
N_AGENTS = len(AGENT_NAMES)
N_ACTIONS = len(ACTION_NAMES)
STATE_DIM = 10


@dataclass
class StepResult:
    state: np.ndarray
    reward: float
    done: bool
    info: Dict


class SaRaDECoordinationEnv:
    """Toy-but-grounded CTDE environment.

    State features are normalized [0, 1]:
      0 profile completeness
      1 opportunity-fit quality
      2 skill-gap coverage
      3 SOP quality
      4 verification confidence
      5 consent scope adequacy
      6 task progress
      7 repeated-call pressure
      8 communication budget remaining
      9 data-exposure pressure

    A joint action is one action per agent: skip/run/verify.
    """

    def __init__(self, seed: int = 7, max_steps: int = 8):
        self.rng = np.random.default_rng(seed)
        self.max_steps = max_steps
        self.steps = 0
        self.state = np.zeros(STATE_DIM, dtype=np.float32)

    @property
    def n_agents(self):
        return N_AGENTS

    @property
    def n_actions(self):
        return N_ACTIONS

    def reset(self) -> np.ndarray:
        self.steps = 0
        # Hard/easy student-task mix.
        self.state = np.array(
            [
                self.rng.uniform(0.15, 0.75),
                self.rng.uniform(0.05, 0.35),
                self.rng.uniform(0.05, 0.30),
                self.rng.uniform(0.00, 0.20),
                0.15,
                self.rng.uniform(0.45, 0.95),
                0.10,
                0.00,
                1.00,
                self.rng.uniform(0.00, 0.15),
            ],
            dtype=np.float32,
        )
        return self.state.copy()

    def local_observations(self, state: np.ndarray | None = None) -> np.ndarray:
        s = self.state if state is None else state
        obs = []
        for i in range(N_AGENTS):
            # Each agent sees relevant global state + a stable role one-hot.
            role = np.zeros(N_AGENTS, dtype=np.float32)
            role[i] = 1.0
            obs.append(np.concatenate([s, role]))
        return np.stack(obs)

    def step(self, actions: List[int]) -> StepResult:
        actions = [int(a) for a in actions]
        if len(actions) != N_AGENTS or any(a < 0 or a >= N_ACTIONS for a in actions):
            raise ValueError(f"Expected {N_AGENTS} actions in [0,{N_ACTIONS-1}]")

        old = self.state.copy()
        progress_gain = np.zeros(4, dtype=np.float32)
        exposure = 0.0
        calls = 0

        for i, action in enumerate(actions):
            if action == 0:
                continue
            calls += 1
            strength = 0.08 if action == 1 else 0.05
            if i == 0:
                progress_gain[i] = strength * (1.0 - old[0])
            elif i == 1:
                progress_gain[i] = strength * (1.0 - old[1])
            elif i == 2:
                progress_gain[i] = strength * (1.0 - old[2])
            else:
                progress_gain[i] = strength * (1.0 - old[3])
            exposure += 0.035 if action == 1 else 0.015

        self.state[0] = min(1.0, old[0] + progress_gain[0])
        self.state[1] = min(1.0, old[1] + progress_gain[1] * (0.5 + 0.5 * old[0]))
        self.state[2] = min(1.0, old[2] + progress_gain[2] * (0.5 + 0.5 * old[1]))
        self.state[3] = min(1.0, old[3] + progress_gain[3] * (0.5 + 0.5 * old[2]))

        # Verification is useful only after something has been produced.
        if actions[0] == 2 or actions[1] == 2 or actions[2] == 2 or actions[3] == 2:
            self.state[4] = min(1.0, self.state[4] + 0.08 * self.state[6] + 0.02)
        else:
            self.state[4] = max(0.0, self.state[4] - 0.005)

        self.state[6] = min(1.0, float(np.mean(self.state[0:4])))
        self.state[7] = min(1.0, old[7] + max(0, calls - 1) * 0.08)
        self.state[8] = max(0.0, old[8] - calls * 0.08)
        self.state[9] = min(1.0, old[9] + exposure)

        quality_before = 0.30 * old[1] + 0.25 * old[2] + 0.20 * old[3] + 0.15 * old[4] + 0.10 * old[6]
        quality = 0.30 * self.state[1] + 0.25 * self.state[2] + 0.20 * self.state[3] + 0.15 * self.state[4] + 0.10 * self.state[6]
        quality_gain = quality - quality_before
        cost = 0.025 * calls + 0.018 * max(0, calls - 1) + 0.025 * self.state[9]
        redundancy = 0.012 * max(0, calls - 2)
        terminal_bonus = 0.20 * quality if self.steps + 1 >= self.max_steps else 0.0
        reward = float(quality_gain + terminal_bonus - cost - redundancy)

        self.steps += 1
        done = self.steps >= self.max_steps or self.state[6] >= 0.90 or self.state[8] <= 0.0
        info = {"quality": float(quality), "calls": calls, "exposure": float(exposure), "state_before": old.tolist()}
        return StepResult(self.state.copy(), reward, done, info)

    def sample_transition(self) -> Tuple[np.ndarray, np.ndarray, float, np.ndarray, bool]:
        state = self.reset()
        obs = self.local_observations(state)
        actions = self.rng.integers(0, N_ACTIONS, size=N_AGENTS).tolist()
        result = self.step(actions)
        return obs, np.asarray(actions, dtype=np.int64), result.reward, self.local_observations(result.state), result.done
