# Importing your calibration films and creating the dose calibration curves

Retrieve the file paths of the calibration files and then import the images.

```mathematica
Clear["Global`*"]
```

```mathematica
calFilePath = SystemDialogInput["FileOpen"]
```
/Users/cptfinch/Documents/maths/gafchromic/my cal and uniformity films/img001.tif

```mathematica
calFile = Import[calFilePath]
```

The next step is to obtain the rectangular regions of interest from the imported images and to obtain a list of the regions in order of increasing dose. 

Incidentally, for best practice the calibration strips should be scanned during one scan; in other words all of the calibration strips should be placed on the scanner bed and scanned together. 

This removes any variation in the scanner response over successive scans - removing the variability in response caused by inter-scan variability.   

To select the regions of interest use the following steps:

Make the image below active by clicking on it; 

A number of options will appear along the bottom of image

Select the rectangular select tool 

Drag over the irradiated regions in order to create selected central rectangular regions of the irradiated part of each strip

Once all regions are selected, copy and paste the list to the right of `calRoiList=`

```mathematica
calRoiList = {, , , , , };

The following `ColorSeparate` function returns an n by 4 matrix instead of an n by 3 matrix. 

In other words there are four columns where I would have expected three columns, three since that corresponds to the three colour channels. 

The fourth column seems to be simply blank, so I am not sure where it comes from.

```mathematica
rgbCalList = Map[ColorSeparate, calRoiList]
```

Obtain here lists containing the calibration regions for respective colour channels. They are obtained by extracting them from the `rgbCalList`.

```mathematica
redCalRois = rgbCalList[[All, 1]]
```

```mathematica
greenCalRois = rgbCalList[[All, 2]]
```

```mathematica
blueCalRois = rgbCalList[[All, 3]]
```

A pure function `f` to obtain the mean value of a calibration region. 

```mathematica
f[x_] := Mean[Flatten[ImageData[x]]]
```

`f` is mapped over each calibration region to obtain a list of values corresponding to the mean pixel values of the calibration regions.

Pixel values are normalized to 1. i.e. 0..65535 is mapped to 0..1.

```mathematica
redCal = Map[f, redCalRois]
```

```mathematica
blueCal = Map[f, blueCalRois]
```

```mathematica
greenCal = Map[f, greenCalRois]
```

Sort the values in order corresonding from high pixel value to low pixel value. 

This corresponds to the order of low dose to high dose. 

```mathematica
redCalPixelValueLowToHighDose = Sort[redCal, Greater];
```

```mathematica
blueCalPixelValueLowToHighDose = Sort[blueCal, Greater];
```

```mathematica
greenCalPixelValueLowToHighDose = Sort[greenCal, Greater];
```

Input the doses given to the calibration strips in the order low to high dose. 

Here I have specified dose in Gy. 

Be sure to keep it in this format - each number separated by a comma and curly braces at each end.

```mathematica
cal1Doses = {0, 1/2, 1, 2, 4, 7, 9};
```

```mathematica
redCalPoints = Transpose[{cal1Doses, redCalPixelValueLowToHighDose}];
```

```mathematica
blueCalPoints = Transpose[{cal1Doses, blueCalPixelValueLowToHighDose}];
```

```mathematica
greenCalPoints = Transpose[{cal1Doses, greenCalPixelValueLowToHighDose}];
```

```mathematica
redLine = FindFit[redCalPoints, (r + s * D) / (t + D), {r, s, t}, D];
```

```mathematica
blueLine = FindFit[blueCalPoints, (r + s * D) / (t + D), {r, s, t}, D];
```

```mathematica
greenLine = FindFit[greenCalPoints, (r + s * D) / (t + D), {r, s, t}, D];
```

```mathematica
redLine = FindFit[redCalPoints, (r + s * D) / (t + D), {r, s, t}, D];
```

