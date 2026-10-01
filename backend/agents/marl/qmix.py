"""Minimal PyTorch QMIX implementation for SaRaDE.

Reference: Rashid et al., "QMIX: Monotonic Value Function Factorisation for
Deep Multi-Agent Reinforcement Learning", ICML 2018.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from torch import nn


class AgentQNetwork(nn.Module):
    def __init__(self, obs_dim: int, n_actions: int, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, n_actions),
        )

    def forward(self, obs):
        return self.net(obs)


class QMixer(nn.Module):
    """Monotonic mixing network using non-negative hypernetwork weights."""

    def __init__(self, n_agents: int, state_dim: int, embed_dim: int = 32):
        super().__init__()
        self.n_agents = n_agents
        self.embed_dim = embed_dim
        self.w1 = nn.Linear(state_dim, n_agents * embed_dim)
        self.b1 = nn.Linear(state_dim, embed_dim)
        self.w2 = nn.Linear(state_dim, embed_dim)
        self.v = nn.Sequential(nn.Linear(state_dim, embed_dim), nn.ReLU(), nn.Linear(embed_dim, 1))

    def forward(self, agent_qs, state):
        # agent_qs: [B, N]
        bsz = agent_qs.shape[0]
        w1 = torch.abs(self.w1(state)).view(bsz, self.n_agents, self.embed_dim)
        b1 = self.b1(state).view(bsz, 1, self.embed_dim)
        hidden = torch.bmm(agent_qs.unsqueeze(1), w1) + b1
        hidden = torch.abs(hidden)
        w2 = torch.abs(self.w2(state)).view(bsz, self.embed_dim, 1)
        v = self.v(state).view(bsz, 1, 1)
        y = torch.bmm(hidden, w2) + v
        return y.view(bsz)


@dataclass
class QMixConfig:
    obs_dim: int
    state_dim: int
    n_agents: int
    n_actions: int
    hidden: int = 64
    mixer_embed: int = 32
    gamma: float = 0.95
    lr: float = 2e-3


class QMIX(nn.Module):
    def __init__(self, config: QMixConfig):
        super().__init__()
        self.config = config
        self.agents = nn.ModuleList([
            AgentQNetwork(config.obs_dim, config.n_actions, config.hidden)
            for _ in range(config.n_agents)
        ])
        self.mixer = QMixer(config.n_agents, config.state_dim, config.mixer_embed)

    def agent_values(self, obs):
        # obs [B, N, O]
        return torch.stack([net(obs[:, i, :]) for i, net in enumerate(self.agents)], dim=1)

    def chosen_joint_q(self, obs, state, actions):
        q = self.agent_values(obs)
        chosen = q.gather(2, actions.unsqueeze(-1)).squeeze(-1)
        return self.mixer(chosen, state)

    def greedy_actions(self, obs):
        q = self.agent_values(obs)
        return q.argmax(dim=-1)

    def save(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"config": self.config.__dict__, "state_dict": self.state_dict()}, path)

    @classmethod
    def load(cls, path: str | Path, map_location="cpu"):
        payload = torch.load(path, map_location=map_location, weights_only=False)
        model = cls(QMixConfig(**payload["config"]))
        model.load_state_dict(payload["state_dict"])
        model.eval()
        return model


def train_qmix(env, episodes=1500, seed=7, checkpoint=None):
    """Train on the deterministic synthetic coordination environment.

    This is a reproducible research baseline, not production personalization.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)
    obs_dim = env.local_observations().shape[-1]
    cfg = QMixConfig(obs_dim, env.state.size, env.n_agents, env.n_actions)
    model = QMIX(cfg)
    target = QMIX(cfg)
    target.load_state_dict(model.state_dict())
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    epsilon = 1.0
    replay = []
    rng = np.random.default_rng(seed)

    for episode in range(episodes):
        state = env.reset()
        for _ in range(env.max_steps):
            obs = env.local_observations(state)
            if rng.random() < epsilon:
                actions = rng.integers(0, env.n_actions, size=env.n_agents)
            else:
                with torch.no_grad():
                    actions = model.greedy_actions(torch.tensor(obs[None], dtype=torch.float32))[0].numpy()
            result = env.step(actions.tolist())
            next_obs = env.local_observations(result.state)
            replay.append((obs, state.copy(), actions.copy(), result.reward, next_obs, result.state.copy(), result.done))
            state = result.state
            if len(replay) > 2048:
                replay.pop(0)
            if result.done:
                break

        epsilon = max(0.08, epsilon * 0.995)
        if len(replay) >= 64 and episode % 2 == 0:
            batch = [replay[i] for i in rng.integers(0, len(replay), 64)]
            obs_b = torch.tensor(np.stack([x[0] for x in batch]), dtype=torch.float32)
            state_b = torch.tensor(np.stack([x[1] for x in batch]), dtype=torch.float32)
            act_b = torch.tensor(np.stack([x[2] for x in batch]), dtype=torch.long)
            rew_b = torch.tensor([x[3] for x in batch], dtype=torch.float32)
            next_obs_b = torch.tensor(np.stack([x[4] for x in batch]), dtype=torch.float32)
            next_state_b = torch.tensor(np.stack([x[5] for x in batch]), dtype=torch.float32)
            done_b = torch.tensor([x[6] for x in batch], dtype=torch.float32)

            q = model.chosen_joint_q(obs_b, state_b, act_b)
            with torch.no_grad():
                next_actions = target.greedy_actions(next_obs_b)
                next_q = target.chosen_joint_q(next_obs_b, next_state_b, next_actions)
                target_q = rew_b + cfg.gamma * (1.0 - done_b) * next_q
            loss = nn.functional.smooth_l1_loss(q, target_q)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
            optimizer.step()

        if episode % 50 == 0:
            target.load_state_dict(model.state_dict())

    if checkpoint:
        model.save(checkpoint)
    return model
