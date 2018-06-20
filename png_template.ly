\documentclass{standalone}
\begin{document}
\begin{lilypond}
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
	  	\new Lyrics \lyricsto "b" \lyricmode {
	  		${lyrics}
	  	}
  	>>
  	\layout{}
\end{lilypond}
\end{document}
