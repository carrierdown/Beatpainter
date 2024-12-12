import click

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


def interleave(source_clip: AudioClip,
               substitution_clips: list[AudioClip],
               chunk_sizes: list[int]) -> list[AudioEvent]:
    substitution_clips = [source_clip] + substitution_clips
    result = []
    lengths = [len(substitution_clip.events) for substitution_clip in substitution_clips]
    index = 0
    event_indexes = [0 for length in lengths]
    chunk_index = 0
    # click.echo(f"got lengths: {lengths}, event indexes {event_indexes}")
    max_length = max(lengths)
    # make sure all clips have the same number of events
    for i in range(len(substitution_clips)):
        substitution_clip = substitution_clips[i]
        while len(substitution_clip.events) < max_length:
            num_events = len(substitution_clip.events)
            substitution_clip.events += substitution_clip.events[0:min(num_events, max_length - num_events)]
        click.echo(f"clip.events # {len(substitution_clip.events)}")

    i = 0
    while 1:
        start = event_indexes[index]
        end = min(start + chunk_sizes[chunk_index], max_length)
        event_indexes[index] = end
        result += substitution_clips[index].events[start:end]
        index = (index + 1) % len(substitution_clips)
        chunk_index = (chunk_index + 1) % len(chunk_sizes)
        # if end >= max_length:
        if sum(event_indexes) >= max_length:
            break

    return result
