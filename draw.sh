#!/usr/bin/env bash
sfdp $1 -Nshape=point -Nwidth=0.01 -Epenwidth=0.1 -Goverlap=prism -Gsize=10! -Gsplines=curved -O -Tpng
