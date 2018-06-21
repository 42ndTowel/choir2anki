"""
A script to transform an annotated lilypond file into an anki deck.

Dependencies: abjad, lilypond, latex, timidity, lame, genanki,
"""

mp3_template_file_name = "mp3_template"
png_template_file_name = "png_template"
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
            source_file_name + ".wav"])
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
            source_file_name + ".ly"])
    os.chdir(tmp_folder)
    subprocess.run(["latex",
            source_file_name + ".tex"])
    subprocess.run(["dvipng",
            source_file_name + ".dvi"])
    os.chdir("..")
    shutil.move(tmp_folder + "/" + source_file_name + "1.png",
                "./" + png_name + ".png")
    shutil.rmtree(tmp_folder)

    if remove_source:
        os.remove(source_file_name + ".ly")

    return png_name + ".png"

def fill_template_mp3(notes, out_file_name="filled_mp3_template",
                      global_options="", tempo='4=100',
                      template_file_name=mp3_template_file_name):
    """Given a template, fill it with the approriate options."""
    options = {}
    options["notes"] = notes
    options["tempo"] = tempo
    options["global_options"] = global_options

    with open(template_file_name + ".ly") as mp3_template_file:
        with open(out_file_name + ".ly", 'w') as out_file:
            template = Template(mp3_template_file.read())
            out_file_content = template.substitute(options)
            out_file.write(out_file_content)
    return out_file_name

def fill_template_png(notes, out_file_name="filled_png_template", lyrics="",
                      global_options="", clef="bass",
                      template_file_name=png_template_file_name):
    """Given a template, fill it with the approriate options."""
    options = {}
    options["clef"] = clef
    options["notes"] = notes
    options["lyrics"] = lyrics
    options["global_options"] = global_options

    with open(template_file_name + ".ly") as png_template_file:
        with open(out_file_name + ".ly", 'w') as out_file:
            template = Template(png_template_file.read())
            out_file_content = template.substitute(options)
            out_file.write(out_file_content)
    return out_file_name

def extract_information_from_source(source_file_name, voice='bass'):
    '''Given a Physikerchor lilypond file, extract metadata, notes and lyrics'''
    with open(source_file_name) as input_file:
        input_string = input_file.read()

    # regexes ahead. If anything breaks, good luck!
    songtitle = re.search("\\\\header(?:[\s]*){(?:[.|\s]*)title = \"(.*)\"",
                          input_string)[1]
    global_options = re.search("global = {([^}]*)}",
                               input_string)[1]
    tempo = re.search("\\\\midi(?:[\s]*){(?:[.|\s]*)\\\\tempo ([^}]*)}",
                      input_string)[1]
    if re.search(voice + "Verse = \\\\lyricmode {([^}]*)}", input_string):
        lyrics = re.search(voice + "Verse = \\\\lyricmode {([^}]*)}",
                           input_string)[1]
    else: # Everybody sings the same
        lyrics = re.search("verse = \\\\lyricmode {([^}]*)}",
                           input_string)[1]
    rel_and_notes = re.search(voice + " = \\\\relative ([^={]*) {([^}]*)}",
                              input_string)

    songtitle = songtitle.strip()
    global_options = global_options.replace('\n', ' ').strip()
    tempo = tempo.strip()
    lyrics = lyrics.replace('\n', ' ').strip()
    relative = rel_and_notes[1]
    notes = rel_and_notes[2].replace('\\global', '').strip()
    return songtitle, global_options, relative, tempo, notes, lyrics, voice

def extract_specifics_from_global_options(global_options):
    key_pattern = re.search("\\\\key ([a-g])(?:[ ])(\\\\major|\\\\minor|)",
                            global_options)
    if key_pattern:
        key = key_pattern[1] + " " + key_pattern[2]
        global_options = global_options.replace('\\key ' + key, '')

    time_pattern = re.search('\\\\time ([0-9]*/[0-9]*)', global_options)
    if time_pattern:
        time = time_pattern[1]
        global_options = global_options.replace('\\time ' + time, '')

    partial_pattern = re.search('\\\\partial ([0-9]*)', global_options)
    if partial_pattern:
        partial = partial_pattern[1]
        global_options = global_options.replace('\\partial ' + partial, '')
    global_options = global_options.strip()
    return key, time, partial, global_options

def create_normal_lyrics(lilypond_lyrics):
    '''Form normal words from lilypond-tokenized lyrics.'''
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

def create_lyric_slice(lilypond_lyrics, slice_start, slice_end):
    '''Create a piece of lyrics that spans the given interval.'''
    tokens = lilypond_lyrics.split()
    lyric_slice = []

    syllable_counter = 0
    for t in tokens:
        if slice_start <= syllable_counter and syllable_counter < slice_end:
            lyric_slice += [t]
        if t != "--":
            syllable_counter += 1
    return " ".join(lyric_slice)

def count_singable_notes(lilypond_notes, open_parantheses=0):
    tokens = lilypond_notes.split()

    singable_notes = 0
    next_is_tie = False
    for t in tokens:
        if t.endswith(')'):
            open_parantheses -= 1
            # account for lyrics '__' that indicates holding a note
            singable_notes += open_parantheses == 0
        if next_is_tie:
            next_is_tie = t.endswith('~') # There might be consecutive ties
            continue # ties are sung as one note
        if t.endswith('~'):
            next_is_tie = True
        if open_parantheses == 0 and re.match('^[a-g]', t):
            singable_notes += 1
        if t.endswith('('):
            open_parantheses += 1
    return singable_notes

