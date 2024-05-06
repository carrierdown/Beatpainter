import math
import numpy as np

default_fade_out_curve = 1 - np.power(np.arange(0.0, 1.0, 1 / math.floor(20 * 44.1), dtype=float), 8)
default_fade_in_curve = np.linspace(0.0, 1.0, 88)
