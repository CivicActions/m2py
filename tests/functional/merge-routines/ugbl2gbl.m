ugbl2gbl ; Unicode global-to-global MERGE test (combined mbyexam + ugbl2gbl.input)
 ; Session 1: From mbyexam.m
 KILL ^A,^B
 W "STEP 1",!
 SET ^A(1,2)="First"
 SET ^A(1,2,4)="Second"
 SET ^B(5,6,7)="Third"
 SET ^B(5,6,8)="Fourth"
 SET ^B(5,6,7,8,1)="Fifth"
 SET ^B(5,6,7,8,9)="Sixth"
 MERGE ^A(1,2)=^B(5,6,7)
 ZWR ^A
 ;
 W "STEP 2",!
 MERGE ^A(1,2,3)=^B(5,6,7,8)
 ZWR ^A
 ;
 W "STEP 3",!
 K ^ABC
 SET ^ABC(1,5,6)="PASSVAL"
 SET ^ABC(1,5,3,4)="FAILVAL"
 SET ^ABC(1,2)="reset naked indicator"
 MERGE ^(3,4)=^(5,6)
 S ^("TESTNAKED")="OK"
 IF ^ABC(1,5,3,"TESTNAKED")'="OK"  W "FAIL",!
 ELSE  ZWR ^ABC
 ;
 ; Clean up session 1 globals before session 2
 KILL ^A,^B,^ABC
 KILL ^var1,^new1,^new2,^var1long,^var1longnamevariableswork4merge,^new1longnamevariableswork4merge
 ;
 ; Session 2: From u_inref/ugbl2gbl.input
 set cnt=1
 f i=1001:1:1005 for j=1000:1:1005 set cnt=cnt+1 s ^var1(i,"ｉnd"_i,j)="αβγδε"_cnt
 set ^var1(1003,"ｉnd"_1003)="αβγδε"_1003
 zwr ^var1
 MERGE ^new2("NEWVAR")=^var1
 zwr ^new2
 MERGE ^new1("ａａa","ｂｂｂｂ","ｃｃｃｃ")=^var1(1003,"ｉnd1003")
 zwr ^new1
 MERGE ^new1("kkk")=^var1(1001,"ｉnd1001")
 zwr ^new1
 MERGE ^new1("ａａａ")=^var1(1004)
 zwr ^new1
 MERGE ^new1("ａａａ")=^var1(1005)
 zwr ^new1
 MERGE ^new1("我能吞下玻璃而不伤身体")=^var1(1001,"ｉnd1001")
 zwr ^new1
 MERGE ^new1("我能吞下玻璃而不伤身体"_$C(0))=^var1(1001,"ｉnd1001",1002)
 zwr ^new1
 MERGE ^new1("我能吞下玻璃而不伤身体")=^var1(1003,"ｉnd1003",1002)
 zwr ^new1
 set ^var1longnamevariableswork4merge(1,2,3)="long global to global"
 set ^var1long(1,2,3)="should  not use this shorter variable"
 MERGE ^new1longnamevariableswork4merge("aaa")=^var1longnamevariableswork4merge(1,2,3)
 MERGE:1 ^new1longnamevariableswork4merge("bbb")=^var1longnamevariableswork4merge(1,2,3)
 set longvar="^new1longnamevariableswork4merge"
 MERGE @longvar@("αβγδε.ＡＢＣＤＥＦＧ.我能吞下玻璃而傷")=^var1longnamevariableswork4merge(1,2,3)
 set localvar="naked reference into (1,2,""nakedx"")"
 set ^new1longnamevariableswork4merge(1,2,4)="tmp"
 MERGE ^("naked1")=localvar
 merge ^("naked2")=^("naked1")
 merge ^("①②③④⑤⑥⑦⑧")=^("naked2")
 merge ^("我能吞下玻璃而不伤身体")=^("①②③④⑤⑥⑦⑧")
 zwr ^new1longnamevariableswork4merge
 QUIT
