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

from urllib import urlopen
from string import Template, replace
import re

### Update documentation ###

def update_doc_de():
    """
    Calls update_doc() with a predefined list of files for our German 
    documentation on the wiki (OpenFacts, a MediaWiki).
    """
    url_base = 'http://openfacts.berlios.de/index-en.phtml?title=Quizdrill'
    file_dict = [
            [ url_base, 'Quizdrill.html', 'Quizdrill'],
            [ url_base + '/Quiz_schreiben', 
                'Quiz_schreiben.html', 'Quiz schreiben'],
            [ url_base + '/Quiz_schreiben/Liste_der_Schlüsselwörter',
                'Liste_der_Schlüsselwörter.html', 'Liste der Schlüsselwörter']
            ]
    output_folder="doc/de/"
    additional_text='Eine aktuelle Version dieser Datei befindet sich ' \
            'auf <a href="$url">unserer Wikiseite</a>.'
    update_doc(file_dict, output_folder, additional_text)

def update_doc_en():
    """
    Calls update_doc() with a predefined list of files for our English 
    documentation on the wiki (OpenFacts, a MediaWiki).
    """
    url_base = 'http://openfacts.berlios.de/index-en.phtml?title=Quizdrill'
    file_dict = [
            [ url_base, 'Quizdrill.html', 'Quizdrill'],
            [ url_base +'/Install', 'Install.html', 'Installing Quizdrill'],
            [ url_base +'/Usage', 'Usage.html', 'Usage of Quizdrill'],
            [ url_base +'/Writing_Quizzes', 'Writing_Quizzes.html', 
                'Writing Quizzes for Quizdrill'],
            [ url_base +'/Simular_Programs', 'simular_programs.html', 
                'Programs Simular to Quizdrill'],
            [ url_base + '/Testing', 'Testing.html', 'Manual Tests']
            ]
    output_folder="doc/en/"
    additional_text='The current version of this file is availible at ' \
            '<a href="$url">our wiki-page</a>.'
    update_doc(file_dict, output_folder, additional_text)

def update_doc(file_dict, output_folder, additional_text=""):
    """
    Download our documentation from the wiki (OpenFacts, a MediaWiki) and 
    convert it so it nicely viewable offline.
    """
    top_of_html = Template(
    '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitionsl//EN">'
    '<html><head><title>$title</title></head>'
    '<body>'
    '<div id="addtext">$add_text</div>')
    end_of_html = Template(r"</body></html>")
    article_div_re = re.compile("<div id='article'>.*?</div>", re.DOTALL)
    for remote_file, locale_file, title in file_dict:
        try:
            fin = urlopen(remote_file)
        except:
            print "Error: Couldn't read url %s." % remote_file
        else:
            html_in = fin.read()
            article = article_div_re.findall(html_in)
            if len(article) == 1:
                article = article[0]
                for url, lfile, forget in file_dict:
                    article = replace(article, 'href="' + url + '"', 
                            'href="' + lfile +'"')
                mapping = { 'title': title, 'url': remote_file, 
                        'add_text': additional_text }
                fout = open(output_folder + locale_file, "w")
                fout.write(
                        Template(top_of_html.substitute(mapping)).\
                                substitute(mapping)
                        + article 
                        + Template(end_of_html.substitute(mapping)).\
                                substitute(mapping)
                        )
                print "Updated %s." % locale_file
            else:
                print "Error: %s doesn't contain an article-block." % \
                        remote_file

### Gettext ###

def make_mo_gettext():
    """
    Calls 'msgfmt' from GNU gettext to genearte object files (.mo) from
    the translation files (.po).

    Note: As this function usese the $PATH variable (with spawnlp) it doesn't
      work under Windows.
    """
    print "Generating gettext mo files:",
    po_files = 'po/*.po'
    mo_base_dir = 'locale/%s/LC_MESSAGES/'
    conv_program = 'msgfmt'

    for lang_file in glob(po_files):
        language = basename(lang_file)[:-3]
        mo_dir = mo_base_dir % language
        print language,
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
    print "."

### Setup ###

def make_setup():
    """
    The setuptools setup packaging for eggs, Python Cheese Shop 
    registration and distutils install.

    Note: Don't forget to update your documentation with "setup update_doc"
      before calling "setup sdist" or "setup bdist*".
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
            data_files=[
                ('quizzes', listdir('quizzes/')),
                ('quizzes/builder', listdir('quizzes/builder/')),
                ('po', ['po/de.po']),
                ('doc', ['README', 'TODO', 'GPL-2', 'Changes']),
                ('doc/html-de', listdir('doc/de/')),
                ('doc/html-en', listdir('doc/en/'))
                ],
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
    elif len(sys.argv) > 1 and sys.argv[1] == 'update_doc':
        update_doc_de()
        update_doc_en()
    else:
        make_setup()
