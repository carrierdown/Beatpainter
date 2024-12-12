# BeatPainter

If you're anything like me, you probably have lots of audio samples lying around on your hard drive. You might even have spent hours meticulously organizing them into folders, only to forget about them later. This project provides a way to breathe new life into those samples by generating new loops based on the audio events in your source samples.

Looped material typically works well as source material, and will generally produce output that is also loopable. The material for substitution however can be anything you like, whether it's a directory full of one-shots (in which case the --one-shot-mode is of relevance to you), a set of loops, longer drone-type sounds (see --one-shot-mode long), or longer recordings like full tracks, mix stems or recorded jam sessions. The output is a new loop that is generated by replacing audio events in the source material with audio events from the substitution material.

## Example command

```
python3 main.py --source-dir <dir>\ 
    --substitution-dir <dir>\
    --recurse-sub-dirs\
    --seed 12341\
    --output <dir>
```

## Usage

```
Usage: main.py [OPTIONS]

Options:
  -n, --number-of-seqs INTEGER RANGE
                                  Number of sequences to generate  [default:
                                  1; 1<=x<=1000]
  -d, --generation-depth INTEGER RANGE
                                  Number of sequences to involve in the
                                  generation of a single loop  [default: 1;
                                  1<=x<=10]
  -sub, --substitution-dir DIRECTORY
                                  Path to directory containing audio files
                                  used to produce new loops based on the
                                  source audio. If left unspecified, the
                                  source directory is used for substitutions
                                  as well  [default: .]
  -o, --output DIRECTORY          Path to output directory  [default: .]
  -src, --source-dir DIRECTORY    Path to directory containing source audio
                                  files. These are then sliced and data for
                                  each slice is used to inform what audio
                                  events from the substitutions directory to
                                  replace them with  [default: .]
  -s, --seed INTEGER              Seed for random number generator  [default:
                                  (current time)]
  --trim                          Trim audio snippets to the nearest transient
  --one-shot-mode [long|true|false]
                                  Use one shots instead of loops as
                                  substitutions for loop generation. If long
                                  is specified, the special LongOneShotMode is
                                  enabled, which extracts several shorter one
                                  shots from longer sustained one shot sounds.
                                  [default: false]
  --strategy [Interleave|InterleavedShuffle|ShuffleByDuration|ShuffleByPitch]
                                  Strategy for generating audio sequences
                                  [default: ShuffleByDuration]
  --recurse-sub-dirs              Recurse into subdirectories when fetching
                                  substitution audio files
  --normalize-durations           Normalize durations of candidates so that
                                  they fall within the same range as the
                                  source durations, thus making for better
                                  matches with the source event durations
  --min-duration INTEGER RANGE    Minimum duration of extracted audio clips in
                                  seconds  [1<=x<=15]
  --max-duration INTEGER RANGE    Maximum duration of extracted audio clips in
                                  seconds  [2<=x<=30]
  --onset-method [default|energy|hfc|complex|phase|specdiff|kl|mkl|specflux]
                                  Aubio onset detection method  [default:
                                  specflux]
  --file-selection-method [random|sequential]
                                  Method for selecting source audio files
                                  [default: random]
  -c, --chunk-sizes INTEGER RANGE
                                  One or more values specifying how many
                                  events should be chunked together before
                                  processing occurs. Only used for interleave
                                  currently.  [1<=x<=15]
  --help                          Show this message and exit.
```