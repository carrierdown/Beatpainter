import pathlib
import click
import random
import aubio
from dataclasses import dataclass
from typing import List
from pedalboard_native.io import AudioFile


# Files longer than this will have a random clip extracted from it
SPLIT_THRESHOLD_IN_SECONDS = 15


@dataclass
class AudioEvent:
    start: int
    duration: int
    pitch: int
    audio_data: List[float]
    rms: float
    should_fade_in: bool = True


@dataclass
class AudioClip:
    events: List[AudioEvent]


# Console.WriteLine($"  --min-duration <seconds>    : Minimum duration of audio snippets in seconds (default: {defaults.MinDurationSeconds})");
# Console.WriteLine($"  --max-duration <seconds>    : Maximum duration of audio snippets in seconds (default: {defaults.MaxDurationSeconds})");
# Console.WriteLine( "  --onset-method <method>     : Aubio onset detection method (default: specflux) One of default|energy|hfc|complex|phase|specdiff|kl|mkl|specflux");
# Console.WriteLine( "  --file-selection-method <method> : Method for selecting source audio files (default: random) One of random|sequential");


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
    source_files = list([p for pattern in ["*.wav", "*.mp3", "*.aiff"]
                         for p in source_path.rglob(pattern)
                         if not p.name.startswith('._')])
    if not source_files:
        click.echo("No audio files were found in the supplied directory")
        exit(0)
    selected_file = random.choice(source_files)
    click.echo(f"Selected file {selected_file}")

    # collect next source file
    # collect substitution clips in the amount generation_depth
    clip = get_audio_clip(str(selected_file), random.random() * .9, random.randint(min_duration, max_duration), onset_method)
    click.echo(f"Got clip with {len(clip.events)} events")


def get_audio_clip(filename: str,
                   start_offset_fraction: float,
                   duration_secs: int,
                   aubio_method: str = "hfc") -> AudioClip:
    win_s = 512  # fft size
    hop_s = win_s // 2  # hop size
    onsets = []
    all_samples = []
    samples_read = 0
    with AudioFile(filename) as f:
        clip_size_fraction = duration_secs / f.duration
        start_offset_fraction *= (.975 - clip_size_fraction)
        start_offset = 0
        if clip_size_fraction < .9:
            start_offset = int(f.duration * start_offset_fraction)
        o = aubio.onset(aubio_method, samplerate=f.samplerate, hop_size=hop_s, buf_size=win_s)
        start_offset_samples = int(start_offset * f.samplerate)
        num_samples = int(duration_secs * f.samplerate)
        f.seek(start_offset_samples)
        while samples_read < num_samples:
            samples = f.read(hop_s)
            samples_read += len(samples[0, :])
            # we only keep left channel
            all_samples.extend(samples[0, :])
            if len(samples[0, :]) < hop_s:
                break
            if o(samples[0, :]):
                onsets.append(o.get_last())
    onsets.insert(0, 0)
    onsets.append(samples_read)
    events: List[AudioEvent] = list()
    for ix, onset in enumerate(onsets[0:-1]):
        duration = onsets[ix + 1] - onset
        events.append(AudioEvent(onset, duration, 0, all_samples[onset:onset + duration], 0, True))
    return AudioClip(events)


if __name__ == "__main__":
    beat_shuffler()
