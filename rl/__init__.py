"""Learner side of the training bridge: PyTorch models, PPO, and rollout I/O.

Rollouts are played in Node (env/remote_worker.js), whose decisions the policy answers here
(rl/remote.py); this package trains on what they record.
"""
