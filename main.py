import click
import numpy as np
import aubio
import helpers
import strategies
import math
import pathlib
from typing import List
from pedalboard_native.io import AudioFile
from AudioEvent import AudioEvent
from AudioClip import AudioClip
from FileChooser import FileChooser
from Logger import Logger

# Files longer than this will have a random clip extracted from it
SPLIT_THRESHOLD_IN_SECONDS = 15
ONE_SHOT_SLICE_THRESHOLD_SECONDS = 3
ONE_SHOT_SLICE_THRESHOLD_SAMPLES = ONE_SHOT_SLICE_THRESHOLD_SECONDS * 44100
SHORTEST_ONE_SHOT = 4410
ONE_SHOT_MAX_SAMPLE_SIZE = 44100 # 1s
MAX_NUMBER_OF_SLICES = 100 # Max number of slices to extract from a single one shot


@click.command()
@click.option("--number-of-seqs", "-n",
              type=click.IntRange(1, 1000, clamp=True),
              default=1,
              show_default=True,
              help="Number of sequences to generate")
@click.option("--generation-depth", "-d",
              type=click.IntRange(1, 10, clamp=True),
              default=1,
              show_default=True,
              help="Number of sequences to involve in the generation of a single loop")
@click.option("--substitution-dir", "-sub",
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
                      "InterleaveInPlace",
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
              default=4,
              help="Minimum duration of extracted audio clips in seconds")
@click.option("--max-duration",
              type=click.IntRange(2, SPLIT_THRESHOLD_IN_SECONDS * 2, clamp=True),
              default=7,
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
              default="random",
              show_default=True,
              type=click.Choice(
                  [
                      "random",
                      "sequential"
                  ],
                  case_sensitive=False),
              help="Method for selecting source audio files")
@click.option('--event-counts', '-c',
              multiple=True,
              help="One or more values specifying a sequence of counts. These are used differently depending on the chosen strategy:"
                   "Interleave: Sequence of number of events to chunk together before interleaving starts"
                   "ShuffleInPlace: Sequence reflects the number of events to return from the current clip before moving onto the next.",
              type=click.IntRange(1, 15),
              default=[1])
@click.option('--output-prefix', '-p',
              type=str,
              help="Prefix to add to output files, in addition to the sequence number",
              default="output")
@click.option('--log-level', '-l',
              type=click.Choice(
                  [
                      "NONE",
                      "INFO",
                      "WARNING",
                      "ERROR"
                  ],
                  case_sensitive=False),
              default="ERROR")
def beat_shuffler(number_of_seqs: int,
                  generation_depth: int,
                  substitution_dir: str,
                  output: str,
                  source_dir: str,
                  seed: int,
                  trim: bool,
                  one_shot_mode: str,
                  strategy: str,
                  recurse_sub_dirs: bool,
                  normalize_durations: bool,
                  min_duration: int,
                  max_duration: int,
                  onset_method: str,
                  file_selection_method: str,
                  # event_selection_method: str,
                  event_counts: List[int],
                  output_prefix: str,
                  log_level: str) -> None:
    logger = Logger(-1 if log_level == "NONE" else 0 if log_level == "INFO" else 1 if log_level == "WARNING" else 2)
    click.echo(f"Iterating all audio files in folder {source_dir} with seed {seed}")
    logger.log(f"Using strategy {strategy}")
    rng = np.random.default_rng() if seed == -1 else np.random.default_rng(seed)
    file_chooser = FileChooser(rng, file_selection_method) 
    source_path = pathlib.Path(source_dir)
    source_files = get_audio_files(source_path, recurse_sub_dirs)
    substitution_path = pathlib.Path(substitution_dir) if substitution_dir else source_path
    substitution_files = get_audio_files(substitution_path, recurse_sub_dirs)

    logger.log(f"Got the following for chunk {event_counts}")

    if not source_files:
        click.echo("No audio files were found in the supplied source directory")
        exit(0)
    if not substitution_files:
        click.echo("No audio files were found in the supplied substitution directory")
        exit(0)

    options = {
        "normalize_durations": normalize_durations,
        "event_counts": event_counts
    }

    for i in range(number_of_seqs):
        selected_file = str(file_chooser.choose(source_files))
        click.echo(f"Selected file {selected_file}")
        source_clip = get_audio_clip(selected_file, rng.random(),
                                     rng.integers(min_duration, high=max_duration), trim, onset_method)
        click.echo(f"Got clip with {len(source_clip.events)} events")
        substitution_clips = get_substitution_clips(substitution_files, generation_depth, min_duration, max_duration,
                                                    one_shot_mode, source_clip, file_chooser, trim)
        result_events = generate_sequence(strategy, source_clip, substitution_clips, options)
        result = AudioClip(result_events)
        write_audio_clip(str(pathlib.Path(output, f"{output_prefix}-{i}")), result)


def generate_sequence(strategy: str,
                      source_clip: AudioClip,
                      substitution_clips: list[AudioClip],
                      options: dict) -> list[AudioEvent]:
    if strategy == "ShuffleByDuration":
        return strategies.shuffle_by_duration(source_clip, substitution_clips,
                                              normalize_durations=options["normalize_durations"])
    if strategy == "Interleave":
        return strategies.interleave(source_clip, substitution_clips, event_counts=options["event_counts"])

    if strategy == "InterleaveInPlace":
        return strategies.interleave_in_place(source_clip, substitution_clips, event_counts=options["event_counts"])

    return []


