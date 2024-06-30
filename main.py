import copy
import pathlib
import click
import random
import aubio
import helpers
from typing import List
from pedalboard_native.io import AudioFile

from AudioEvent import AudioEvent
from AudioClip import AudioClip

# Files longer than this will have a random clip extracted from it
SPLIT_THRESHOLD_IN_SECONDS = 15
ONE_SHOT_SLICE_THRESHOLD_SECONDS = 3


@click.command()
@click.option("--number-of-seqs", "-n",
              type=click.IntRange(1, 1000, clamp=True),
              default=1,
              show_default=True,
              help="Number of sequences to generate")
@click.option("--generation-depth", "-d",
              type=int,
              default=1,
              show_default=True,
              help="Number of sequences to involve in the generation of a single loop")
@click.option("--substitution-dir", "-s",
              type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=pathlib.Path),
              default=".",
              show_default=True,
              help="Path to directory containing audio files used to produce new loops based on the source audio. "
                   "If left unspecified, the source directory is used for substitutions as well")
@click.option("--output", "-o",
              type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True, path_type=pathlib.Path),
              default=".",
              show_default=True,
              help="Path to output directory")
@click.option("--source-dir", "-src",
              type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=pathlib.Path),
              default=".",
              show_default=True,
              help="Path to directory containing source audio files. These are then sliced and data for each slice "
                   "is used to inform what audio events from the substitutions directory to replace them with")
@click.option("--seed", "-s",
              type=int,
              help="Seed for random number generator",
              show_default="current time")
@click.option("--trim",
              is_flag=True,
              help="Trim audio snippets to the nearest transient")
@click.option("--one-shot-mode",
              type=click.Choice(["long", "true", "false"], case_sensitive=False),
              default="false",
              show_default=True,
              help="Use one shots instead of loops as substitutions for loop generation. If long is specified, the "
                   "special LongOneShotMode is enabled, which extracts several shorter one shots from longer sustained "
                   "one shot sounds.")
@click.option('--strategy',
              type=click.Choice(
                  [
                      "Interleave",
                      "InterleavedShuffle",
                      "ShuffleByDuration",
                      "ShuffleByPitch"
                  ],
                  case_sensitive=False),
              default="ShuffleByDuration",
              show_default=True,
              help="Strategy for generating audio sequences"
              )
@click.option("--recurse-sub-dirs",
              is_flag=True,
              help="Recurse into subdirectories when fetching substitution audio files")
@click.option("--normalize-durations",
              is_flag=True,
              help="Normalize durations of candidates so that they fall within the same range as the source "
                   "durations, thus making for better matches with the source event durations")
@click.option("--min-duration",
              type=click.IntRange(1, SPLIT_THRESHOLD_IN_SECONDS, clamp=True),
              help="Minimum duration of extracted audio clips in seconds")
@click.option("--max-duration",
              type=click.IntRange(2, SPLIT_THRESHOLD_IN_SECONDS * 2, clamp=True),
              help="Maximum duration of extracted audio clips in seconds")
@click.option("--onset-method",
              type=click.Choice(
                  [
                      "default",
                      "energy",
                      "hfc",
                      "complex",
                      "phase",
                      "specdiff",
                      "kl",
                      "mkl",
                      "specflux"
                  ],
                  case_sensitive=False),
              default="specflux",
              show_default=True,
              help="Aubio onset detection method")
@click.option("--file-selection-method",
              type=click.Choice(
                  [
                      "random",
                      "sequential"
                  ],
                  case_sensitive=False),
              help="Method for selecting source audio files")
