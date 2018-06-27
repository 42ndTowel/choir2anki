"""
A script to transform an annotated lilypond file into an anki deck.

Dependencies: abjad, lilypond, latex, timidity, lame, genanki,
"""

tmp_folder = "OUTPUT__TMP"
media_folder = "collection.media"

import re
import os
import shutil
import subprocess
import uuid
import genanki
import abjad
from string import Template
from choirnote import ChoirNote, mp3_template, png_template

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
            stderr=subprocess.DEVNULL) # For some reason, lilypond spams stderr
    subprocess.run(["timidity",
            "-Ow",
            source_file_name + ".midi"],
            stdout=subprocess.DEVNULL)
    subprocess.run(["lame",
            source_file_name + ".wav"],
            stdout=subprocess.DEVNULL)
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
            stdout=subprocess.DEVNULL)
    os.chdir(tmp_folder)
    subprocess.run(["latex",
            source_file_name + ".tex"],
            stdout=subprocess.DEVNULL)
    subprocess.run(["dvipng",
            source_file_name + ".dvi"],
            stdout=subprocess.DEVNULL)
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
    tempo = re.search(r"\\tempo ([\d|=]*)", midi)
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

def calculate_new_partial(partial, time, cur_notes):
    '''Calculate how much of the last measurement is left incompleted.'''
    parser = abjad.lilypondparsertools.LilyPondParser()
    # If there was a change in \time, that implies completed measures and we
    # thus have to look only at the part after the last change of \time
    if cur_notes.find('\\time') >= 0:
        partial = None
        time_before = time_now = None
        for time_now in re.finditer('\\\\time ([0-9]*/[0-9]*)', cur_notes):
            time_before = time_now
            time_now = time_now[1]
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
        # Compensating for the multiples workaround
        if partial.find('*') >= 0:
            partial, numerator = partial.split('*')
            partial = abjad.Duration(partial)
            partial *= int(numerator)
        else:
            partial = abjad.Duration.from_lilypond_duration_string(partial)
    time = abjad.Duration(time)

    if partial:
        notes_duration -= partial
    partial = time - (notes_duration % time)

    # Ended on a completed measurement. lilypond doesn't like \partial 0…
    if partial >= time:
        partial = None
    else:
        try:
            partial = partial.lilypond_duration_string
        except abjad.AssignabilityError: # lilypond understands multiples
            numerator = partial.numerator
            partial /= numerator
            partial = partial.lilypond_duration_string + '*' + str(numerator)
    return partial

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

def get_lyric_slice(lilypond_lyrics, slice_start, slice_end):
    '''Get the piece of lyrics that spans the given interval.'''
    lilypond_lyrics = remove_lilypond_comments(lilypond_lyrics)
    tokens = lilypond_lyrics.split()
    lyric_slice = []

    syllable_counter = 0
    for t in tokens:
        if syllable_counter == slice_end and not is_singable_syllable(t):
            lyric_slice += [t] # Add trailing '__'
        if slice_start <= syllable_counter and syllable_counter < slice_end:
            lyric_slice += [t]
        if is_singable_syllable(t):
            syllable_counter += 1
    lyric_slice = " ".join(lyric_slice)
    lyric_slice = lyric_slice.lstrip("[_|-| ]") # if start is in middle of word
    return lyric_slice

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
    return is_singable, next_is_tie, open_parantheses

def get_note_slice(lilypond_notes, slice_start, slice_end, open_parantheses=0):
    '''Get the stretch of notes thet spans the given interval.'''
    lilypond_notes = remove_lilypond_comments(lilypond_notes)
    tokens = lilypond_notes.split()
    note_slice = []

    singable_notes = 0
    next_is_tie = False
    for t in tokens:
        is_singable, next_is_tie, open_parantheses = \
                            is_singable_note(t, next_is_tie, open_parantheses)
        # TODO Incorporate intelligence -- Maximize simplicity of partials when
        # adding rests, thus making the resulting notes more natural
        if singable_notes == slice_end and not is_singable:
            note_slice += [t] # Add trailing rests, glissando, ties, …
        if slice_start <= singable_notes and singable_notes < slice_end:
            note_slice += [t]
        if is_singable:
            singable_notes += 1
    note_slice = " ".join(note_slice)
    return note_slice