def get_substitution_clips(substitution_files,
                           generation_depth: int,
                           min_duration: int,
                           max_duration: int,
                           one_shot_mode: str,
                           source_clip: AudioClip,
                           file_chooser: FileChooser,
                           trim: bool) -> list[AudioClip]:

    clips = list()
    if one_shot_mode == "true":
        for _ in range(generation_depth):
            # num_events = rng.integers(source_events_length, source_events_length + round(source_events_length / 2))
            events: List[AudioEvent] = []
            for event in source_clip.events:
                filename: str = str(file_chooser.choose(substitution_files))
                events.append(get_audio_event(filename, 0, 44100, event.start, 
                                              event.duration, False))
            clips.append(AudioClip(events, source_clip.sample_rate))
    elif one_shot_mode == "long":
        for _ in range(generation_depth):
            events: List[AudioEvent] = []
            cur_event_ix = 0
            while cur_event_ix < len(source_clip.events):
                filename: str = str(file_chooser.choose(substitution_files))
                with AudioFile(filename) as file_to_slice:
                    file_length_samples = file_to_slice.frames
                # Long one shot mode is only enabled for files longer than a certain threshold
                if file_length_samples > ONE_SHOT_SLICE_THRESHOLD_SAMPLES:
                    num_slices = len(source_clip.events)
                    slice_length = int(math.floor(file_length_samples / num_slices))
                    if slice_length < SHORTEST_ONE_SHOT:
                        slice_length = SHORTEST_ONE_SHOT
                        num_slices = int(math.floor(file_length_samples / SHORTEST_ONE_SHOT))
                    num_slices = min(len(source_clip.events) - cur_event_ix, num_slices)
                    events.extend(get_slices(filename, cur_event_ix, num_slices, slice_length, source_clip))
                    cur_event_ix += len(events)
                    
                else:
                    if cur_event_ix >= len(source_clip.events):
                        break
                    ev = get_audio_event(filename, 
                                         0, 
                                         44100, 
                                         source_clip.events[cur_event_ix].start,
                                         source_clip.events[cur_event_ix].duration, 
                                         False)
                    events.append(ev)
                    cur_event_ix += 1
            clips.append(AudioClip(events, source_clip.sample_rate))
    else:    
        for _ in range(generation_depth):
            file: str = str(file_chooser.choose(substitution_files))
            duration = file_chooser.rng.integers(min_duration, high=max_duration)
            clips.append(get_audio_clip(file, file_chooser.rng.random(), duration, trim))

    return clips


def get_slices(filename: str, cur_event_ix: int, num_slices: int, slice_length: int, source_clip: AudioClip) -> List[AudioEvent]:
    slices: List[AudioEvent] = []
    for i in range(min(num_slices, MAX_NUMBER_OF_SLICES)):
        if cur_event_ix >= len(source_clip.events):
            break
        start_time = i * slice_length
        slices.append(get_audio_event(filename,
                                      start_time,
                                      start_time + min(44100, slice_length),
                                      source_clip.events[cur_event_ix].start,
                                      source_clip.events[cur_event_ix].duration,
                                      i > 0))
        cur_event_ix += 1
    return slices


def get_audio_event(filename: str,
                    start_time_samples: int,
                    end_time_samples: int,
                    map_to_onset_samples: int,
                    map_to_duration_samples: int,
                    should_fade_in: bool) -> AudioEvent:
    samples = []
    with AudioFile(filename) as file:
        if start_time_samples >= file.frames:
            start_time_samples = 0
        if end_time_samples >= file.frames:
            end_time_samples = file.frames - 1
        file.seek(start_time_samples)
        duration = end_time_samples - start_time_samples
        samples.extend(file.read(duration)[0, :])
    return AudioEvent(map_to_onset_samples, map_to_duration_samples, 0, samples, 0, should_fade_in)

# Could be nice to give audio events generated from one shots timing information (onset, duration), since it could be 
# useful for processes like remapping events from substitution clips into event slots from a source_clip

def get_audio_clip(filename: str,
                   start_offset_fraction: float,
                   duration_secs: int,
                   trim: bool,
                   aubio_method: str = "hfc") -> AudioClip:
    win_s = 512  # fft size
    hop_s = win_s // 2  # hop size
    onsets = []  # contains sample indexes to all onsets in the current clip, including start and end points
    all_samples = []
    samples_read = 0
    with AudioFile(filename) as file:
        duration_secs = helpers.clamp(duration_secs, 0, file.duration)
        if file.duration < SPLIT_THRESHOLD_IN_SECONDS:
            duration_secs = file.duration
            trim = False
        samplerate = file.samplerate
        start_offset = helpers.clamp(
            int(file.duration * start_offset_fraction),
            0,
            file.duration - duration_secs
        )
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
    if trim:
        events = events[1:-1]
    return AudioClip(events=events, sample_rate=samplerate)


def write_audio_clip(filename: str, clip: AudioClip):
    with AudioFile(f"{filename}.wav", "w", samplerate=clip.sample_rate, num_channels=clip.num_channels) as f:
        for event in clip.events:
            f.write(event.audio_data)


def get_audio_files(path, recurse) -> List[pathlib.Path]:
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
