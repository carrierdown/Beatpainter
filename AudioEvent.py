import copy
from dataclasses import dataclass
from typing import List
import numpy as np
import audio_utils


@dataclass
class AudioEvent:
    start: int
    duration: int
    pitch: int
    _audio_data: List[float]
    rms: float
    should_fade_in: bool = True
    _faded_audio_data: np.ndarray = None

    @property
    def audio_data(self):
        if self._faded_audio_data is None:
            self._faded_audio_data = self.apply_fade(self._audio_data, self.should_fade_in, self.duration)
        return self._faded_audio_data

    def apply_new_fade(self):
        self._faded_audio_data = self.apply_fade(self._audio_data, self.should_fade_in, self.duration)

    @staticmethod
    def apply_fade(audio_data: list[float], should_fade_in: bool, duration: int) -> np.ndarray:
        if len(audio_data) > duration:
            audio_data = copy.copy(audio_data[0:duration])
        result = np.array(audio_data)
        if should_fade_in and len(audio_data) > len(audio_utils.default_fade_in_curve):
            result[0:len(audio_utils.default_fade_in_curve)] *= audio_utils.default_fade_in_curve
        if len(audio_data) > len(audio_utils.default_fade_out_curve):
            result[-len(audio_utils.default_fade_out_curve):] *= audio_utils.default_fade_out_curve
        return result
