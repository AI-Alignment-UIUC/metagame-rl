"""Policy-value networks.

IdentityMLP is the identity-indexed baseline (plan items A1.3 / A3): the encoder's fixed-size
observation in, one logit per action id plus a value out. Observations arrive as bytes
(round(48 * x), exact for the encoder), so the network divides by 48 itself and the same
uint8 tensor goes to ONNX in the rollout workers and to the GPU here.
"""
import torch
import torch.nn as nn


class IdentityMLP(nn.Module):
    def __init__(self, obs_size: int, action_size: int, hidden: int = 512, layers: int = 2):
        super().__init__()
        self.obs_size, self.action_size, self.hidden, self.layers = obs_size, action_size, hidden, layers
        blocks, width = [], obs_size
        for _ in range(layers):
            blocks += [nn.Linear(width, hidden), nn.LayerNorm(hidden), nn.GELU()]
            width = hidden
        self.trunk = nn.Sequential(*blocks)
        self.policy = nn.Linear(hidden, action_size)
        self.value = nn.Linear(hidden, 1)
        nn.init.zeros_(self.policy.weight)      # start uniform over the legal actions
        nn.init.zeros_(self.policy.bias)
        nn.init.zeros_(self.value.weight)
        nn.init.zeros_(self.value.bias)

    def forward(self, obs_u8: torch.Tensor):
        h = self.trunk(obs_u8.float() / 48.0)
        return self.policy(h), torch.tanh(self.value(h)).squeeze(-1)

    def config(self) -> dict:
        return dict(kind="IdentityMLP", obs_size=self.obs_size, action_size=self.action_size,
                    hidden=self.hidden, layers=self.layers)


def build(config: dict) -> nn.Module:
    kind = config.get("kind", "IdentityMLP")
    if kind == "IdentityMLP":
        return IdentityMLP(config["obs_size"], config["action_size"], config.get("hidden", 512), config.get("layers", 2))
    raise ValueError(f"unknown model kind {kind}")


def export_onnx(model: nn.Module, path: str) -> None:
    """Export for the Node rollout workers: input obs uint8 [batch, obs_size],
    outputs logits [batch, action_size] and value [batch]."""
    model = model.eval().to("cpu")
    dummy = torch.zeros(2, model.obs_size, dtype=torch.uint8)
    torch.onnx.export(model, (dummy,), path, input_names=["obs"], output_names=["logits", "value"],
                      dynamic_axes={"obs": {0: "batch"}, "logits": {0: "batch"}, "value": {0: "batch"}},
                      opset_version=17, dynamo=False)
