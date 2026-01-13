ext3 ; Routine for $TEXT testing (US6, US7)
 ; This is line 1 - entry label comment
 W "Hello",!
 Q
 ;
TEXT1 ; Label for $TEXT tests
 W $T(+1),!  ; Write first line of current routine
 Q
 ;
TEXT0 ; Test $T(+0) - returns routine name
 W $T(+0),!
 Q
 ;
TEXTLABEL ; Test $T(LABEL) and $T(LABEL+N)
 W $T(TEXT1),!  ; Write TEXT1 label line
 W $T(TEXT1+1),!  ; Write line after TEXT1
 Q
 ;
TEXTEXT ; Test $T(+N^ROUTINE) and $T(LABEL^ROUTINE)
 W $T(+1^ext2),!  ; First line of ext2
 W $T(HELPER^ext2),!  ; HELPER label line in ext2
 Q
 ;
TEXTPAST ; Test $T past end of routine
 W $T(+999),!  ; Returns empty - past end
 Q
 ;
TEXTNEG ; Test $T with negative offset
 W $T(-1),!  ; Returns empty per YDB
 Q
 ;
DATA ; Embedded data for $TEXT retrieval
 ;;Line 1 of data
 ;;Line 2 of data
 ;;Line 3 of data
 Q
