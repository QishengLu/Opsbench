"""CPU inference adapter for the published OpsAgent PatternMatcher checkpoint."""
from __future__ import annotations

import numpy as np

LABELS = [
    "Level shift up", "Level shift down", "Steady increase", "Steady decrease",
    "Single spike", "Single dip", "Transient level shift up", "Transient level shift down",
    "Multiple spikes", "Multiple dips", "Fluctuations",
]


class ShapeClassifier:
    def __init__(self, checkpoint):
        import torch
        from torch import nn
        torch.set_num_threads(1)

        class Network(nn.Module):
            def __init__(self):
                super().__init__()
                for i, (incoming, outgoing, bias) in enumerate(
                    [(1, 64, True), (64, 128, False), (128, 256, False)], start=1
                ):
                    setattr(self, f"conv{i}", nn.Sequential(
                        nn.Conv1d(incoming, outgoing, kernel_size=5, padding=1, bias=bias),
                        nn.ReLU(), nn.MaxPool1d(2),
                    ))
                self.flatten = nn.Sequential(nn.Linear(512, 64), nn.BatchNorm1d(64), nn.ReLU())
                self.out = nn.Linear(64, 11)

            def forward(self, x):
                x = self.conv3(self.conv2(self.conv1(x)))
                return self.out(self.flatten(x.flatten(1)))

        self.torch = torch
        self.network = Network()
        self.network.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
        self.network.eval()

    def predict(self, values):
        x = np.asarray(values, dtype=np.float32)
        if len(x) != 30 or not np.isfinite(x).all() or x.max() == x.min():
            return None
        x = (x - x.min()) / (x.max() - x.min())
        with self.torch.inference_mode():
            index = int(self.network(self.torch.from_numpy(x).reshape(1, 1, 30)).argmax())
        return LABELS[index]
