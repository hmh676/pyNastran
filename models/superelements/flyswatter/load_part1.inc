$ file - loadprt1.dat
$ loads on s.e. 1
$
$ LOAD CASE 1 - PRESSURE LOAD
$
PLOAD2,101,-1.,18,THRU,42
$
$ LOAD CASE 2 - 2 POINT LOADS AT CORNERS
$
FORCE,201,93,,2.,0.,0.,1.
$
$ LOAD CASE 3 - OPPOSING POINT LOADS AT CORNERS
$
FORCE,301,93,,2.,0.,0.,1.
$