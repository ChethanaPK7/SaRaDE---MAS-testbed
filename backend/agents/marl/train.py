"""Train the SaRaDE QMIX coordinator.

Usage from backend/:
    python -m agents.marl.train --episodes 1500
"""
import argparse
from pathlib import Path

from .env import SaRaDECoordinationEnv
from .qmix import train_qmix


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", default=str(Path(__file__).with_name("qmix_sarade.pt")))
    args = parser.parse_args()
    env = SaRaDECoordinationEnv(seed=args.seed)
    train_qmix(env, episodes=args.episodes, seed=args.seed, checkpoint=args.output)
    print(f"Saved QMIX checkpoint to {args.output}")