```mathematica
Show[ListPlot[redCalPoints, PlotStyle -> Red], Plot[{(r + s * D) /. redLine}, {D, 0, 15}], PlotStyle -> Red], 
ListPlot[blueCalPoints, PlotStyle -> Blue], Plot[{(r + s * D) /. blueLine, {D, 0, 15}}, PlotStyle -> Blue], 
ListPlot[greenCalPoints, PlotStyle -> Green], Plot[{(r + s * D) /. greenLine, {D, 0, 15}}, PlotStyle -> Green]]
```

```mathematica
ListPlot[redCalPoints, PlotStyle -> Red]
```

```mathematica
ListPlot[blueCalPoints, PlotStyle -> Blue]
```
Red
```mathematica
, Plot
```

(
r
+
s
*
D
```mathematica
) / (
```
t
+
D
```mathematica
) /
```
. redLine
,
D, 0, 15
,
```mathematica
ListPlot
blueCalPoints, PlotStyle
```
Blue
,
```mathematica
Plot
```

(
r
+
s
*
D
```mathematica
) / (
```
t
+
D
```mathematica
) /
```
. blueLine
,
D, 0, 15
,
```mathematica
ListPlot
greenCalPoints, PlotStyle
```
Green
,
```mathematica
Plot
```

(
r
+
s
*
D
```mathematica
) / (
```
t
+
D
```mathematica
) /
```
. greenLine
,
D, 0, 15

2
4
6
8
0.1
0.2
0.3
0.4
0.5
0.6
Converting Application films to dose using the Multi-
channel method
appFilmFilePath
=
```mathematica
SystemDialogInput
```
[
"FileOpen"
]
;
appFilm
=
```mathematica
Import
```
[
appFilmFilePath
]
;
redChannel
=
```mathematica
ColorSeparate
```
[
appFilm, "R"
]
;
blueChannel
=
```mathematica
ColorSeparate
```
[
appFilm, "G"
]
;
greenChannel
=
```mathematica
ColorSeparate
```
[
appFilm
,
"B"
]
;
redFit
[
dose
_ ] =
 
(
r
+
s
*
dose
)
 
 (
t
+
dose
)
```mathematica
 /
```
. redLine;
blueFit
[
dose
_ ] =
 
(
r
+
s
*
dose
)
 
 (
t
+
dose
)
```mathematica
 /
```
. blueLine;
greenFit
[
dose
_ ] =
 
(
r
+
s
*
dose
)
 
 (
t
+
dose
)
```mathematica
 /
```
. greenLine;
f
[
pixelR
_
, pixelB
_
, pixelG
_ ]
:
=
bestDose
```mathematica
/
```
. Last
[
```mathematica
Minimize
```
[
 
pixelR
-
redFit
[
bestDose
]
^ 2
+
 
pixelB
-
blueFit
[
bestDose
]
^ 2
+
pixelG
-
greenFit
[
bestDose
]
^ 2, bestDose
]]
;
```mathematica
ImageApply
```
[
f,
{
redChannel, blueChannel, greenChannel
}]
3

The following is test data
redPixel1
=
```mathematica
ImageData
```
[
redChannel
]
1, 1
bluePixel1
=
```mathematica
ImageData
```
[
blueChannel
]
1, 1
greenPixel1
=
```mathematica
ImageData
```
[
greenChannel
]
1, 1
croppedApp
=
ImageCrop
[
appFilm,
{
2, 2
}]
croppedFilm
[ _
width,
_
height
]
:
=
ImageCrop
appFilm,
width, height
4

smallerFilm
=
ImageCrop
appFilm,
{
2, 2
}
```mathematica
Map
```
[
l
,
```mathematica
ImageData
```
[
smallerFilm
,
{
2
}]]
```mathematica
ImageData::imgprop
```
:
 {
2
}
is not a valid property for an image.
```mathematica
Part::partd
: Part speci
```
cation 
1

is longer than depth of object.
```mathematica
Part::partd
: Part speci
```
cation 
2

is longer than depth of object.
```mathematica
Part::partd
: Part speci
```
cation 
3

is longer than depth of object.
General
::stop
: Further output of  
```mathematica
Part::partd
```
 will be suppressed during this calculation.
```mathematica
NMinimize::nnum
```
: The function value 

-
 0.895554
 +
 

1

2
+
 
-
 0.401758
 +
 

2

2
+
 
-
 0.747834
 +
 

3

2
 
is not a number at 
{
bestDose
}
 
=
 
{
-
 0.829053
}
.
```mathematica
NMinimize::nnum
```
: The function value 

-
 0.895554
 +
 

1

2
+
 
-
 0.401758
 +
 

2

2
+
 
-
 0.747834
 +
 

3

2
 
is not a number at 
{
bestDose
}
 
=
 
{
-
 0.829053
}
.
```mathematica
NMinimize::nnum
```
: The function value 

-
 0.895554
 +
 

1

2
+
 
-
 0.401758
 +
 

2

2
+
 
-
 0.747834
 +
 

3

2
 
is not a number at 
{
bestDose
}
 
=
 
{-
 0.829053
}
.
General
::stop
: Further output of  
```mathematica
NMinimize::nnum
```
 will be suppressed during this calculation.
ReplaceAll::reps
:
 {
bestDose
}
 is neither a list of replacement rules nor a valid dispatch table, and so cannot be
used for
replacing
.
```mathematica
Part::partw
: Part 2 of  
```
{
2
}
 does not exist.
```mathematica
Part::partw
: Part 3 of  
```
{
2
}
 does not exist.
ReplaceAll::reps
:
 {
bestDose
}
 is neither a list of replacement rules nor a valid dispatch table, and so cannot be
used for
replacing
.
```mathematica
ImageData::imginv
```
: Expecting an image or graphics instead of  bestDose
```mathematica
 /
```
 . bestDose.
```mathematica
ImageData
```
[
bestDose
```mathematica
/
```
. bestDose, bestDose
```mathematica
/
```
. bestDose
]
croppedFilm
[
2, 2
]
croppedFilm
[
2, 2
]
blahd
[ _
yep
]
:
=
yep
*
2
blahd
[
4
]
blahd
[
4
]
ImageCrop
[
appFilm,
{
2, 2
}]
l
[
pixel
_ ]
:
=
bestDose
```mathematica
/
```
. Last
[
```mathematica
Minimize
```
[
 
pixel
1
 -
redFit
[
bestDose
]
^ 2
+
pixel
2
 -
blueFit
[
bestDose
]
^ 2
+
pixel
3
 -
greenFit
[
bestDose
]
^ 2, bestDose
]]
;
5

```mathematica
ImageApply
```
l,
l
[
pixel
_ ]
:
=
bestDose
```mathematica
/
```
. Last
```mathematica
Minimize
```

pixel
1
 -
redFit
[
bestDose
]
^ 2
+
 
pixel
2
 -
blueFit
[
bestDose
]
^ 2
+
pixel
3
 -
greenFit
[
bestDose
]
^ 2, bestDose
<
5 && bestDose
>
2, bestDose
;
```mathematica
ImageData
```
[ %
207
]
```mathematica
ImageData
```
[ %
156
]
{
{{
0.371069, 0.447761, 0.310719
}
,
{
0.368612, 0.447364, 0.310491
}}
,
{{
0.370809, 0.448905, 0.311192
}
,
{
0.368566, 0.448508, 0.311604
}}}
Last
[ {
4, 3, 2
}]
l

0.3710688944838636`, 0.4477607385366598`, 0.31071946288242924`
3.38007
```mathematica
ImageApply
```
[ # *
6 &, croppedApp
]
```mathematica
Map
```
[
```mathematica
func, ImageData
```
[
croppedApp
]]
func

0.3710688944838636`, 0.4477607385366598`, 0.31071946288242924`
,
0.3686121919584955`, 0.4473640039673457`, 0.3104905775539788`

,
func

0.37080949111161976`, 0.44890516517891205`, 0.31119249256122683`
,
0.3685664148928054`, 0.44850843060959794`, 0.31160448615243763`

```mathematica
Map
```
[
```mathematica
func, ImageData
```
[
croppedApp
]
,
{
2
}]
{
func
[ {{
0.371069, 0.447761, 0.310719
}
,
{
0.368612, 0.447364, 0.310491
}}]
,
func
[ {{
0.370809, 0.448905, 0.311192
}
,
{
0.368566, 0.448508, 0.311604
}}]}
{
{
func
[ {
0.371069, 0.447761, 0.310719
}]
, func
[ {
0.368612, 0.447364, 0.310491
}]}
,
{
func
[ {
0.370809, 0.448905, 0.311192
}]
, func
[ {
0.368566, 0.448508, 0.311604
}]}}
croppedFilm
[
2, 2
]
croppedFilm
[
2, 2
]
6

```mathematica
Map
```
[
```mathematica
l, ImageData
```
[
croppedFilm
[
2, 2
]]
,
{
2
}]
```mathematica
ImageData::imginv
```
: Expecting an image or graphics instead of  croppedFilm
[
2, 2
]
.
```mathematica
Part::partd
: Part speci
```
cation 2

1

is longer than depth of object.
```mathematica
Part::partd
: Part speci
```
cation 2

2

is longer than depth of object.
```mathematica
Part::partd
: Part speci
```
cation 2

3

is longer than depth of object.
General
::stop
: Further output of  
```mathematica
Part::partd
```
 will be suppressed during this calculation.
```mathematica
NMinimize::nnum
```
: The function value 
(-
 0.895554
 +
 2

1

)
2
+ (-
 0.401758
 +
 2

2

)
2
+ (-
 0.747834
 +
 2

3

)
2
 is not a
number at 
{
bestDose
}
 
=
 
{
-
 0.829053
}
.
```mathematica
NMinimize::nnum
```
: The function value 
(-
 0.895554
 +
 2

1

)
2
+ (-
 0.401758
 +
 2

2

)
2
+ (-
 0.747834
 +
 2

3

)
2
 is not a
number at 
{
bestDose
}
 
=
 
{
-
 0.829053
}
.
```mathematica
NMinimize::nnum
```
: The function value 
(-
 0.895554
 +
 2

1

)
2
+ (-
 0.401758
 +
 2

2

)
2
+ (-
 0.747834
 +
 2

3

)
2
 is not a
number at 
{
bestDose
}
 
=
 
{
-
 0.829053
}
.
General
::stop
: Further output of  
```mathematica
NMinimize::nnum
```
 will be suppressed during this calculation.
ReplaceAll::reps
:
 {
bestDose
}
 is neither a list of replacement rules nor a valid dispatch table, and so cannot be
used for
replacing
.
ReplaceAll::reps
:
 {
bestDose
}
 is neither a list of replacement rules nor a valid dispatch table, and so cannot be
used for
replacing
.
```mathematica
ImageData::imginv
```
: Expecting an image or graphics instead of  croppedFilm
[
bestDose
```mathematica
 /
```
 . bestDose, bestDose
```mathematica
 /
```
 .
bestDose
]
.
```mathematica
ImageData
```
[
croppedFilm
[
bestDose
```mathematica
/
```
. bestDose, bestDose
```mathematica
/
```
. bestDose
]]
```mathematica
Map
```
[
```mathematica
l, ImageData
```
[
appFilm
]
,
{
2
}]
$Aborted
```mathematica
Map
```
[
```mathematica
l, ImageData
```
[
croppedApp
]
,
{
2
}]
3.3800694075890885`, 3.410693701660224`
,
3.373477673023367`, 3.395045616008423`
```mathematica
ImageData
```
[ %
213
]
{
{{
1., 1., 1.
}
,
{
1., 1., 1.
}}
,
{{
1., 1., 1.
}
,
{
1., 1., 1.
}}}
```mathematica
Minimize
```
{
1, 2, 3
}
2
2
```mathematica
ImageApply
```
f,
```mathematica
ImageApply::bdf
```
: Applying f  to 
{
0.371069, 0.447761, 0.310719
}
 does not yield a number or list of numbers.
```mathematica
ImageApply
```
f,
```mathematica
ImageApply
```
[
f,
{
croppedRed, croppedBlue, croppedGreen
}]
7

croppedRed
g
[
pixelR
_
, pixelB
_
, pixelG
_ ]
:
=
bestDose
```mathematica
/
```
. Last
[
```mathematica
Minimize
```
[
 
pixelR
-
redFit
[
bestDose
]
^ 2
+
 
pixelB
-
blueFit
[
bestDose
]
^ 2
+
pixelG
-
greenFit
[
bestDose
]
^ 2, bestDose
]]
blahd
[
fir
_
, sec
_
, thi
_ ] =
fir
+
sec
+
thi
3
g
[
0.5, 0.5, 0.5
]
1.01878
```mathematica
ImageApply
```
[
g,
{
croppedRed, croppedBlue, croppedGreen
}]
```mathematica
ImageApply::bdf
```
: Applying gto 
{
0.371069, 0.447761, 0.310719
}
 does not yield a number or list of numbers.
```mathematica
ImageApply
```
g,
,
,
```mathematica
 //
```
ImageAdjust
```mathematica
ImageData
```
{
{
0., 0.
}
,
{
0., 0.
}}
```mathematica
ImageData
```
{
{
0.376516, 0.375494
}
,
{
0.376974, 0.376226
}}
```mathematica
ImageApply
```
g,
```mathematica
ImageApply::bdf
```
: Applying gto0.3710688944838636`does not yield a number or list of numbers.
```mathematica
ImageApply
```
g,
```mathematica
ImageApply::bdf
```
: Applying gto0.3710688944838636`does not yield a number or list of numbers.
```mathematica
ImageApply
```
g,
,
,
```mathematica
ImageApply::nonopt
```
: Options expected
 (
instead of  
)
```mathematica
 beyond position2inImageApply
```
g,
,
,
. An
option
must be a rule or a list of rules.
```mathematica
ImageApply
```
g,
,
,
```mathematica
ImageData
```
{
{
0.376516, 0.375494
}
,
{
0.376974, 0.376226
}}
8

```mathematica
ImageApply
```
g,
,
,
```mathematica
ImageApply
```
[
g,
{
Image
[ {{
0.5, 0.8
}
,
{
0.5, 0.5
}}]
, Image
[ {{
0.5, 0.1
}
,
{
0.5, 0.5
}}]
, Image
[ {{
0.5, 0.3
}
,
{
0.5, 0.5
}}]}]
```mathematica
ImageData
```
{
{
1.01878, 0.407006
}
,
{
1.01878, 1.01878
}}
```mathematica
ImageApply
```
g,
,
,
```mathematica
ImageApply
ImageData
```
{
{
1., 1.
}
,
{
1., 1.
}}
```mathematica
ArrayPlot
```
[ {{
1., 1.
}
,
{
1., 1.
}}]
9

```mathematica
ImageApply
```
[
bestDose
```mathematica
/
```
. Last
[
```mathematica
Minimize
```
[
 
#
1
-
redFit
[
bestDose
]
^ 2
+
 
#
2
-
blueFit
[
bestDose
]
^ 2
+
 
#
3
-
greenFit
[
bestDose
]
^ 2,
bestDose
]
&
]
,
croppedRed
,
croppedBlue
,
croppedGreen
]
```mathematica
NMinimize::nnum
```
: The function value 
(-
 0.895554
 + #
 1
)
2
+ (-
 0.401758
 + #
 2
)
2
+ (-
 0.747834
 + #
 3
)
2
 is not a number
at 
{
bestDose
}
 
=
 
{
-
 0.829053
}
.
```mathematica
NMinimize::nnum
```
: The function value 
(-
 0.895554
 + #
 1
)
2
+ (-
 0.401758
 + #
 2
)
2
+ (-
 0.747834
 + #
 3
)
2
 is not a number
at 
{
bestDose
}
 
=
 
{
-
 0.829053
}
.
```mathematica
NMinimize::nnum
```
: The function value 
(-
 0.895554
 + #
 1
)
2
+ (-
 0.401758
 + #
 2
)
2
+ (-
 0.747834
 + #
 3
)
2
 is not a number
at 
{
bestDose
}
 
=
 
{
-
 0.829053
}
.
General
::stop
: Further output of  
```mathematica
NMinimize::nnum
```
 will be suppressed during this calculation.
ReplaceAll::reps
:
```mathematica
Minimize
```

-
1.93515
 +
 Times
[

2

]
Plus
[

2

]
+ #
 1
2
+
-
3.99831
 +
 Times
[

2

]
Plus
[

2

]
+ #
 2
2
+
-
3.84505
 +
 Times
[

2

]
Plus
[

2

]
+ #
 3
2
,
bestDose

is neither a list of replacement rules nor a valid dispatch table, and so
cannot be used for replacing.
```mathematica
ImageApply::nonopt
```
: Options expected
 (
instead of  
)
```mathematica
 beyond position2inImageApply
```
bestDose
```mathematica
 /
```
 .
```mathematica
Minimize
```
-
 Plus
[

2

]
 Power
 [
2

] + #
 1

2
+
 
-
 Plus
[

2

]
 Power
 [
2

] + #
 2

2
+
 
-
 Plus
[

2

]
 Power
 [
2

]
+ #
 3

2
, bestDose
,
,
,
. An option must be
a rule or a list of rules.
```mathematica
ImageApply
```
bestDose
```mathematica
/
```
.
```mathematica
Minimize
```
-
1.93515
+
0.0366878 bestDose
2.95594
+
bestDose
+ #
1
2
+
-
3.99831
+
0.0703032 bestDose
10.636
+
bestDose
+ #
2
2
+
-
3.84505
+
0.00711172 bestDose
5.96275
+
bestDose
+ #
3
2
, bestDose
,
,
,
```mathematica
ImageData
```
[
croppedRed
]
{
{
0.371069, 0.368612
}
,
{
0.370809, 0.368566
}}
redPixelbla
=
```mathematica
ImageData
```
[
redChannel
]
Dimensions
[
redPixelbla
]
{
685, 544
}
ImageAssemble
f
[
redPixel1, bluePixel1, greenPixel1
]
3.88121
10

croppedRed
=
ImageCrop
[
redChannel,
{
2, 2
}]
croppedBlue
=
ImageCrop
[
blueChannel,
{
2, 2
}]
croppedGreen
=
ImageCrop
[
greenChannel,
{
2, 2
}]
```mathematica
ImageData
```
[
croppedGreen
]
1, 1
```mathematica
MapThread
```
[
f,
{
croppedRed, croppedBlue, croppedGreen
}]
```mathematica
ImageData
```
[
croppedRed
]
0.310719
```mathematica
MapThread::mptd
```
: Object 
 at position
 {
2, 1
}
```mathematica
 inMapThread
```

f ,
 
,
,

 has only0of required 1 
dimensions.
```mathematica
MapThread
```
f,
,
,

{
{
0.371069, 0.368612
}
,
{
0.370809, 0.368566
}}
wat
=
```mathematica
ImageApply
```
[
f,
{
croppedRed, croppedBlue, croppedGreen
}]
```mathematica
ImageApply
```
ImageAdjust
[
wat
]
ImageHistogram
0.0
0.2
0.4
0.6
0.8
1.0
```mathematica
ImageData
```
[
wat
]
0.0
0.2
0.4
0.6
0.8
1.0
{
{
1., 1.
}
,
{
1., 1.
}}
11
