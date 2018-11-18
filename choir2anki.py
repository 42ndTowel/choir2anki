"""
A script to transform an annotated lilypond file into an anki deck.

Dependencies: abjad, lilypond, latex, timidity, lame, genanki,
"""

tmp_folder = "OUTPUT__TMP"

import re
import os
import shutil
import subprocess
import uuid
import genanki
import abjad
import argparse
from string import Template
from choirnote import * # Barely any namespace pollution, I promise

def create_mp3(source_file_name, mp3_name=None, remove_source=False):
    """Generate an .mp3 and write it to disk.

    Given the file name of a (valid) lilypond file, write an .mp3 to the
    current directory and return the file name of the .mp3. In both cases, the
    trailing '.ly' and '.mp3' are omitted except in the return value.
    If no file name for the .mp3 is provided, a uuid is assigned.

    source_file_name -- the location of the .ly file, without file ending
    mp3_name -- the file name of the .mp3 (default: random uuid4)
    remove_source -- remove the lilypond after .mp3 is created (default: false)
    return -- the name of the created .mp3
    """

    if mp3_name == None:
        mp3_name = uuid.uuid4().hex

    subprocess.run(["lilypond",
            source_file_name + ".ly"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL) # For some reason, lilypond spams stderr
    subprocess.run(["timidity",
            "-Ow",
            source_file_name + ".midi"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    subprocess.run(["lame",
            source_file_name + ".wav"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    os.remove(source_file_name + ".midi")
    os.remove(source_file_name + ".wav")
    shutil.move(source_file_name + ".mp3", mp3_name + ".mp3")

    if remove_source:
        os.remove(source_file_name + ".ly")

    return mp3_name + ".mp3"

def create_png(source_file_name, png_name=None, tmp_folder=tmp_folder,
               remove_source=False):
    """Typeset music and write to disk as .png.

    Given the file name of a (valid) lilypond file, typeset the music on a
    single line, create a .png and write it to the current directory. Then,
    return the filename of the created .png.
    The trailing '.ly' and '.png' are omitted except in the return value.
    If no file name for the .png is provided, a uuid is assigned.

    source_file_name -- the location of the .ly file, without file ending
    png_name -- the file name of the .png (default: random uuid4)
    tmp_folder -- a folder for intermediary files (default: "OUTPUT__TMP")
    remove_source -- remove the lilypond after .mp3 is created (default: false)
    return -- the name of the created .png
    """

    if png_name == None:
        png_name = uuid.uuid4().hex

    subprocess.run(["lilypond-book",
            "-f",
            "latex",
            "--output",
            tmp_folder,
            source_file_name + ".ly"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    os.chdir(tmp_folder)
    subprocess.run(["latex",
            source_file_name + ".tex"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    subprocess.run(["dvipng",
            source_file_name + ".dvi"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    os.chdir("..")
    shutil.move(tmp_folder + "/" + source_file_name + "1.png",
                "./" + png_name + ".png")
    shutil.rmtree(tmp_folder)

    if remove_source:
        os.remove(source_file_name + ".ly")

    return png_name + ".png"

def fill_template_mp3(notes, out_file_name="filled_mp3_template",
                      global_options="", tempo='4=100'):
    """Given a template, fill it with the approriate options."""
    options = {}
    options["notes"] = notes
    options["tempo"] = tempo
    options["global_options"] = global_options

    with open(out_file_name + ".ly", 'w') as out_file:
        template = Template(mp3_template)
        out_file_content = template.substitute(options)
        out_file.write(out_file_content)
    return out_file_name

def fill_template_png(notes, out_file_name="filled_png_template", lyrics="",
                      global_options="", clef="bass"):
    """Given a template, fill it with the approriate options."""
    options = {}
    options["clef"] = clef
    options["notes"] = notes
    options["lyrics"] = lyrics
    options["global_options"] = global_options

    with open(out_file_name + ".ly", 'w') as out_file:
        template = Template(png_template)
        out_file_content = template.substitute(options)
        out_file.write(out_file_content)
    return out_file_name

def extract_information_from_source(source_file_name, voice='bass'):
    '''Given a Physikerchor lilypond file, extract metadata, notes and lyrics'''
    with open(source_file_name) as input_file:
        input_string = input_file.read()
    parser = abjad.lilypondparsertools.LilyPondParser()

    trigger_words = [r"\header", "global", r"\score",
                     voice + "Verse", "verse", voice]

    # The lilypond parser has very limited functionality for now. Thus,
    # we need to extract the relevant blocks of information manually but
    # can then feed them to the parser to be less error prone than regexes.
    def extract_from_first_level(trigger_words, input_string):
        trigger_words = dict(zip(trigger_words, ['']*len(trigger_words)))
        open_context = 0
        encountered_context_begin = False
        is_recording = False
        recording_word = ''
        # Keep whitespaces for line comments to keep working
        for t in re.split(r'(\s+)', input_string):
            open_context += t.count('{') - t.count('}')
            open_context += t.count('<<') - t.count('>>')
            if t in trigger_words.keys() and not is_recording and open_context <= 0:
                is_recording = True
                recording_word = t

            if is_recording: # Add everything, keep track of {…} or <<…>> blocks
                if t.count('{') >= 1 or t.count('<<') >= 1:
                    encountered_context_begin = True
                trigger_words[recording_word] += t

            if open_context <= 0 and encountered_context_begin: # Reset
                is_recording = False
                open_context = 0
                encountered_context_begin = False
                recording_word = ''
        return trigger_words

    clean_up = lambda kw, st : st.lstrip(kw).strip().strip('{|}').strip()

    information = extract_from_first_level(trigger_words, input_string)
    songtitle = parser(information[r"\header"]).title
    verse = "verse"
    if information[verse] == '':
        verse = voice + "Verse"
    lyrics = information[verse].split(r"\lyricmode")[1]
    lyrics = clean_up("=", lyrics)
    global_options = clean_up("global =", information["global"])
    score = clean_up(r"\score =", information[r"\score"])
    midi = extract_from_first_level([r"\midi"], score)[r"\midi"]
    tempo = re.search(r"\\tempo ([\d|=]*)", midi)[1]
    relative = re.search(r"\\relative ([a-g]['|,]*)", information[voice])[1]
    notes = clean_up(voice + r"= \relative " + relative, information[voice])
    notes = notes.lstrip(r"\global").strip()

    return songtitle, global_options, relative, tempo, notes, lyrics, voice

def extract_key_time_partial(options):
    '''Extract key, time, and anacrusis from global options'''
    key = None
    for key in re.finditer("\\\\key ([a-g])(?:[ ]|)(\\\\major|\\\\minor|)",
                            options):
        key = key[1] + " " + key[2]
    if key:
        options = options.replace('\\key ' + key, '')

    time = None
    for time in re.finditer('\\\\time ([0-9]*/[0-9]*)', options):
        time = time[1]
    if time:
        options = options.replace('\\time ' + time, '')

    partial = None
    for partial in re.finditer('\\\\partial ([0-9]*)', options):
        partial = partial[1]
    if partial:
        options = options.replace('\\partial ' + partial, '')

    options = options.strip()
    return key, time, partial, options

def encode_partial(abjad_duration):
    if abjad_duration == None:
        return None
    try:
        partial = abjad_duration.lilypond_duration_string
    except abjad.AssignabilityError: # lilypond understands multiples
        numerator = abjad_duration.numerator
        abjad_duration /= numerator
        partial = abjad_duration.lilypond_duration_string + '*' + str(numerator)
    return partial

def decode_partial(partial):
    if partial == None or partial == "":
        return abjad.Duration()
    # Compensating for the multiples workaround
    if partial.find('*') >= 0:
        partial, numerator = partial.split('*')
        partial = abjad.Duration(1, int(partial))
        partial *= int(numerator)
    else:
        partial = abjad.Duration.from_lilypond_duration_string(partial)
    return partial

def calculate_new_partial(partial, time, cur_notes):
    '''Calculate how much of the last measurement is left incompleted.'''
    parser = abjad.lilypondparsertools.LilyPondParser()
    # If there was a change in \time, that implies completed measures and we
    # thus have to look only at the part after the last change of \time
    if cur_notes.find('\\time') >= 0:
        partial = None
        time_before = time_now = None
        for time_new in re.finditer('\\\\time ([0-9]*/[0-9]*)', cur_notes):
            time_before = time_now
            time_now = time_new[1]
        split_notes = cur_notes.split('\\time ' + time_now)
        # If the \time change was last command, no notes after, pick time_before
        time = time_now
        if split_notes[-1] == '':
            split_notes = split_notes[-2].split('\\time ' + time_before)
            time = time_before
        cur_notes = split_notes[-1]

    # With or without change in \time, see how incomplete last measurement is
    abj_notes = parser(r'\new Voice { ' + cur_notes + r'}')
    notes_duration = abjad.inspect(abj_notes).get_duration()
    if partial:
        partial = decode_partial(partial)
    time = abjad.Duration(time)

    if partial:
        notes_duration -= partial
    partial = time - (notes_duration % time)

    # Ended on a completed measurement. lilypond doesn't like \partial 0…
    if partial >= time:
        partial = None
    else:
        partial = encode_partial(partial)
    return partial

def find_best_split(partial, time, left_note_shard, right_note_shard):
    '''Given two note shards, find the most natural splitting point.

    Rests are only expected on the end of the left shard, never at the
    beginning of the right shard.
    '''
    def contains_singable_note(lilypond_note_array, open_paranthesis):
        next_is_tie = False
        open_parantheses = 0
        for note in lilypond_note_array:
            is_singable, next_is_tie, open_parantheses =\
                is_singable_note(note, next_is_tie, open_parantheses)
            if is_singable:
                return True
        return False

    def partial_metric(abjad_duration):
        if abjad_duration == None:
            return 0
        return abjad_duration.numerator + abjad_duration.denominator - 1

    best_partial = calculate_new_partial(partial, time, left_note_shard)
    best_partial = decode_partial(best_partial)
    left_note_shard = left_note_shard.split()
    right_note_shard = right_note_shard.split()

    splitpoint = 0
    contains_singable = True
    while contains_singable and splitpoint <= len(left_note_shard):
        left_split, right_split = (left_note_shard[:splitpoint],
                                   left_note_shard[splitpoint:])
        # can't split in the middle of a slur
        open_paranthesis = "".join(left_split).count('(')
        open_paranthesis -= "".join(left_split).count(')')
        open_paranthesis += "".join(right_split).count('(') # don' move slurs!
        if right_split != []:
            starts_with_tie = right_split[0].endswith('~')
        if open_paranthesis == 0 and not starts_with_tie:
            contains_singable = contains_singable_note(right_split,
                                                       open_paranthesis)
        splitpoint += 1
    left_note_shard = left_split
    movable_tokens = right_split

    splitpoint = 0
    best_splitpoint = 0
    while splitpoint <= len(movable_tokens):
        left_candidate = left_note_shard + movable_tokens[:splitpoint]
        right_candidate = movable_tokens[splitpoint:] + right_note_shard
        if left_candidate[-1].endswith("\\time"): # '\time 12/8' -> += 2
            splitpoint += 2
            continue
        if left_candidate[-1].endswith("\\key"): # '\key e \major' -> += 2
            splitpoint += 2
            continue
        open_paranthesis = "".join(left_candidate).count('(')
        open_paranthesis -= "".join(left_candidate).count(')')
        ends_in_tie = left_candidate[-1].endswith('~')
        if open_paranthesis == 0 and not ends_in_tie:
            candidate_partial = calculate_new_partial(partial,
                                                      time,
                                                      " ".join(left_candidate))
            if candidate_partial != None:
                candidate_partial = decode_partial(candidate_partial)
            if partial_metric(candidate_partial) <= partial_metric(best_partial):
                best_partial = candidate_partial
                best_splitpoint = splitpoint
        splitpoint += 1

    left_note_shard = left_note_shard + movable_tokens[:best_splitpoint]
    right_note_shard = movable_tokens[best_splitpoint:] + right_note_shard
    left_note_shard = " ".join(left_note_shard)
    right_note_shard = " ".join(right_note_shard)
    new_left_partial = calculate_new_partial(partial, time, left_note_shard)
    return left_note_shard, right_note_shard, new_left_partial

def remove_lilypond_comments(string):
    '''Remove all comments from a given string'''
    string += '\n' # Last line workaround until $ matches the way it should.
    string = ''.join(re.split("(?<!%)%{(?:.|\s)*?%}", string)) # multiline %{…%}
    string = '\n'.join(re.split("%(?:.*?)\n", string)) # singleline %…\n
    return string

def create_normal_lyrics(lilypond_lyrics):
    '''Form normal words from lilypond-tokenized lyrics.'''
    lilypond_lyrics = remove_lilypond_comments(lilypond_lyrics)
    tokens = lilypond_lyrics.split()
    words = []

    join_next = False
    for t in tokens:
        if t == "__":
            continue
        if t == "--":
            join_next = True
        elif join_next:
            words[-1] += t
            join_next = False
        else:
            words += [t]
    return " ".join(words)

def is_singable_syllable(lilypond_lyric_piece):
    if lilypond_lyric_piece == "--":
        return False
    if lilypond_lyric_piece == "__":
        return False
    return  True

def count_singable_lyrics(lilypond_lyrics):
    '''Given a piece of lyrics, count how many syllables are sung in it.'''
    lilypond_lyrics = remove_lilypond_comments(lilypond_lyrics)
    tokens = lilypond_lyrics.split()

    syllable_counter = 0
    for t in tokens:
        if is_singable_syllable(t):
            syllable_counter += 1
    return syllable_counter

def is_singable_note(lilypond_note, next_is_tie, open_parantheses):
    this_is_tie = next_is_tie
    next_is_tie = False
    is_singable = False
    if open_parantheses == 0 and not this_is_tie:
        if re.match('^[a-g]', lilypond_note):
            is_singable = True
    if lilypond_note.endswith('~'):
        next_is_tie = True
    if lilypond_note.endswith(')'):
        open_parantheses -= 1
    if lilypond_note.endswith('('):
        open_parantheses += 1
    if lilypond_note.endswith('\\key'):
        next_is_tie = True
    return is_singable, next_is_tie, open_parantheses

def get_note_shards(lilypond_notes, lyric_shard_lengths):
    '''Get the note shards corresponding to the given lyric shards.

    All entries in lyric_shard_lengths must be strictly positive integers.
    '''
    lilypond_notes = remove_lilypond_comments(lilypond_notes)
    tokens = lilypond_notes.split()

    for x in lyric_shard_lengths:
        assert(x > 0)
    note_shards = []
    current_shard = []
    open_parantheses = 0
    next_is_tie = False
    singable_notes = 0
    for t in tokens:
        is_singable, next_is_tie, open_parantheses = \
                            is_singable_note(t, next_is_tie, open_parantheses)
        if singable_notes >= lyric_shard_lengths[0] and is_singable:
            singable_notes = 0
            note_shards += [current_shard]
            current_shard = []
            lyric_shard_lengths = lyric_shard_lengths[1:]
        current_shard += [t]
        if is_singable:
            singable_notes += 1
    if current_shard != []:
        note_shards += [current_shard]
    note_shards = [" ".join(shard) for shard in note_shards]
    return note_shards

def create_absolute_notes(lilypond_notes, relative):
    '''Turn relative lilypond notes into absolute lilypond notes.'''
    if relative == "":
        raise ValueError("relative needs to be set")
    # Apparently, Christian speaks dutch…
    lilypond_notes = remove_lilypond_comments(lilypond_notes)
    parser = abjad.lilypondparsertools\
                  .LilyPondParser(default_language='nederlands')
    abj_notes = parser(r"\relative "
                         + relative
                         + r" { " + lilypond_notes + r" }")
    normal_notes = abjad.LilyPondFormatManager.format_lilypond_value(abj_notes)
    normal_notes = normal_notes.split('\n')
    normal_notes = [n.strip() for n in normal_notes][1:-1] # '{' and '}'
    normal_notes = " ".join(normal_notes)
    for match in re.findall(r"(R.)( ?\* ?)([0-9]+)", normal_notes):
        to_replace = match[0] + match[1] + match[2]
        replace_with = " ".join([match[0]]*int(match[2]))
        normal_notes = normal_notes.replace(to_replace, replace_with)
    normal_notes = normal_notes.replace('%%%', '')
    return normal_notes

def main(source_file_name):
    '''Run the thing.'''
    clef_dict = {'bass':'bass',
                 'tenor':'bass',
                 'alto':'violin',
                 'soprano':'violin'}
    info = extract_information_from_source(source_file_name)
    songtitle, global_options, relative, tempo, notes, lyrics, voice = info
    tags = [songtitle, voice, 'physikerchor']
    tags = [x.lower().replace(' ', '_') for x in tags]

    key, time, partial, options = extract_key_time_partial(global_options)
    notes = create_absolute_notes(notes, relative)
    lyric_shards = re.split("(?<!%)%{(?:.|\s)*?%}", lyrics)
    lyric_shard_lengths = [count_singable_lyrics(x) for x in lyric_shards]
    print("Generating note shards...", end='\r')
    note_shards = get_note_shards(notes, lyric_shard_lengths)

    print("Looking for best splits...", end='\r')
    tmp_partial = partial
    for i in range(1, len(note_shards)):
        (note_shards[i-1],
            note_shards[i],
            tmp_partial) = find_best_split(tmp_partial,
                                           time,
                                           note_shards[i-1],
                                           note_shards[i])

    print("Starting note generation...", end='\r')
    anki_deck = genanki.Deck(1452737122, 'Physikerchor') # random but hardcoded
    anki_media = []

    is_first_part = 'True'
    qustn_png_id = ''
    qustn_png_no_lyrics_id = ''
    qustn_lyrics = ''
    qustn_mp3_id = ''
    feedback = 'Completed note {:003} of {:003}...'
    for shard_num, answr_lyrics in enumerate(lyric_shards):
        # First up, generate the 'answr' shard, which will be the answer…
        answr_notes = note_shards[shard_num]
        answ_options = r"\key {} \time {} {}".format(key, time, options)
        if partial:
            answ_options += r" \partial {}".format(partial)

        filename = songtitle.replace(' ', '_').lower()
        filename += "_{:003n}".format(shard_num)
        dot_ly_file_name = fill_template_mp3(answr_notes,
                                             global_options=answ_options,
                                             tempo=tempo)
        answr_mp3_id = create_mp3(dot_ly_file_name,
                                  mp3_name=filename,
                                  remove_source=True)
        dot_ly_file_name = fill_template_png(answr_notes,
                                             global_options=answ_options,
                                             clef=clef_dict[voice],
                                             lyrics=answr_lyrics)
        answr_png_id = create_png(dot_ly_file_name,
                                  png_name=filename,
                                  remove_source=True)
        dot_ly_file_name = fill_template_png(answr_notes,
                                             global_options=answ_options,
                                             clef=clef_dict[voice])
        answr_png_no_lyrics_id = create_png(dot_ly_file_name,
                                            png_name=filename + "_no_lyrics",
                                            remove_source=True)

        # …then, fill the note with both 'qustn' shard and the 'answr' shard…
        anki_media += [answr_mp3_id, answr_png_id, answr_png_no_lyrics_id]
        anki_note = ChoirNote(model=ChoirNote.choir_model(),
                              fields=["{} - {:003n}".format(songtitle,
                                                            shard_num),
                                      songtitle,
                                      str(shard_num),
                                      is_first_part,
                                      embed_picture(qustn_png_id),
                                      embed_picture(qustn_png_no_lyrics_id),
                                      create_normal_lyrics(qustn_lyrics),
                                      embed_mp3(qustn_mp3_id),
                                      embed_picture(answr_png_id),
                                      embed_picture(answr_png_no_lyrics_id),
                                      create_normal_lyrics(answr_lyrics),
                                      embed_mp3(answr_mp3_id)],
                              tags=tags)
        anki_deck.add_note(anki_note)

        # …find out if there was a change in time, key, or partial…
        new_key, new_time, _, _ = extract_key_time_partial(answr_notes)
        if new_key:
            key = new_key
        if new_time:
            time = new_time
        partial = calculate_new_partial(partial, time, answr_notes)

        # …cache the 'answr' shard, so it can become the next question.
        qustn_png_id = answr_png_id
        qustn_png_no_lyrics_id = answr_png_no_lyrics_id
        qustn_lyrics = answr_lyrics
        qustn_mp3_id = answr_mp3_id
        is_first_part = ''

        # Give a little feedback
        print(feedback.format(shard_num + 1, len(lyric_shards)), end='\r')

    # Export the deck
    anki_package = genanki.Package(anki_deck, media_files=anki_media)
    anki_package.write_to_file(songtitle + '.apkg')
    for file in anki_media: # All files are now inside the apkg
        os.remove(file)
    print('Successfully generated ' + songtitle + '.apkg')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="lilypond file to parse")
    args = parser.parse_args()
    main(args.filename)