def count_singable_notes(lilypond_notes, open_parantheses=0):
    '''Given a piece of music, count how many notes start in it.'''
    lilypond_notes = remove_lilypond_comments(lilypond_notes)
    tokens = lilypond_notes.split()

    singable_notes = 0
    next_is_tie = False
    for t in tokens:
        is_singable, next_is_tie, open_parantheses = \
                            is_singable_note(t, next_is_tie, open_parantheses)
        if is_singable:
            singable_notes += 1
    return singable_notes

def create_absolute_notes(lilypond_notes, relative):
    '''Turn relative lilypond notes into absolute lilypond notes.'''
    # Apparently, Christian speaks dutch…
    parser = abjad.lilypondparsertools\
                  .LilyPondParser(default_language='nederlands')
    abj_notes = parser(r"\relative "
                         + relative
                         + r" { " + lilypond_notes + r" }")
    normal_notes = abjad.LilyPondFormatManager.format_lilypond_value(abj_notes)
    normal_notes = normal_notes.split('\n')
    normal_notes = [n.strip() for n in normal_notes][1:-1] # '{' and '}'
    return normal_notes

def count_musical_tokens(lilypond_notes):
    '''Count the amount of notes, rests, etc.'''
    parser = abjad.lilypondparsertools\
                  .LilyPondParser(default_language='nederlands')
    return len(parser(r"\relative c {" + lilypond_notes + r"}"))


