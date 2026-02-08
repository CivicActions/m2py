gbl2gbl ; Global-to-Global MERGE tests (combines mbyexam + inline session)
	; Session 1: mbyexam merge examples
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
	W "STEP 2",!
	MERGE ^A(1,2,3)=^B(5,6,7,8)
	ZWR ^A
	W "STEP 3",!
	K ^ABC
	SET ^ABC(1,5,6)="PASSVAL"
	SET ^ABC(1,5,3,4)="FAILVAL"
	SET ^ABC(1,2)="reset naked indicator"
	MERGE ^(3,4)=^(5,6)
	S ^("TESTNAKED")="OK"
	IF ^ABC(1,5,3,"TESTNAKED")'="OK"  W "FAIL",!
	ELSE  ZWR ^ABC
	; Session 2: global-to-global merge pattern
	KILL ^var1,^new1,^new2,^var1long,^var1longnamevariableswork4merge,^new1longnamevariableswork4merge
	set cnt=1
	f i=1001:1:1005 for j=1000:1:1005 set cnt=cnt+1 s ^var1(i,"ind"_i,j)="BBB"_cnt
	set ^var1(1003,"ind"_1003)="BBB"_1003
	zwr ^var1
	MERGE ^new2("NEWVAR")=^var1
	zwr ^new2
	MERGE ^new1("aaa","bbbb","cccc")=^var1(1003,"ind1003")
	zwr ^new1
	MERGE ^new1("kkk")=^var1(1001,"ind1001")
	zwr ^new1
	MERGE ^new1("aaa")=^var1(1004)
	zwr ^new1
	MERGE ^new1("aaa")=^var1(1005)
	zwr ^new1
	MERGE ^new1("lll")=^var1(1001,"ind1001")
	zwr ^new1
	MERGE ^new1("lll0")=^var1(1001,"ind1001",1002)
	MERGE ^new1("lll")=^var1(1003,"ind1003",1002)
	zwr ^new1
	set ^var1longnamevariableswork4merge(1,2,3)="long global to global"
	set ^var1long(1,2,3)="should  not use this shorter variable"
	MERGE ^new1longnamevariableswork4merge("aaa")=^var1longnamevariableswork4merge(1,2,3)
	MERGE:1 ^new1longnamevariableswork4merge("bbb")=^var1longnamevariableswork4merge(1,2,3)
	set longvar="^new1longnamevariableswork4merge"
	MERGE @longvar@("ccc")=^var1longnamevariableswork4merge(1,2,3)
	set localvar="naked reference into (1,2,""nakedx"")"
	set ^new1longnamevariableswork4merge(1,2,4)="tmp"
	MERGE ^("naked1")=localvar
	merge ^("naked2")=^("naked1")
	zwr ^new1longnamevariableswork4merge
	QUIT
