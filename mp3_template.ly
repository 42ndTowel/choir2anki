\version "2.18.2"
\score {
  \new Voice = "my_notes" {
  	${global_options}
  	\absolute {
  		${notes}
  	}
  }
  \midi {\tempo ${tempo}}
}