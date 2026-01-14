ext2 ; Called routine for external call tests
 ; Entry label - called by D ^ext2
 W "In ext2",!
 Q
 ;
HELPER ; Helper label - called by D HELPER^ext2
 W "In HELPER",!
 Q
 ;
A ; Label A for multi-label tests
 W "A-Line1",!
 W "A-Line2",!
 Q
 ;
B ; Label B for multi-label tests
 W "B",!
 Q
 ;
MODVAR ; Modifies caller's variable (US4)
 S X=999
 Q
 ;
HIDESVAR ; Uses NEW to hide caller's variable
 N X
 S X=999
 Q
 ;
CREATEVAR ; Creates a new variable for caller
 S NEWVAR=42
 Q
 ;
ADD(A,B) ; Extrinsic function - returns sum (US5)
 Q A+B
 ;
DOUBLE(N) ; Extrinsic function - returns double
 Q N*2
 ;
TESTVAR ; Returns extrinsic with $TEST check
 I 0  ; Sets $TEST to 0
 Q 1
