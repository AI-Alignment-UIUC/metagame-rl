"""Matchup model (plan item A5): P(deck a beats deck b) from the two decklists.

A deck is embedded as the count-weighted mean of its card embeddings (card features + frozen
rules-text embedding + a learned per-card residual, as in the token model), then an MLP.
The prediction is antisymmetric by construction: P(a beats b) = sigmoid(f(a, b) - f(b, a)), so
P(a, b) = 1 - P(b, a) and a deck against itself is exactly 0.5.

Trained on game results (wins and games per pair, from env/tools/matrix.js), refit each PSRO
iteration on everything played so far, because the deck builder will exploit its errors.
"""
import json

import numpy as np
import torch
import torch.nn as nn

from rl.token_model import card_feature_matrix


class MatchupModel(nn.Module):
    def __init__(self, table: list, text_emb: np.ndarray, d: int = 128, hidden: int = 256):
        super().__init__()
        self.register_buffer("feats", torch.from_numpy(card_feature_matrix(table)))
        self.register_buffer("text", torch.from_numpy(text_emb.astype(np.float32)))
        n = self.feats.shape[0]
        self.card_struct = nn.Linear(self.feats.shape[1], d)
        self.card_text = nn.Linear(self.text.shape[1], d)
        self.card_resid = nn.Embedding(n, d)
        nn.init.zeros_(self.card_resid.weight)
        self.deck = nn.Sequential(nn.Linear(d, hidden), nn.GELU(), nn.Linear(hidden, d))
        self.pair = nn.Sequential(nn.Linear(4 * d, hidden), nn.GELU(), nn.Linear(hidden, hidden), nn.GELU(),
                                  nn.Linear(hidden, 1))

    def card_table(self):
        return self.card_struct(self.feats) + self.card_text(self.text) + self.card_resid.weight

    def embed(self, counts: torch.Tensor) -> torch.Tensor:
        """counts [B, n] -> deck embeddings [B, d]."""
        return self.deck(counts.float() @ self.card_table() / 60.0)

    def logit(self, za, zb):
        f = lambda x, y: self.pair(torch.cat([x, y, x * y, x - y], -1)).squeeze(-1)
        return f(za, zb) - f(zb, za)

    def forward(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        """P(a beats b) for count vectors a, b [B, n]."""
        return torch.sigmoid(self.logit(self.embed(a), self.embed(b)))


def fit(model: MatchupModel, decks: np.ndarray, wins: np.ndarray, games: np.ndarray, device: str,
        epochs: int = 400, lr: float = 3e-3, weight_decay: float = 1e-4, holdout: float = 0.0, seed: int = 0):
    """Fits on pair results: decks [D, n] counts; wins[i][j] = wins of i against j, games[i][j]."""
    rng = np.random.default_rng(seed)
    pairs = [(i, j) for i in range(len(decks)) for j in range(len(decks)) if i < j and games[i][j] > 0]
    rng.shuffle(pairs)
    k = int(len(pairs) * holdout)
    test, train = pairs[:k], pairs[k:]
    D = torch.from_numpy(decks).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    def tensors(ps):
        i = torch.tensor([p[0] for p in ps], device=device)
        j = torch.tensor([p[1] for p in ps], device=device)
        w = torch.tensor([wins[p[0]][p[1]] for p in ps], dtype=torch.float32, device=device)
        g = torch.tensor([games[p[0]][p[1]] for p in ps], dtype=torch.float32, device=device)
        return i, j, w, g

    def nll(ps):
        i, j, w, g = tensors(ps)
        p = model(D[i], D[j]).clamp(1e-5, 1 - 1e-5)
        return -(w * p.log() + (g - w) * (1 - p).log()).sum() / g.sum(), p, w / g

    model.to(device).train()
    for _ in range(epochs):
        loss, _, _ = nll(train)
        opt.zero_grad()
        loss.backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        out = {"train_nll": float(nll(train)[0])}
    if test:
        with torch.no_grad():
            l, p, y = nll(test)
            out.update(test_nll=float(l), test_mae=float((p - y).abs().mean()),
                       test_direction=float(((p > 0.5) == (y > 0.5)).float().mean()))
    return out
