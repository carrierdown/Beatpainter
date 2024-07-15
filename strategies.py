import helpers
import copy

from AudioClip import AudioClip
from AudioEvent import AudioEvent


def shuffle_by_duration(source_clip: AudioClip,
                        substitution_clips: list[AudioClip],
                        normalize_durations) -> list[AudioEvent]:
    result = []
    if not (len(source_clip.events) > 0 and len(substitution_clips) > 0 and len(substitution_clips[0].events) > 0):
        return result

    substitution_events = [event for substitution_clip in substitution_clips for event in substitution_clip.events]
    candidates = [event.duration for event in substitution_events]

    if normalize_durations:
        processed_candidate_durations = helpers.normalize(candidates,
                                                          min(event.duration for event in source_clip.events),
                                                          max(event.duration for event in source_clip.events))
    else:
        processed_candidate_durations = candidates

    for i in range(len(source_clip.events)):
        closest_index = helpers.get_closest_index(processed_candidate_durations, source_clip.events[i].duration)
        old_event = source_clip.events[i]
        new_event = copy.copy(substitution_events[closest_index])
        new_event.start = old_event.start
        new_event.duration = old_event.duration

        result.append(new_event)
    return result
