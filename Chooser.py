from dataclasses import dataclass, field

import numpy as np


@dataclass
class Chooser:
    rng: np.random.Generator
    random: bool = True
    index: int = 0
    values: list = field(default_factory=list)

    def choose(self):
        if self.random:
            return self.rng.choice(self.values)
        value = self.values[self.index % len(self.values)]
        self.index += 1
        return value

    def reset(self):
        self.index = 0
