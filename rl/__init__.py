"""Learner side of the training bridge: PyTorch models, PPO, and rollout I/O.

Rollouts are played in Node (env/rollout_worker.js) with the policy exported to ONNX; this
package trains on what they write and exports the next policy.
"""
