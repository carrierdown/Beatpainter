# BeatPainter

```
Usage: main.py [OPTIONS]

Options:
  -n, --number-of-seqs INTEGER RANGE
                                  Number of sequences to generate  [default:
                                  1; 1<=x<=1000]
  -d, --generation-depth INTEGER  Number of sequences to involve in the
                                  generation of a single loop  [default: 1]
  -s, --substitution-dir DIRECTORY
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
  --help                          Show this message and exit.
```