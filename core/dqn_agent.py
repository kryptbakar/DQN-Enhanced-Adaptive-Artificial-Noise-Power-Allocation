"""
Deep Q-Network agent for AN power-split optimisation.

Architecture (matches the project proposal, Phase 3, step 8):

    Input  (5)  ->  Dense 64 ReLU
                ->  Dense 64 ReLU
                ->  Dense 32 ReLU
                ->  Output 9  (linear, Q-values)

Nine discrete actions map to rho in {0.1, 0.2, ..., 0.9}.

Two identical networks are maintained:
  * online Q-network  -- updated every training step
  * target Q-network  -- a frozen copy, hard-updated every TARGET_SYNC steps

This decoupling is the "target network" trick from Mnih et al. 2015 and is
what distinguishes DQN from vanilla Q-learning. It prevents the network
from "chasing its own tail" during training -- a notorious failure mode
that Lin et al. 2023 (our Sensors reference) cite explicitly.

Because each episode in our setting is one channel realisation with a
one-step decision, every transition we store has done=True and the
Bellman target reduces to:

    y = reward        (no bootstrap from the next state)

We still implement the full bootstrap form so the code is a textbook DQN
and so we can later extend to multi-step sequences (e.g. block-fading
channels) without rewriting the agent.
"""

from __future__ import annotations

import os
from typing import Tuple

import numpy as np

# Keep TF's own noise to a minimum
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


# ---------------------------------------------------------------------------
# Action space
# ---------------------------------------------------------------------------

ACTION_RHOS: np.ndarray = np.round(np.arange(0.1, 0.91, 0.1), 2)  # 9 actions
N_ACTIONS: int = len(ACTION_RHOS)
STATE_DIM: int = 5


def action_to_rho(action: int) -> float:
    """Map a discrete action index in [0, 8] to a concrete rho value."""
    return float(ACTION_RHOS[action])


# ---------------------------------------------------------------------------
# Q-network factory
# ---------------------------------------------------------------------------

def build_q_network(state_dim: int = STATE_DIM,
                    n_actions: int = N_ACTIONS,
                    learning_rate: float = 1e-3) -> keras.Model:
    """
    Build the Q-network exactly as specified in the proposal.

    Returns a compiled Keras Model with Huber loss (robust to the occasional
    reward spike) and Adam optimiser.
    """
    inputs = keras.Input(shape=(state_dim,), name="state")
    x = layers.Dense(64, activation="relu", name="dense1")(inputs)
    x = layers.Dense(64, activation="relu", name="dense2")(x)
    x = layers.Dense(32, activation="relu", name="dense3")(x)
    outputs = layers.Dense(n_actions, activation="linear", name="q_values")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="q_network")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss=keras.losses.Huber(),
    )
    return model


# ---------------------------------------------------------------------------
# DQN agent
# ---------------------------------------------------------------------------

class DQNAgent:
    """
    A lightweight DQN agent with target network, epsilon-greedy exploration
    and Huber-loss Bellman updates.

    Intended usage:
        agent = DQNAgent()
        for ep in range(n_episodes):
            s = env.reset()
            a = agent.act(s, epsilon)
            s2, r, done = env.step(a)
            agent.remember(s, a, r, s2, done)
            agent.learn()
            if ep % TARGET_SYNC == 0:
                agent.sync_target()
    """

    def __init__(self,
                 state_dim: int = STATE_DIM,
                 n_actions: int = N_ACTIONS,
                 gamma: float = 0.0,
                 learning_rate: float = 1e-3,
                 seed: int | None = None):
        """
        Args:
            gamma: discount factor. We default to 0.0 because each episode
                   is a one-step decision (one channel realisation -> one
                   rho choice -> terminal). For multi-step problems set
                   gamma=0.99.
        """
        self.state_dim = state_dim
        self.n_actions = n_actions
        self.gamma = float(gamma)

        self.online_net = build_q_network(state_dim, n_actions, learning_rate)
        self.target_net = build_q_network(state_dim, n_actions, learning_rate)
        self.sync_target()                  # start with identical weights

        self._rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    def sync_target(self) -> None:
        """Hard-copy online weights into the target network."""
        self.target_net.set_weights(self.online_net.get_weights())

    # ------------------------------------------------------------------
    def act(self, state: np.ndarray, epsilon: float) -> int:
        """Epsilon-greedy action selection."""
        if self._rng.random() < epsilon:
            return int(self._rng.integers(0, self.n_actions))
        q_values = self.online_net(
            state.reshape(1, -1).astype(np.float32), training=False
        ).numpy()[0]
        return int(np.argmax(q_values))

    # ------------------------------------------------------------------
    def q_values(self, state: np.ndarray) -> np.ndarray:
        """Return the full Q-value vector for diagnostics/visualisation."""
        return self.online_net(
            state.reshape(1, -1).astype(np.float32), training=False
        ).numpy()[0]

    # ------------------------------------------------------------------
    @tf.function(reduce_retracing=True)
    def _train_step(self,
                    states: tf.Tensor,
                    actions: tf.Tensor,
                    rewards: tf.Tensor,
                    next_states: tf.Tensor,
                    dones: tf.Tensor) -> tf.Tensor:
        """
        One Bellman update:
            y = r + gamma * (1 - done) * max_a' Q_target(s', a')
            loss = Huber(y, Q_online(s, a))
        """
        next_q = tf.reduce_max(self.target_net(next_states, training=False),
                               axis=1)
        targets = rewards + self.gamma * (1.0 - dones) * next_q

        with tf.GradientTape() as tape:
            q_all = self.online_net(states, training=True)
            # pick Q(s, a) for the action actually taken
            idx = tf.stack([tf.range(tf.shape(actions)[0]), actions], axis=1)
            q_sa = tf.gather_nd(q_all, idx)
            loss = tf.reduce_mean(keras.losses.huber(targets, q_sa))

        grads = tape.gradient(loss, self.online_net.trainable_variables)
        self.online_net.optimizer.apply_gradients(
            zip(grads, self.online_net.trainable_variables)
        )
        return loss

    # ------------------------------------------------------------------
    def learn(self, batch) -> float:
        """
        Run one gradient step from a replay-buffer batch and return the loss.

        `batch` is the 5-tuple returned by ReplayBuffer.sample().
        """
        states, actions, rewards, next_states, dones = batch
        loss = self._train_step(
            tf.convert_to_tensor(states, dtype=tf.float32),
            tf.convert_to_tensor(actions, dtype=tf.int32),
            tf.convert_to_tensor(rewards, dtype=tf.float32),
            tf.convert_to_tensor(next_states, dtype=tf.float32),
            tf.convert_to_tensor(dones, dtype=tf.float32),
        )
        return float(loss.numpy())

    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        """Save trained weights to disk (Keras v3 .keras format)."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.online_net.save(path)

    def load(self, path: str) -> None:
        """Load trained weights from disk and sync the target."""
        self.online_net = keras.models.load_model(path)
        self.target_net = keras.models.load_model(path)
