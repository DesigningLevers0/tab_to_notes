#!/usr/bin/env python3


import argparse
import math
import pathlib
import re
from collections import OrderedDict


TRANSPOSING_TABLE = {
        'Bb': 2,
        'Eb': 9,
        'F': 7,
        'A': 3
}

NOTES_SHARPS = {"C" : 0, "C#" : 1,  "D": 2, "D#" : 3, "E": 4, "F": 5, 
   "F#" : 6, "G":  7, "G#" : 8, "A": 9, "A#" : 10, "B": 11}

NOTES_FLATS = {"C" : 0, "Db" : 1,  "D": 2, "Eb" : 3, "E": 4, "F": 5, 
   "Gb" : 6, "G":  7, "Ab" : 8, "A": 9, "Bb" : 10, "B": 11}

SHARP_NAMES = dict([(v, k) for (k, v) in NOTES_SHARPS.items()])
FLAT_NAMES = dict([(v, k) for (k, v) in NOTES_FLATS.items()])

# Chord and interval abbreviations with descriptions
CHORD_ABBREVIATIONS = {
    "unison": ("1", "Unison (same note)"),
    "minor 2nd": ("m2", "Minor second"),
    "major 2nd": ("M2", "Major second"), 
    "minor 3rd": ("m3", "Minor third"),
    "major 3rd": ("M3", "Major third"),
    "perfect 4th": ("P4", "Perfect fourth"),
    "tritone": ("TT", "Tritone (augmented 4th/diminished 5th)"),
    "perfect 5th": ("P5", "Perfect fifth (Power chord)"),
    "minor 6th": ("m6", "Minor sixth"),
    "major 6th": ("M6", "Major sixth"),
    "minor 7th": ("m7", "Minor seventh"),
    "major 7th": ("M7", "Major seventh")
}

def build_filtered_legend(used_chord_types):
    """
    Build legend showing only chord types that appear in the document
    """
    if not used_chord_types:
        return ""
    
    legend_items = []
    
    # Add relevant interval abbreviations
    for chord_type in used_chord_types:
        for full_name, (abbrev, desc) in CHORD_ABBREVIATIONS.items():
            if abbrev in chord_type or full_name in chord_type:
                legend_items.append(f"{abbrev}: {desc}")
    
    # Add chord symbol explanations for any used chord types
    chord_symbols = []
    for chord_type in used_chord_types:
        if 'maj' in chord_type and 'maj=Major' not in chord_symbols:
            chord_symbols.append('maj=Major')
        if 'm' in chord_type and chord_type != 'maj' and 'm=Minor' not in chord_symbols:
            chord_symbols.append('m=Minor')
        if 'dim' in chord_type and 'dim=Diminished' not in chord_symbols:
            chord_symbols.append('dim=Diminished')
        if 'aug' in chord_type and 'aug=Augmented' not in chord_symbols:
            chord_symbols.append('aug=Augmented')
        if '5' in chord_type and '5=Power chord' not in chord_symbols:
            chord_symbols.append('5=Power chord')
        if 'sus' in chord_type and 'sus=Suspended' not in chord_symbols:
            chord_symbols.append('sus=Suspended')
    
    legend = "\n--- Chord/Interval Legend ---\n"
    if legend_items:
        legend += "\n".join(sorted(set(legend_items))) + "\n"
    if chord_symbols:
        legend += "Chord symbols: " + ", ".join(sorted(chord_symbols)) + "\n"
    
    return legend

def fretsFromLine(line):
    """
    Creates a dict with fret info including position, width, and value
    """
    
    result = {}
    # next line doesn't work for tremolo arm and harmonics
    for m in re.finditer(r"\d+", line):
        result[m.start()] = {
            'value': m.group(0),
            'start': m.start(),
            'end': m.end() - 1,
            'width': len(m.group(0))
        }
    return result

