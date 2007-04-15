#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, Adam Schmalhofer <schmalhof@users.berlios.de>
# Developed at http://quizdrill.berlios.de/
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from os import listdir, spawnl, P_WAIT, makedirs
from os.path import basename, normpath
from glob import glob

def make_mo_gettext():
    """
    Calls 'msgfmt' from GNU gettext to genearte object files (.mo) from
    the translation files (.po).
    """
    print "Generating gettext mo files: "
    po_files = 'po/*.po'
    mo_base_dir = 'locale/%s/LC_MESSAGES/'
    conv_program = 'msgfmt'

    for lang_file in glob(po_files):
        language = basename(lang_file)[:-3]
        mo_dir = mo_base_dir % language
        print language + " "
        try:
            makedirs(mo_dir)
        except OSError, inst:
            if inst.strerror != 'File exists':
                print 'Warning: ', inst.file, inst.strerror, 'ignoring.'
        print lang_file, "+", mo_dir    # debugging
        # normalize path for windows #
        lang_file_norm = normpath(lang_file)
        mo_dir_norm = normpath(mo_dir)
        #
        spawnl(P_WAIT, conv_program, lang_file_norm, "-o", mo_dir_norm)
    print "done"


make_mo_gettext()
