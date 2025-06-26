# tab_to_notes

This script will convert [guitar tabs in ascii format](https://en.wikipedia.org/wiki/ASCII_tab) to note names like A B C G# etc. 

It is possible to preserve octaves and write note names like A4 B3 C2 G#6 etc. 

It will convert any text file and then replaces the tabs with lines of note names. Chords are written as a series of notes between brackets. E.g. `[F# G# B]`.

As the ascii tab format tends to be not that standard there are a few options to influence the processing and the results.

## Install

Just clone this repository or download the one script file `tab_to_notes.py`. As it uses only Python standard libraries it will run just about anywhere where Python is available.

The script will run as a command line tool under most Linux flavors. Windows users may use the windows command prompt to enter the `python` command followed by the path to the script file.

## Usage 

The script can be used in it's most simple form:

```
tab_to_notes.py tab_file_in_goes_here.txt result_file_out_goes_here.txt
```

Options can be added which are listed below. A summary of this can be obtained from the script itself by running:

```
tab_to_notes.py --help
```

### Options

### Help

option: `-h` or `--help`

Shows the help.

#### Octaves

option: `-c` or `--omit_octaves`

The result will have note names without indication in which octave the note is. Eg `E` instead of `E4`. All information given about the tuning of the instrument using the `--s..` options is ignored. The tuning is taken from the part of the line before the tuning_separator symbol. 

#### Tuning separator

option: `-t` or `--tuning_separator`

In an ascii tab there is a letter denoting the note a string is tuned to. Most often followed by a `|` and then the rest of the line. eg:

```
b|--------2p1------|
```

Sometimes another separator is used, or none at all like:

```
B---0----|----------0----|
```

In that case the tuning separator can be given as the option `-`, or whatever separator is used. A combination of multiple characters is possible. 

#### String tuning

options: `-s1` to `-s6`

To show the octave for each note it is necessary to know the exact note (including octave information) to which each string is tuned. For a standard guitar tuning that is (counting from the top string (the thinnest string)):

```
1: E4
2: B3
3: G3
4: D3
5: A3
6: E2
```

This tuning is the default tuning. Any string that is tuned differently should be given as an option. E.g. for a "drop D" the necessary option to give is: `-s6 D2`. The other strings need not be specified as these are in accordance to the defaults.

For a 4 string instrument the `-s5` and `-s6` options are ignored. For a 3 string instrument the `-s4` is ignored as well.

The tuning information written in the tab itself is ignored when the tuning options are used. If you want to use the tuning information in the tab itself (losing the octave information in the process) use the option `-c` or `--omit_octaves`.

#### Transpose

option: `-u` or `--transpose`

It is possible to transpose on the fly. The number of semitones to transpose with can be given, or the tuning of the instrument (e.g. `Bb` for a tenor saxophone).

#### Sharps or flats

options: `-s` or `--sharps`

options: `-f` or `--flats`

Use one of these options to have the results written with sharps or flats. Sharps will be used when none of these options are given.

#### Techniques

option: `-o` or `--omit_techniques`

This option suppresses the various techniques like hammer, bend, slide, etc in the result.

## Limitations

- Tremolo and harmonics notation will not work. The number used in these notations will show up as notes. These will show up even when the option  `--omit_techniques` is used.
- As the conversion does not preserve the spacing very well (especially not when converting chords) any indications above or below the tab will be probably in the wrong position after conversion.