def group_by_timing(notedict):
    """
    Groups frets from all strings into timing buckets based on position overlap
    Returns dict of {timing_position: [(string, fret_info, uncertain), ...]}
    """
    
    # Collect all fret positions from all strings
    all_frets = []
    for string_note, frets in notedict.items():
        for pos, fret_info in frets.items():
            all_frets.append((string_note, pos, fret_info))
    
    # Sort by position for efficient grouping
    all_frets.sort(key=lambda x: x[1])
    
    timing_groups = {}
    
    for string_note, pos, fret_info in all_frets:
        # Find which timing group this fret belongs to
        group_found = False
        
        for timing_pos, group in timing_groups.items():
            # Check if this fret overlaps with any fret in this group
            for _, _, existing_fret, _ in group:
                # Check for position overlap (±1 tolerance)
                fret_range = range(fret_info['start'], fret_info['end'] + 1)
                existing_range = range(existing_fret['start'], existing_fret['end'] + 1)
                
                if (set(fret_range) & set(existing_range) or 
                    abs(fret_info['start'] - existing_fret['start']) <= 1 or
                    abs(fret_info['end'] - existing_fret['end']) <= 1):
                    
                    # Determine if this is uncertain alignment
                    uncertain = (fret_info['start'] < existing_fret['start'] and 
                               fret_info['width'] == 1 and existing_fret['width'] > 1)
                    
                    group.append((string_note, pos, fret_info, uncertain))
                    group_found = True
                    break
            
            if group_found:
                break
        
        if not group_found:
            # Create new timing group
            timing_groups[pos] = [(string_note, pos, fret_info, False)]
    
    return timing_groups
    
def addTechniquesFromLine(line, fret_position_dict):
    """
    Adds the used techniques from the tab with position on the line
    as index.
    """
    # next line doesn't work for tremolo arm and harmonics
    for m in re.finditer(r"[^-\d+]+", line):
        if not m.start() in fret_position_dict.keys():
            fret_position_dict[m.start()] = {
                'value': m.group(0),
                'start': m.start(),
                'end': m.end() - 1,
                'width': len(m.group(0))
            }
            
    return fret_position_dict

def GetNote(stringNote, fretNum, settings):
    """
    Gets the note if a number, otherwise return the character
    """
    
    if not fretNum.isnumeric():
        return fretNum

    base_octave = "".join([c for c in stringNote if c.isdigit()])
    if base_octave.isdigit():
        base_octave = int(base_octave)
    else:
        base_octave = 0

    baseNote = NOTES_SHARPS[stringNote.upper().replace(
                                                str(base_octave),'')]
    noteNum = baseNote + int(fretNum) + settings['transpose']
    fretNoteNum = noteNum % 12
    octave = math.floor(noteNum / 12) + base_octave
    
    if settings['write_sharps']:
        name = SHARP_NAMES[fretNoteNum]
    if settings['write_flats']:
        name = FLAT_NAMES[fretNoteNum]
    if settings['write_octaves']:
        name = name + str(octave)
        
    if settings['add_space']:
        if not ('#' in name or 'b' in name):
            name = name + ' '

    return name

def get_note_number(note_name):
    """
    Convert note name to semitone number (0-11), ignoring octave
    """
    # Remove octave numbers
    clean_note = ''.join([c for c in note_name if not c.isdigit()])
    
    if clean_note in NOTES_SHARPS:
        return NOTES_SHARPS[clean_note]
    elif clean_note in NOTES_FLATS:
        return NOTES_FLATS[clean_note]
    else:
        return None

def analyze_chord(notes):
    """
    Analyze a list of note names and return chord/interval identification
    Returns list of possible interpretations for educational value
    """
    if not notes or len(notes) < 2:
        return []
    
    # Get unique note numbers (remove octaves and duplicates)
    note_nums = []
    for note in notes:
        num = get_note_number(note)
        if num is not None and num not in note_nums:
            note_nums.append(num)
    
    note_nums.sort()
    
    if len(note_nums) == 1:
        return ["unison"]
    elif len(note_nums) == 2:
        return analyze_interval(note_nums)
    elif len(note_nums) >= 3:
        return analyze_triad(note_nums)
    
    return []

