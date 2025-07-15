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

def fretsFromLine(line):
    """
    Creates an dict with the fret number and the position on 
    the line as index
    """
    
    result = {}
    # next line doesn't work for tremolo arm and harmonics
    for m in re.finditer(r"\d+", line):
        result[m.start()] = m.group(0)
    return result
    
def addTechniquesFromLine(line, fret_position_dict):
    """
    Adds the used techniques from the tab with position on the line
    as index.
    """
    # next line doesn't work for tremolo arm and harmonics
    for m in re.finditer(r"[^-\d+]+", line):
        if not m.start() in fret_position_dict.keys():
            fret_position_dict[m.start()] = m.group(0)
            
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
    Outputs the notes as a line
    """
    
    result = []
    for i in range(line_length):
        has_something = False
        chord = []
        for stringNote, notes in notedict.items():
            if i in notes.keys() \
            and notes[i]:
                note_name  = GetNote(   stringNote, 
                                        notes[i], 
                                        settings
                                    )
                chord.append(note_name)
        if len(chord) == 1:
            result.append(chord[0])
        elif len(chord) > 1:
            result.append(  
                str(settings["chord_start"]) + \
                str(settings["chord_separator"]).join(chord) + \
                str(settings["chord_end"])
            )
        else:
            result.append('-')
        
    return ['|' + ''.join(result) + '|','\n']

def proces_tabdict(tabdict, settings):
    result = []
    notedict, line_length = extract_notes(tabdict, settings)
    #print("Processing ascii tab with length: %s" % line_length)
    result.extend(format_notedict(  notedict, 
                                    line_length, 
                                    settings))
    return result

def proces_doc(doc, settings):
    """
    Proceses the document and returns a result document.
    
    Both documents asre lists of strings.
    """
    
    resultdoc = []
    tab_nr = 0
    tab = False
    tabdict = OrderedDict()
    string_nr = 0       # we count from top
    tuning = settings['tuning']
    for line in doc:
        if settings['tuning_separator'] in line:
            noteName = line.split(settings['tuning_separator'])[0].strip()
            if noteName.upper() in NOTES_SHARPS.keys() \
            or noteName.upper() in [x for x in NOTES_FLATS.keys().upper()]:
                tab = True
                string_nr = string_nr + 1
                if settings['write_octaves']:
                    tabdict[tuning[string_nr]] = line.split(
                        settings['tuning_separator'], 1)[1].strip()[:-1]
                else:
                    tabdict[noteName + str(string_nr)] = line.split(
                        settings['tuning_separator'], 1)[1].strip()[:-1]
            elif tab:
                resultdoc.extend(proces_tabdict(tabdict, settings))
                tab = False
                string_nr = 0
                tabdict = OrderedDict()
        else:
            # we just return all other lines
            if tab:
                resultdoc.extend(proces_tabdict(tabdict, settings))
                tab = False
                string_nr = 0
                tabdict = OrderedDict()
            resultdoc.append(line)
            
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
        "tab_file",
        type = pathlib.Path, 
        help = "A file containing ascii tab."
    )
    parser.add_argument(
        "result",
        type = pathlib.Path, 
        help = "A file to write the result as ascii text."
    )
    args = parser.parse_args()
    
    if args.transpose in TRANSPOSING_TABLE.keys():
        transpose = TRANSPOSING_TABLE[args.transpose]
    elif type(args.transpose) == str and args.transpose.isnumeric():
        transpose = int(args.transpose)
    else:
        transpose = args.transpose

    
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
        'tuning_separator': args.tuning_separator,
        'tuning':           {   1: args.s1,
                                2: args.s2,
                                3: args.s3,
                                4: args.s4,
                                5: args.s5,
                                6: args.s6 }
    }
    
    with open(args.tab_file) as f:
        doc = f.readlines()
    
    result = proces_doc(doc, settings)
    
    with open(args.result,'w') as f:
        f.writelines(result)


           

    
