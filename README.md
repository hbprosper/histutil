# histutil
A collection of simple utilities based on the CERN package ROOT.

Classes:
```
  TimeLeft
  Scribe
  PercentileCurve
  Table
  Ntuple
  BDT
``` 
Functions:
```
  nameonly(filename)
  setStyle()
  expo(x, fmt="%4.2f", code="#")
  addTitle(title)
  percentiles(point, percent)
  getarg(args, key, d)
  mkpline(xx, y1, y2, boundary, **args)
  mkhist1(histname, xtitle, ytitle, nbinx, xmin, xmax, **args)
  mkhist2(histname, xtitle, ytitle, nbinx, xmin, xmax, nbiny, ymin, ymax, **args)
  mkgraph(x, y, xtitle, ytitle, xmin, xmax, **args)
  mkcdf(hist, minbin=1)
  mkroc(name, hsig, hbkg, lcolor=kBlue, lwidth=2, ndivx=505, ndivy=505)
  mklegend(x, y, xw, yw)
```
Scripts:
```
	writeTMVA.py <TMVA-C++-class> <classifier-name>
	makeTstruct.py variables-file [treename=Analysis]
```