def beat_shuffler(number_of_seqs: int, generation_depth: int, substitution_dir: str, output: str, source_dir: str,
                  seed: int, trim: bool, one_shot_mode: str, strategy: str, recurse_sub_dirs: bool,
                  normalize_durations: bool, min_duration: int, max_duration: int, onset_method: str,
                  file_selection_method: str):
    click.echo(f"Iterating all audio files in folder {source_dir} with seed {seed}")
    click.echo(f"You chose {strategy}")
    if seed != -1:
        random.seed(seed)
    source_path = pathlib.Path(source_dir)
    source_files = get_audio_files(source_path, False)
    substitution_path = pathlib.Path(substitution_dir) if substitution_dir else source_path
    substitution_files = get_audio_files(substitution_path, recurse_sub_dirs)
    if not source_files:
        click.echo("No audio files were found in the supplied source directory")
        exit(0)
    if not substitution_files:
        click.echo("No audio files were found in the supplied substitution directory")
        exit(0)

    for i in range(number_of_seqs):
        selected_file = random.choice(source_files)
        click.echo(f"Selected file {selected_file}")
        source_clip = get_audio_clip(str(selected_file), random.random() * .9,
                                     random.randint(min_duration, max_duration), onset_method)
        click.echo(f"Got clip with {len(source_clip.events)} events")
        substitution_clips = get_substitution_clips(substitution_files, min_duration, max_duration, one_shot_mode)
        result_events = generate_sequence(strategy, source_clip, substitution_clips, min_duration, max_duration,
                                          onset_method)
        result = AudioClip(result_events)
        # write result_clip to disk


def generate_sequence(strategy: str, source_clip: AudioClip, substitution_clips: list[AudioClip], min_duration: int,
                      max_duration: int, onset_method: str) -> list[AudioEvent]:
    if strategy == "ShuffleByDuration":
        return shuffle_by_duration(source_clip, substitution_clips, min_duration, max_duration, onset_method)
    return []


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


def get_substitution_clips(substitution_files, min_duration, max_duration, one_shot_mode) -> list[AudioClip]:
    clips = list()
    for file in substitution_files:
        clips.append(get_audio_clip(str(file), random.random() * .9, random.randint(min_duration, max_duration)))
    return clips


def get_audio_clip(filename: str,
                   start_offset_fraction: float,
                   duration_secs: int,
                   aubio_method: str = "hfc") -> AudioClip:
    win_s = 512  # fft size
    hop_s = win_s // 2  # hop size
    onsets = []  # contains sample indexes to all onsets in the current clip, including start and end points
    all_samples = []
    samples_read = 0
    with AudioFile(filename) as file:
        clip_size_fraction = duration_secs / file.duration
        start_offset_fraction *= (.975 - clip_size_fraction)
        start_offset = 0
        if clip_size_fraction < .9:
            start_offset = int(file.duration * start_offset_fraction)
        onset_detector = aubio.onset(aubio_method, samplerate=file.samplerate, hop_size=hop_s, buf_size=win_s)
        start_offset_samples = int(start_offset * file.samplerate)
        num_samples = int(duration_secs * file.samplerate)
        file.seek(start_offset_samples)
        while samples_read < num_samples:
            samples = file.read(hop_s)
            samples_read += len(samples[0, :])
            # we only keep left channel
            all_samples.extend(samples[0, :])
            if len(samples[0, :]) < hop_s:
                break
            if onset_detector(samples[0, :]):
                onsets.append(onset_detector.get_last())
    onsets.insert(0, 0)  # First onset always starts at 0
    onsets.append(samples_read)  # Last onset = end of clip
    events: List[AudioEvent] = list()
    for ix, onset in enumerate(onsets[0:-1]):
        duration = onsets[ix + 1] - onset
        events.append(AudioEvent(onset, duration, 0, all_samples[onset:onset + duration], 0, True))
    return AudioClip(events)


def write_audio_clip(filename: str, clip: AudioClip):
    with AudioFile(filename, "w", samplerate=clip.sample_rate, num_channels=clip.num_channels) as f:
        for event in clip.events:
            f.write(event.audio_data)


def get_audio_files(path, recurse):
    if recurse:
        return [p for pattern in ["*.wav", "*.mp3", "*.aiff"]
                for p in path.rglob(pattern)
                if not p.name.startswith('._')]
    else:
        return [p for pattern in ["*.wav", "*.mp3", "*.aiff"]
                for p in path.glob(pattern)
                if not p.name.startswith('._')]


if __name__ == "__main__":
    beat_shuffler()
