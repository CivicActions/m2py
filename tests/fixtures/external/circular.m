circular ; Test circular routine calls
 ; Tests that A calls B calls A works correctly
 W "In circular",!
 D ^circularb
 W "Back in circular",!
 Q
 ;
RECUR ; Recursive call test
 S COUNT=$G(COUNT)+1
 I COUNT<3 D ^circular
 Q
 ;
CALLBACK ; Calls back to a routine that called us
 ; Used to test that mutual recursion works
 W "In CALLBACK, COUNT=",COUNT,!
 I COUNT<3 S COUNT=COUNT+1 D CALLBACK^circularb
 Q
