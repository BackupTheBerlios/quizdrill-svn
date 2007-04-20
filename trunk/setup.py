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

from setuptools import setup
import sys

from os import listdir, spawnlp, P_WAIT, makedirs
from os.path import basename, normpath
from glob import glob

def make_mo_gettext():
    """
    Calls 'msgfmt' from GNU gettext to genearte object files (.mo) from
    the translation files (.po).

    Note: As this function usese the $PATH variable (with spawnlp) it doesn't
      work under Windows.
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
        # normalize path for windows #
        lang_file_norm = normpath(lang_file)
        mo_dir_norm = normpath(mo_dir)
        #
        mo_file = mo_dir_norm + "/quizdrill.mo"
        #print conv_program, lang_file, "-o", mo_file    # debugging
        spawnlp(P_WAIT, conv_program, conv_program, lang_file_norm, "-o", 
                mo_file)
    print "done"

def make_setup():
    """
    The setuptools setup packaging for eggs, Python Cheese Shop 
    registration and distutils install.
    """
    setup(name='quizdrill', 
            version='0.2.0-rc1',
            # prevents *_scripts from working when installed by debian package
            # much higher minimum pygtk version is needed than written
            #install_requires=['pygtk > 2.0'],
            license='GNU General Public License',
            platforms=['any'],
            # descriptions should be kept in sync with debian/control,
            # the berlios project page, the wiki-homepage and 
            # (in the future) freshmeat.
            description='A learning-by-testing to excess program.',
            long_description="""A learning-by-testing program to learn quickly, 
                mostly memorizing tasks like vocabulary. Quizdrill supports
                multiple choice, simple quiz as well as flashcard testing.
                """,
            author='Adam Schmalhofer',
            author_email='schmalhof@users.berlios.de',
            url='http://quizdrill.berlios.de/',
            package_dir={'quizdrill': 'src'},
            packages=['quizdrill'],
            package_data={'quizdrill': ['data/quizdrill.glade']},
            data_files=[('quizzes', ['quizzes/deu-fra.drill', 
                'quizzes/eng-fra.drill', 'quizzes/eng-jpn.drill', 
                'quizzes/eng-jpn_romaji.drill', 'quizzes/eng-svd.drill', 
                'quizzes/fra_verb.drill']),
                ('po', ['po/de.po']),
                ('doc', ['README', 'TODO', 'GPL-2', 'Changes'])],
            entry_points={
                'console_scripts': [ 'quiz_builder = quizdrill.builder:build' ],
                'gui_scripts': [ 'quizdrill = quizdrill.quizdrill:main' ]
                },
            classifiers=[
                'Development Status :: 4 - Beta',
                'Environment :: X11 Applications :: Gnome',
                'Intended Audience :: Education',
                'Intended Audience :: End Users/Desktop',
                'License :: OSI Approved :: GNU General Public License (GPL)',
                'Natural Language :: English',
                'Natural Language :: German',
                'Operating System :: OS Independent',
                'Programming Language :: Python',
                'Topic :: Education :: Testing'
                ]
            )


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'gettext-mo':
        make_mo_gettext()
    else:
        make_setup()
