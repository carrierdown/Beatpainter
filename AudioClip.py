from dataclasses import dataclass
from typing import List
from AudioEvent import AudioEvent


@dataclass
class AudioClip:
    events: List[AudioEvent]
    sample_rate: int = 44100
    num_channels: int = 1
