"""
Experience replay buffer for the DQN agent.

The agent stores (state, action, reward, next_state, done) tuples from each
environment step into a circular buffer. At training time we sample a random
minibatch from this memory instead of learning only from the most recent
step. This breaks temporal correlation between consecutive samples and
stabilises gradient updates -- a central trick from the original DQN paper
(Mnih et al. 2015) and explicitly mentioned in Lin et al. 2023, our
supporting DRL reference.

In our setting each "episode" is one channel realisation, so every stored
experience has done=True and the Bellman bootstrap term is automatically
zero. The replay mechanism still matters because it lets the network learn
from a diverse batch of past channel conditions per gradient step.
"""

from __future__ import annotations

from collections import deque
from typing import Tuple

import numpy as np


class ReplayBuffer:
    """Fixed-capacity circular buffer of past experiences."""

    def __init__(self, capacity: int = 10_000, seed: int | None = None):
        self.capacity = int(capacity)
        self._memory: deque = deque(maxlen=self.capacity)
        self._rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._memory)

    def is_ready(self, batch_size: int) -> bool:
        """True iff the buffer holds at least `batch_size` samples."""
        return len(self._memory) >= batch_size

    # ------------------------------------------------------------------
    def push(self,
             state: np.ndarray,
             action: int,
             reward: float,
             next_state: np.ndarray,
             done: bool) -> None:
        """Store one transition."""
        self._memory.append((
            np.asarray(state, dtype=np.float32),
            int(action),
            float(reward),
            np.asarray(next_state, dtype=np.float32),
            bool(done),
        ))

    # ------------------------------------------------------------------
    def sample(self, batch_size: int
               ) -> Tuple[np.ndarray, np.ndarray, np.ndarray,
                          np.ndarray, np.ndarray]:
        """
        Return a random minibatch as five stacked numpy arrays:
            states:      (B, state_dim)   float32
            actions:     (B,)             int32
            rewards:     (B,)             float32
            next_states: (B, state_dim)   float32
            dones:       (B,)             float32 (0.0 / 1.0)
        """
        idx = self._rng.integers(0, len(self._memory), size=batch_size)
        batch = [self._memory[i] for i in idx]

        states      = np.stack([b[0] for b in batch]).astype(np.float32)
        actions     = np.array([b[1] for b in batch], dtype=np.int32)
        rewards     = np.array([b[2] for b in batch], dtype=np.float32)
        next_states = np.stack([b[3] for b in batch]).astype(np.float32)
        dones       = np.array([b[4] for b in batch], dtype=np.float32)

        return states, actions, rewards, next_states, dones