def analyze_interval(note_nums):
    """
    Analyze two-note interval
    """
    interval = (note_nums[1] - note_nums[0]) % 12
    
    interval_names = {
        0: "unison",
        1: "minor 2nd", 
        2: "major 2nd",
        3: "minor 3rd",
        4: "major 3rd", 
        5: "perfect 4th",
        6: "tritone",
        7: "perfect 5th",
        8: "minor 6th",
        9: "major 6th",
        10: "minor 7th",
        11: "major 7th"
    }
    
    interval_name = interval_names.get(interval, f"interval({interval})")
    if interval_name in CHORD_ABBREVIATIONS:
        return [CHORD_ABBREVIATIONS[interval_name][0]]  # Return abbreviation
    else:
        return [interval_name]

def analyze_triad(note_nums):
    """
    Analyze three or more note chord
    """
    results = []
    
    # Try each note as potential root
    for i, root in enumerate(note_nums):
        intervals = []
        for note in note_nums:
            if note != root:
                intervals.append((note - root) % 12)
        intervals.sort()
        
        # Check for common triad patterns
        root_name = SHARP_NAMES[root]
        
        if 3 in intervals and 7 in intervals:
            results.append(f"{root_name}m")
        elif 4 in intervals and 7 in intervals:
            results.append(f"{root_name}maj")
        elif 3 in intervals and 6 in intervals:
            results.append(f"{root_name}dim")
        elif 4 in intervals and 8 in intervals:
            results.append(f"{root_name}aug")
        elif 7 in intervals and len(intervals) == 1:
            results.append(f"{root_name}5")
        elif 4 in intervals and len(intervals) == 1:
            results.append(f"{root_name}(M3)")
        elif 3 in intervals and len(intervals) == 1:
            results.append(f"{root_name}(m3)")
    
    # If no standard patterns found, check for common intervals
    if not results:
        root_name = SHARP_NAMES[note_nums[0]]
        intervals = [(note - note_nums[0]) % 12 for note in note_nums[1:]]
        
        # Check for sus chords or other common patterns
        if 5 in intervals and 7 in intervals:  # sus4
            results.append(f"{root_name}sus4")
        elif 2 in intervals and 7 in intervals:  # sus2
            results.append(f"{root_name}sus2")
        else:
            # Show intervals in abbreviated form
            interval_abbrevs = []
            for interval in intervals:
                interval_names = {
                    1: "m2", 2: "M2", 3: "m3", 4: "M3", 5: "P4", 
                    6: "TT", 7: "P5", 8: "m6", 9: "M6", 10: "m7", 11: "M7"
                }
                interval_abbrevs.append(interval_names.get(interval, str(interval)))
            results.append(f"{root_name}({'+'.join(interval_abbrevs)})")
    
    return results

def extract_notes(tabdict, settings):
    """
    Extracts the notes and techniques from a tabdict
    """
    
    notedict = {}
    line_length = 0
    for stringNote, line in tabdict.items():
        if len(line) > line_length:
            line_length = len(line)
        notedict[stringNote] = fretsFromLine(line)
        if settings['write_techniques']:
            notedict[stringNote] = addTechniquesFromLine(
                                        line, notedict[stringNote])

    return (notedict, line_length)

def format_notedict(notedict, line_length, settings):
    """
    Outputs the notes as a line using timing-based grouping
    """
    
    # Get timing groups for all frets
    timing_groups = group_by_timing(notedict)
    
    # Sort timing groups by position
    sorted_positions = sorted(timing_groups.keys())
    
    result = []
    chord_analysis = []
    used_chord_types = set()  # Track chord types used in this line
    covered_positions = set()
    
    for pos in sorted_positions:
        if pos in covered_positions:
            continue
            
        group = timing_groups[pos]
        chord = []
        is_uncertain = False
        
        # Extract notes from this timing group
        for string_note, _, fret_info, uncertain in group:
            if uncertain:
                is_uncertain = True
            
            note_name = GetNote(string_note, fret_info['value'], settings)
            chord.append(note_name)
            
            # Mark all positions in this fret as covered
            for i in range(fret_info['start'], fret_info['end'] + 1):
                covered_positions.add(i)
        
        # Analyze chord if enabled
        if settings.get('chord_analysis', False):
            analysis = analyze_chord(chord)
            if analysis:
                # Show multiple interpretations separated by /
                chord_text = '/'.join(analysis[:2])
                chord_analysis.append(chord_text)
                # Track used chord types for legend
                for chord_type in analysis[:2]:
                    used_chord_types.add(chord_type)
            else:
                chord_analysis.append('-')
        
        # Format the chord output
        if len(chord) == 1:
            chord_str = chord[0]
        elif len(chord) > 1:
            chord_str = (str(settings["chord_start"]) + 
                        str(settings["chord_separator"]).join(chord) + 
                        str(settings["chord_end"]))
        else:
            chord_str = '-'
            
        # Add uncertainty marker if needed
        if is_uncertain:
            chord_str += '?'
            
        result.append(chord_str)
    
    # Build output lines
    output_lines = []
    
    # Add chord analysis line if enabled
    if settings.get('chord_analysis', False) and chord_analysis:
        analysis_line = ' '.join(chord_analysis)
        output_lines.append(analysis_line + '\n')
    
    # Add note line
    output_lines.append('|' + '--'.join(result) + '|' + '\n')
    
    if settings.get('chord_analysis', False):
        return output_lines, used_chord_types
    else:
        return output_lines

