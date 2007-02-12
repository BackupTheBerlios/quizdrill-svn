#!/bin/sh

LANGUAGES="de"

for po_lang in $LANGUAGES
do
    echo -n "Processing $po_lang"
    mkdir -p "locale/$po_lang/LC_MESSAGES/"
    msgfmt "po/$po_lang.po" -o "locale/$po_lang/LC_MESSAGES/quizdrill.mo"
    echo "."
done