class ChoirNote(genanki.Note):
    def choir_model():
        model_id = '1544216877' # random string, hardcoded
        model_name = 'choir_model'
        fields = [
            {'name': 'title_and_part'},
            {'name': 'songtitle'},
            {'name': 'part_number'},
            {'name': 'is_first_part'},
            {'name': 'qustn_score'},
            {'name': 'qustn_score_no_lyrics'},
            {'name': 'qustn_lyrics'},
            {'name': 'qustn_mp3'},
            {'name': 'answr_score'},
            {'name': 'answr_score_no_lyrics'},
            {'name': 'answr_lyrics'},
            {'name': 'answr_mp3'},
        ]
        templates = [
            {
              'name': 'with_score',
              'qfmt': '''<span style="color:aqua; font-size:24px">
                            Keep singing
                        </span><br /><br />
                        {{#is_first_part}}
                            Beginning of “{{songtitle}}”
                        {{/is_first_part}}
                        {{^is_first_part}}
                        <img src="{{qustn_score}}">
                        <span style="display:none">[sound:{{qustn_mp3}}]</span>
                        {{/is_first_part}}
                        ''',
              'afmt': '''{{FrontSide}}
                        <hr id="answer">
                        <img src="{{answr_score}}">
                        <span style="display:none">[sound:{{answr_mp3}}]</span>
                        ''',
            },
            {
              'name': 'without_score',
              'qfmt': '''<span style="color:aqua; font-size:24px">
                            Keep singing
                        </span><br /><br />
                        {{#is_first_part}}
                            Beginning of “{{songtitle}}”
                        {{/is_first_part}}
                        {{^is_first_part}}
                        <span style="display:none">[sound:{{qustn_mp3}}]</span>
                        {{/is_first_part}}
                        ''',
              'afmt': '''{{FrontSide}}
                        <hr id="answer">
                        {{answr_lyrics}}
                        <span style="display:none">[sound:{{answr_mp3}}]</span>
                        ''',
            },
        ]
        css = '''.card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
            }
            '''
        return genanki.Model(model_id, model_name, fields, templates, css)

    @property
    def guid(self):
        # Don't hash random strings, only identifier: songtitle & part_number
        return genanki.guid_for(self.fields[1], self.fields[2])

def create_normal_note_shards(lilypond_notes, relative, split_symbol='%%'):
    '''Turn relative lilypond notes into note shards based on annotation.'''

    # To turn relative to absolute, we need entire context
    # Apparently, Christian speaks dutch…
    parser = abjad.lilypondparsertools\
                  .LilyPondParser(default_language='nederlands')
    abj_notes = parser(r"\relative "
                         + relative
                         + r" { " + lilypond_notes + r" }")
    normal_notes = abjad.LilyPondFormatManager.format_lilypond_value(abj_notes)
    normal_notes = normal_notes.split('\n')
    normal_notes = [n.strip() for n in normal_notes][1:-1] # '{' and '}'

    # Since the abjad parser throws away comments (i.e. our annotation),
    # we need the original notes to get the length of the shards
    notes = lilypond_notes.split(split_symbol)
    shard_lengths = [len(parser(r"\relative " # counts only notes & rests
                                + relative
                                + r" { " + n + r" }")) for n in notes]

    # Combine notes in normalized form and the desired lengths
    note_shards = []
    for l in shard_lengths:
        shard, normal_notes = normal_notes[:l], normal_notes[l:]
        # The abjad parser turns some things (e.g. time changes) into comments.
        # Those don't count towards shard length
        cmnts_found = sum([x.startswith('%%%') for x in shard])
        cmnts_compensated = 0
        while cmnts_found != cmnts_compensated:
            shard_addition, normal_notes = (normal_notes[:cmnts_found],
                                            normal_notes[cmnts_found:])
            shard += shard_addition
            cmnts_found = sum([x.startswith('%%%') for x in shard])
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

    partials = [4, 1, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
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
        cur_global_options = (global_options
                              + r"\partial "
                              + str(partials[shard_num]))

        # Select the relevant piece of lyrics based on the amount of notes that
        # are actually singable (e.g. no rests, no portamento)
        num_lyric_relevant_notes = count_singable_notes(cur_notes)
        answr_lyrics = create_lyric_slice(lyrics, num_seen_singable_notes,
                         num_seen_singable_notes + num_lyric_relevant_notes + 1)
        num_seen_singable_notes += num_lyric_relevant_notes

        dot_ly_file_name = fill_template_mp3(cur_notes,
                                             global_options=cur_global_options,
                                             tempo=tempo)
        answr_mp3_id = create_mp3(dot_ly_file_name,
                                  remove_source=True)
        dot_ly_file_name = fill_template_png(cur_notes,
                                             global_options=cur_global_options,
                                             clef=clef_dict[voice],
                                             lyrics=answr_lyrics)
        answr_png_id = create_png(dot_ly_file_name,
                                  remove_source=True)
        dot_ly_file_name = fill_template_png(cur_notes,
                                             global_options=cur_global_options,
                                             clef=clef_dict[voice])
        answr_png_no_lyrics_id = create_png(dot_ly_file_name,
                                            remove_source=True)

        # …then, fill the note with both 'qustn' shard and the 'answr' shard…
        anki_media += [answr_mp3_id, answr_png_id, answr_png_no_lyrics_id]
        anki_note = ChoirNote(model=ChoirNote.choir_model(),
                              fields=[songtitle + " - " + str(shard_num),
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

        # …lastly, cache the 'answr' shard, so it can become the next question.
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
    anki_package = genanki.Package(anki_deck)
    anki_package.media_files = [media_folder + "/" + f for f in anki_media]
    anki_package.write_to_file(songtitle + '.apkg')

if __name__ == "__main__":
    source_file_name = 'big_bang_theory_theme.ly'
    #source_file_name = 'cosmic_gall.ly'

    #notes_duration = abjad.inspect(abj_notes).get_duration()
    #upbeat = (notes_duration * 4) % 4

    main(source_file_name)
