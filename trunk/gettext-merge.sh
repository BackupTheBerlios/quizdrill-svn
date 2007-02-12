#!/bin/sh

intltool-extract --type=gettext/glade quizdrill.glade
xgettext -k_ -kN_ -o locale/quizdrill.pot *.py *.glade.h
for po_file in po/*.po
do
    msgmerge -U "$po_file" locale/quizdrill.pot
done
mv -f *.glade.h locale/
