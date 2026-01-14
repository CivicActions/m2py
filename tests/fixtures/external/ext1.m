ext1 ; Main test routine for external calls
 ; Tests D ^ROUTINE (US1), D LABEL^ROUTINE (US2), G ^ROUTINE (US3)
 ; Variable visibility (US4), $$FUNC^ROUTINE (US5)
 ;
 ; Entry point - basic external DO call test
 D ^ext2
 W "Back in ext1",!
 Q
 ;
DOLABEL ; Test D LABEL^ROUTINE pattern
 D HELPER^ext2
 W "After HELPER",!
 Q
 ;
GOEXT ; Test G ^ROUTINE - transfers permanently
 W "Start",!
 G ^ext2
 W "Never printed",!  ; This should never execute
 Q
 ;
GOLABEL ; Test G LABEL^ROUTINE
 G HELPER^ext2
 W "Never",!
 Q
 ;
VARTEST ; Test variable visibility (US4)
 S X=100
 D ^ext2
 W "X after call: ",X,!
 Q
 ;
NEWTEST ; Test NEW hiding caller variables
 S X=100
 D HIDESVAR^ext2
 W "X after NEW: ",X,!
 Q
 ;
EXTRTEST ; Test external extrinsic function (US5)
 S RESULT=$$ADD^ext2(3,5)
 W "Result: ",RESULT,!
 Q
 ;
MULTI ; Test multiple calls to same routine
 D ^ext2
 D ^ext2
 D ^ext2
 W "Done",!
 Q
 ;
CALLBOTH ; Test calling different labels in same routine
 D A^ext2
 D B^ext2
 Q
 ;
GOOFFSET ; Test GOTO with label+offset
 G A+1^ext2
 W "Never",!
 Q
 ;
DOOFFSET ; Test DO with label+offset
 D A+1^ext2
 W "After offset call",!
 Q
 ;
ABSOFFSET ; Test absolute line offset D +N^ROUTINE
 D +4^ext2
 W "After abs offset",!
 Q
 ;
GOABSOFF ; Test absolute line offset G +N^ROUTINE
 G +4^ext2
 W "Never",!
 Q
