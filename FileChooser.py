from dataclasses import dataclass
import numpy as np


@dataclass
class FileChooser:
    rng: np.random.Generator
    file_selection_method: str
    index: int = 0

    def choose(self, values: list):
        if self.file_selection_method == "random":
            return self.rng.choice(values)
        value = values[self.index % len(values)]
        self.index += 1
        return value
