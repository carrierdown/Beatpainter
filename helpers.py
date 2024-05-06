import numpy as np


def get_closest_index(number_list: list[int], target: int) -> int:
    if len(number_list) == 0:
        return 0
    smallest_diff = abs(number_list[0] - target)
    closest_index = 0
    for i, number in enumerate(number_list[1:], 1):
        diff = abs(number - target)
        if diff < smallest_diff:
            smallest_diff = diff
            closest_index = i
    return closest_index


def normalize(source_values: list[int], target_min: int, target_max: int) -> list[int]:
    if target_min > target_max:
        target_min, target_max = target_max, target_min
    source_min = min(duration for duration in source_values)
    source_max = max(duration for duration in source_values)
    rescale_factor = (target_max - target_min) / (source_max - source_min)
    normalized = np.array(source_values).astype(float)
    normalized -= source_min
    normalized *= rescale_factor
    normalized = np.floor(normalized + target_min).astype(int)
    return normalized.tolist()
