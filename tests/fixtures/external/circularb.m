circularb ; Second routine for circular call tests
 ; Called by circular.m
 W "In circularb",!
 Q
 ;
CALLBACK ; Mutual callback test
 W "In circularb CALLBACK, COUNT=",COUNT,!
 I COUNT<3 S COUNT=COUNT+1 D CALLBACK^circular
 Q