def proces_tabdict(tabdict, settings):
    result = []
    used_chord_types = set()
    notedict, line_length = extract_notes(tabdict, settings)
    #print("Processing ascii tab with length: %s" % line_length)
    if settings.get('chord_analysis', False):
        output_lines, chord_types = format_notedict(notedict, line_length, settings)
        result.extend(output_lines)
        used_chord_types.update(chord_types)
    else:
        # For non-chord analysis, format_notedict returns only lines
        output_lines = format_notedict(notedict, line_length, settings)
        if isinstance(output_lines, tuple):
            result.extend(output_lines[0])
        else:
            result.extend(output_lines)
    return result, used_chord_types

def proces_doc(doc, settings):
    """
    Proceses the document and returns a result document.

    Both documents asre lists of strings.
    """
    resultdoc = []
    all_used_chord_types = set()  # Track all chord types used in document
    tab_nr = 0
    tab = False
    tabdict = OrderedDict()
    string_nr = 0       # we count from top
    tuning = settings['tuning']
    for line in doc:
        if settings['tuning_separator'] in line:
            noteName = line.split(settings['tuning_separator'])[0].strip()
            if noteName.upper() in NOTES_SHARPS.keys() \
            or noteName.upper() in [x.upper() for x in NOTES_FLATS.keys()]:
                tab = True
                string_nr = string_nr + 1
                if settings['write_octaves']:
                    tabdict[tuning[string_nr]] = line.split(
                        settings['tuning_separator'], 1)[1].strip()[:-1]
                else:
                    tabdict[noteName + str(string_nr)] = line.split(
                        settings['tuning_separator'], 1)[1].strip()[:-1]
            elif noteName == "" and line.startswith(settings['tuning_separator']):
                # Handle tablature without string tuning indicators (assumes standard tuning)
                tab = True
                string_nr = string_nr + 1
                if string_nr <= 6:  # Limit to 6 strings max
                    if settings['write_octaves']:
                        tabdict[tuning[string_nr]] = line.split(
                            settings['tuning_separator'], 1)[1].strip()[:-1]
                    else:
                        tabdict[tuning[string_nr] + str(string_nr)] = line.split(
                            settings['tuning_separator'], 1)[1].strip()[:-1]
            elif tab:
                tab_result, chord_types = proces_tabdict(tabdict, settings)
                resultdoc.extend(tab_result)
                all_used_chord_types.update(chord_types)
                tab = False
                string_nr = 0
                tabdict = OrderedDict()
        else:
            # we just return all other lines
            if tab:
                tab_result, chord_types = proces_tabdict(tabdict, settings)
                resultdoc.extend(tab_result)
                all_used_chord_types.update(chord_types)
                tab = False
                string_nr = 0
                tabdict = OrderedDict()
            resultdoc.append(line)
    
    # Process any remaining tab data at end of file
    if tab:
        tab_result, chord_types = proces_tabdict(tabdict, settings)
        resultdoc.extend(tab_result)
        all_used_chord_types.update(chord_types)
    
    # Add filtered legend if chord analysis is enabled
    if settings.get('chord_analysis', False):
        filtered_legend = build_filtered_legend(all_used_chord_types)
        if filtered_legend:
            resultdoc.append(filtered_legend)
            
    return resultdoc

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
        description = "Converts text files containing ascii tabs as "
                      "used by guitar players and the like to "
                      "note names as used by e.g. saxophonists.")
    parser.add_argument(    
        "-t", 
        "--tuning_separator", 
        default = '|',
        help = "The symbol used to separate the note name indicating " 
               "how the string is tuned from the rest of the tab line. "
               "Default |."
    )
    parser.add_argument(    
        "-u", 
        "--transpose", 
        default = 0,
        help = "Transpose the result with the given number of "
               "semitones. Alternatively a note (Eb, Bb, F, A) "
               "indicating instrument tuning can be used."
    )
    parser.add_argument(    
        "-s", 
        "--sharps", 
        help = "Write note names with sharps.",
        action = "store_true"
    )
    parser.add_argument(    
        "-f", 
        "--flats", 
        help = "Write note names with flats.",
        action="store_true"
    )
    parser.add_argument(
        "-s1",
        help = "Tuning of string nr 1 (counting from top). Default E4.",
        default = "E4"
    )
    parser.add_argument(
        "-s2",
        help = "Tuning of string nr 2 (counting from top). Default B3.",
        default = "B3"
    )
    parser.add_argument(
        "-s3",
        help = "Tuning of string nr 3 (counting from top). Default G3.",
        default = "G3"
    )
    parser.add_argument(
        "-s4",
        help = "Tuning of string nr 4 (counting from top). Default D3.",
        default = "D3"
    )
    parser.add_argument(
        "-s5",
        help = "Tuning of string nr 5 (counting from top). Default A3.",
        default = "A3"
    )
    parser.add_argument(
        "-s6",
        help = "Tuning of string nr 6 (counting from top). Default E2.",
        default = "E2"
    )
    parser.add_argument(
        '--dropd',
        help = "Use drop D tuning (equivalent to -s6 D2).",
        action="store_true"
    )
    parser.add_argument(
        '-c',
        '--omit_octaves',
        help = "Omit writing octaves with the notes. All tuning "
               "information in the -s.. options is ingnored.",
        action="store_true"
    )
    parser.add_argument(    
        "-o", 
        "--omit_techniques", 
        help = "Omit writing techniques as in tab.",
        action="store_true"
    )
    parser.add_argument(
        '--chord_analysis',
        help = "Add chord/interval analysis above note output.",
        action="store_true"
    )
    parser.add_argument(
        "tab_file",
        type = pathlib.Path, 
        help = "A file containing ascii tab."
    )
    parser.add_argument(
        "result",
        type = pathlib.Path, 
        help = "A file to write the result as ascii text.",
        nargs = '?'
    )
    args = parser.parse_args()
    
    if args.transpose in TRANSPOSING_TABLE.keys():
        transpose = TRANSPOSING_TABLE[args.transpose]
    elif type(args.transpose) == str and args.transpose.isnumeric():
        transpose = int(args.transpose)
    else:
        transpose = args.transpose

    # Handle drop D tuning
    s6_tuning = "D2" if args.dropd else args.s6
    
    settings = {
        "chord_start":      '[',
        "chord_end":        ']',
        "chord_separator":  '_',
        'add_space':        False,
        'transpose':        transpose,
        'write_sharps':     not args.flats,
        'write_flats':      args.flats,
        'write_techniques': not args.omit_techniques,
        'write_octaves':    not args.omit_octaves,
        'chord_analysis':   args.chord_analysis,
        'tuning_separator': args.tuning_separator,
        'tuning':           {   1: args.s1,
                                2: args.s2,
                                3: args.s3,
                                4: args.s4,
                                5: args.s5,
                                6: s6_tuning }
    }
    
    with open(args.tab_file) as f:
        doc = f.readlines()
    
    result = proces_doc(doc, settings)
    
    if args.result:
        with open(args.result,'w') as f:
            f.writelines(result)
    else:
        for line in result:
            print(line, end='')
