"""
A script to transform a lilypond file (or some input, not very clear yet) into an anki deck.

Dependencies: lilypond, latex, timidity, lame, genanki
"""

mp3_template_file_name = "mp3_template"
png_template_file_name = "png_template"
tmp_folder = "OUTPUT__TMP"
media_folder = "collection.media"

import os
import shutil
import subprocess
import uuid
import genanki
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
            stderr=subprocess.DEVNULL) # For some reasons, lilypond spams the error stream…
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

def create_png(source_file_name, png_name=None, tmp_folder=tmp_folder, remove_source=False):
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
    shutil.move(tmp_folder + "/" + source_file_name + "1.png", "./" + png_name + ".png")
    shutil.rmtree(tmp_folder)

    if remove_source:
        os.remove(source_file_name + ".ly")

    return png_name + ".png"

def fill_template_mp3(notes,
                      out_file_name="filled_mp3_template",
                      global_options="",
                      tempo='4=100',
                      template_file_name=mp3_template_file_name):
    """Given a template, fill it with the approriate options."""
    options = {}
    options["notes"] = notes
    options["tempo"] = tempo
    options["global_options"] = global_options

    with open(template_file_name + ".ly") as mp3_template_file, open(out_file_name + ".ly", 'w') as out_file:
        template = Template(mp3_template_file.read())
        out_file_content = template.substitute(options)
        out_file.write(out_file_content)
    return out_file_name

def fill_template_png(notes,
                      out_file_name="filled_png_template",
                      lyrics="",
                      global_options="",
                      clef="bass",
                      template_file_name=png_template_file_name):
    """Given a template, fill it with the approriate options."""
    options = {}
    options["clef"] = clef
    options["notes"] = notes
    options["lyrics"] = lyrics
    options["global_options"] = global_options

    with open(template_file_name + ".ly") as png_template_file, open(out_file_name + ".ly", 'w') as out_file:
        template = Template(png_template_file.read())
        out_file_content = template.substitute(options)
        out_file.write(out_file_content)
    return out_file_name

def create_normal_lyrics( lilypond_lyrics ):
    '''Forms normal words from lilypond-tokenized lyrics.'''
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


class ChoirNote(genanki.Note):
    def choir_model():
        model_id = '1544216877' # random string, hardcoded
        model_name = 'choir_model'
        fields = [
            {'name': 'title_and_part'},
            {'name': 'songtitle'},
            {'name': 'part_number'},
            {'name': 'is_first_part'},
            {'name': 'this_score'},
            {'name': 'this_score_no_lyrics'},
            {'name': 'this_lyrics'},
            {'name': 'this_mp3'},
            {'name': 'next_score'},
            {'name': 'next_score_no_lyrics'},
            {'name': 'next_lyrics'},
            {'name': 'next_mp3'},
        ]
        templates = [
            {
              'name': 'with_score',
              'qfmt': '''<span style="color:aqua; font-size:24px">Keep singing</span><br /><br />
                        {{#is_first_part}}Beginning of “{{songtitle}}”{{/is_first_part}}
                        {{^is_first_part}}
                        <img src="{{this_score}}">
                        <span style="display:none">[sound:{{this_mp3}}]</span>
                        {{/is_first_part}}
                        ''',
              'afmt': '''{{FrontSide}}
                        <hr id="answer">
                        <img src="{{next_score}}">
                        <span style="display:none">[sound:{{next_mp3}}]</span>
                        ''',
            },
            {
              'name': 'without_score',
              'qfmt': '''<span style="color:aqua; font-size:24px">Keep singing</span><br /><br />
                        {{#is_first_part}}Beginning of “{{songtitle}}”{{/is_first_part}}
                        {{^is_first_part}}
                        <span style="display:none">[sound:{{this_mp3}}]</span>
                        {{/is_first_part}}
                        ''',
              'afmt': '''{{FrontSide}}
                        <hr id="answer">
                        <span style="display:none">[sound:{{next_mp3}}]</span>
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
        return genanki.guid_for(self.fields[1], self.fields[2]) # Don't hash random strings, only identifier: songtitle & part_number

def main():
    '''Run the thing.

    TODO: Incorporate docopt to parse commandline options (but I'm far from that right now).
    '''
    clef = "bass"
    tempo = "4=100"
    global_options = "\\key g \\major \\time 4/4"
    '''
    How to get here (more) automatically:
    Put the duration suffix after each note to make it context-free
    Keep track of octave and put after each note to make it context-free
        - replace \\relative with \\absolute
    Count syllables to get lyric_shards automatically
    '''
    partials = [4, 1, 4, 1, 1]
    note_shards = [
            "g4 e4 e8 g d d e fis g4 fis e r r1",
            "g4( a fis d g4 fis) e",
            "r8 d e g g a b a g fis g g fis fis e4. r8",
            "e2( fis)",
            "r8 g fis d e e16 e~ e8 r",
            ]
    lyric_shards = [
            "Our whole u -- ni -- verse was in a hot, dense state",
            "ah __ wait!",
            "the earth be -- gan to cool the au -- to -- trophs be -- gan to drool",
            "ah __ ",
            "we built the py -- ra -- mids",
            ]

    anki_deck = genanki.Deck(1452737122, 'Physikerchor') # random but hardcoded
    anki_media = []

    # The first anki note is a special case, since we need to ask the question “How does song X start?”
    # Because of that, the extra field 'songtitle' gets supplied with the title and the note deals with that
    this_score = ''
    this_score_no_lyrics = ''
    this_lyrics = ''
    this_mp3 = ''
    songtitle = "Big Bang Theory Theme"
    is_first_part = 'True'
    tags = ['big_bang_theory', 'physikerchor']

    for i in range(len(note_shards)):
        notes = note_shards[i]
        lyrics = lyric_shards[i]
        cur_global_options = global_options + "\\partial " + str(partials[i])

        dot_ly_file_name = fill_template_mp3( notes, global_options=cur_global_options, tempo=tempo )
        mp3_id = create_mp3(dot_ly_file_name, remove_source=True)
        dot_ly_file_name = fill_template_png( notes, global_options=cur_global_options, clef=clef, lyrics=lyrics)
        png_id = create_png(dot_ly_file_name, remove_source=True)
        dot_ly_file_name = fill_template_png( notes, global_options=cur_global_options, clef=clef, lyrics="")
        png_no_lyrics_id = create_png(dot_ly_file_name, remove_source=True)

        anki_media += [mp3_id, png_id, png_no_lyrics_id]
        anki_note = ChoirNote(  model=ChoirNote.choir_model(),
                                fields=[songtitle + " - " + str(i),
                                            songtitle,
                                            str(i),
                                            is_first_part,
                                            this_score,
                                            this_score_no_lyrics,
                                            this_lyrics,
                                            this_mp3,
                                            png_id,
                                            png_no_lyrics_id,
                                            lyrics,
                                            mp3_id],
                                tags=tags)
        anki_deck.add_note(anki_note)

        this_score = png_id
        this_score_no_lyrics = png_no_lyrics_id
        this_lyrics = lyrics
        this_mp3 = mp3_id
        is_first_part = ''

    # Store away all our precious media
    if not os.path.isdir(media_folder):
        os.makedirs(media_folder)
    for file in anki_media:
        shutil.move(file, media_folder)

    anki_package = genanki.Package(anki_deck)
    anki_package.media_files = [media_folder + "/" + file for file in anki_media] # This doesn't seem to do anything
    anki_package.write_to_file('big_bang.apkg')

if __name__ == "__main__":
    main()