def create_normal_note_shards(lilypond_notes, relative,
                              split_symbol='%%'):
    '''Turn relative lilypond notes into note shards based on annotation.'''

    # To turn relative to absolute, we need entire context.
    # Apparently, Christian speaks dutch…
    parser = abjad.lilypondparsertools\
                  .LilyPondParser(default_language='nederlands')
    normal_notes = create_absolute_notes(lilypond_notes, relative)

    # Since the abjad parser throws away comments (i.e. our annotation),
    # we need the original notes to get the length of the shards
    notes = lilypond_notes.split(split_symbol)
    shard_lengths = [count_musical_tokens(n) for n in notes]

    # Combine notes in normalized form and the desired lengths
    note_shards = []
    comment_starts = ['%%%', '\\']
    for l in shard_lengths:
        shard, normal_notes = normal_notes[:l], normal_notes[l:]
        # The abjad parser turns some things (e.g. time changes) into comments.
        # Those don't count towards shard length
        cmnts_found = sum([x.startswith(y) for x in shard
                                           for y in comment_starts])
        cmnts_compensated = 0
        while cmnts_found != cmnts_compensated:
            shard_addition, normal_notes = (normal_notes[:cmnts_found],
                                            normal_notes[cmnts_found:])
            shard += shard_addition
            cmnts_found = sum([x.startswith(y) for x in shard
                                               for y in comment_starts])
            cmnts_compensated += len(shard_addition)
        note_shards += [" ".join(shard)]

    # Lastly, remove comments
    note_shards = [n.replace('%%%', '') for n in note_shards]
    return note_shards

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
    note_shards = create_normal_note_shards(notes, relative)

    anki_deck = genanki.Deck(1452737122, 'Physikerchor') # random but hardcoded
    anki_media = []

    is_first_part = 'True'
    qustn_png_id = ''
    qustn_png_no_lyrics_id = ''
    qustn_lyrics = ''
    qustn_mp3_id = ''
    num_seen_singable_notes = 0
    for shard_num in range(len(note_shards)):
        # First up, generate the 'answr' shard, which will be the answer…
        cur_notes = note_shards[shard_num]
        cur_options = r"\key {} \time {} {}".format(key, time, options)
        if partial:
            cur_options += r" \partial {}".format(partial)

        # Select the relevant piece of lyrics based on the amount of notes that
        # are actually singable (e.g. no rests, no portamento)
        num_lyric_relevant_notes = count_singable_notes(cur_notes)
        answr_lyrics = get_lyric_slice(lyrics, num_seen_singable_notes,
                         num_seen_singable_notes + num_lyric_relevant_notes)
        num_seen_singable_notes += num_lyric_relevant_notes

        dot_ly_file_name = fill_template_mp3(cur_notes,
                                             global_options=cur_options,
                                             tempo=tempo)
        answr_mp3_id = create_mp3(dot_ly_file_name,
                                  remove_source=True)
        dot_ly_file_name = fill_template_png(cur_notes,
                                             global_options=cur_options,
                                             clef=clef_dict[voice],
                                             lyrics=answr_lyrics)
        answr_png_id = create_png(dot_ly_file_name,
                                  remove_source=True)
        dot_ly_file_name = fill_template_png(cur_notes,
                                             global_options=cur_options,
                                             clef=clef_dict[voice])
        answr_png_no_lyrics_id = create_png(dot_ly_file_name,
                                            remove_source=True)

        # …then, fill the note with both 'qustn' shard and the 'answr' shard…
        anki_media += [answr_mp3_id, answr_png_id, answr_png_no_lyrics_id]
        anki_note = ChoirNote(model=ChoirNote.choir_model(),
                              fields=["{} - {:003n}".format(songtitle,
                                                            shard_num),
                                      songtitle,
                                      str(shard_num),
                                      is_first_part,
                                      qustn_png_id,
                                      qustn_png_no_lyrics_id,
                                      create_normal_lyrics(qustn_lyrics),
                                      qustn_mp3_id,
                                      answr_png_id,
                                      answr_png_no_lyrics_id,
                                      create_normal_lyrics(answr_lyrics),
                                      answr_mp3_id],
                              tags=tags)
        anki_deck.add_note(anki_note)

        # …find out if there was a change in time, key, or partial…
        new_key, new_time, _, _ = extract_key_time_partial(cur_notes)
        if new_key:
            key = new_key
        if new_time:
            time = new_time
        partial = calculate_new_partial(partial, time, cur_notes)

        # …cache the 'answr' shard, so it can become the next question.
        qustn_png_id = answr_png_id
        qustn_png_no_lyrics_id = answr_png_no_lyrics_id
        qustn_lyrics = answr_lyrics
        qustn_mp3_id = answr_mp3_id
        is_first_part = ''

    # Store away all our precious media
    if not os.path.isdir(media_folder):
        os.makedirs(media_folder)
    for file in anki_media:
        shutil.move(file, media_folder)

    # And export the deck
    anki_package = genanki.Package(anki_deck, media_files=anki_media)
    anki_package.media_files = [media_folder + "/" + f for f in anki_media]
    anki_package.write_to_file(songtitle + '.apkg')
    print('\n========\nSuccessfully generated ' + songtitle + '.apkg\n========')

if __name__ == "__main__":
    source_file_name = 'big_bang_theory_theme.ly'
    #source_file_name = 'cosmic_gall.ly'
    #source_file_name = 'meet_the_elements.ly'
    #source_file_name = 'schoepfung_metamorphosen.ly'

    # TODO
    # In Lilypond, use multine comments & tags: %{<NOTE>%}, %{<BEGIN_SPLIT>%}, …
    # Make the splitting rules based on the lyrics, not notes

    #print(create_absolute_notes("\\relative c'' { r1 %{NOTE%}\n\ng4g4( a fis d\ng4 fis) e \n%{NOTE%}\n r8 d\n }", "c'"))
    main(source_file_name)
