import genanki

mp3_template = r'''
\version "2.18.2"
\language "english"
\score {
  \new Voice = "my_notes" {
    ${global_options}
    \absolute {
      ${notes}
    }
  }
  \midi {\tempo ${tempo}}
}
'''

png_template = r'''
\documentclass{standalone}
\begin{document}
\begin{lilypond}
  \language "english"
  \layout {
    indent = #0
    line-width = #50000
  }
  \new Staff = "s" <<
    \new Voice = "b"{
      ${global_options}
      \clef ${clef}
      \absolute {
        ${notes}
      }
    }
    \new Lyrics \lyricsto "b" <<
      \lyricmode {
        ${lyrics}
      }
    >>
  >>
\layout{}
\end{lilypond}
\end{document}
'''

def embed_picture(picture_location):
  if picture_location == "":
    return ""
  return '<img src="{}">'.format(picture_location)

def embed_mp3(mp3_location):
  if mp3_location == "":
    return ""
  return '[sound:{}]'.format(mp3_location)

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
              'qfmt': '''
<span style="color:aqua; font-size:24px">
    Keep singing
</span><br /><br />
{{#is_first_part}}
    Beginning of “{{songtitle}}”
{{/is_first_part}}
{{^is_first_part}}
{{qustn_score}}
<span style="display:none">{{qustn_mp3}}</span>
{{/is_first_part}}
''',
              'afmt': '''
<span style="color:aqua; font-size:24px">
    Keep singing
</span><br /><br />
{{#is_first_part}}
    Beginning of “{{songtitle}}”
{{/is_first_part}}
{{^is_first_part}}
{{qustn_score}}
{{/is_first_part}}
<hr id="answer">
{{answr_score}}
<span style="display:none">{{answr_mp3}}</span>
''',
            },
            {
              'name': 'without_score',
              'qfmt': '''
<span style="color:aqua; font-size:24px">
    Keep singing
</span><br /><br />
{{#is_first_part}}
    Beginning of “{{songtitle}}”
{{/is_first_part}}
{{^is_first_part}}
{{qustn_lyrics}}
<span style="display:none">{{qustn_mp3}}</span>
{{/is_first_part}}
''',
              'afmt': '''
<span style="color:aqua; font-size:24px">
    Keep singing
</span><br /><br />
{{#is_first_part}}
    Beginning of “{{songtitle}}”
{{/is_first_part}}
{{^is_first_part}}
{{qustn_lyrics}}
{{/is_first_part}}
<hr id="answer">
{{answr_lyrics}}
<span style="display:none">{{answr_mp3}}</span>
''',
            },
        ]
        css = '''
.card {
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
