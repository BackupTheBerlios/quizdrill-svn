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

from SaDrill import SaDrill

import re
import sys
import os.path
from pkg_resources import resource_filename, iter_entry_points
# i18n #
import locale
import gettext
_ = gettext.gettext
APP = "quizdrill"
DIR = resource_filename(__name__, "data/locale")
if not os.path.exists(DIR):
    DIR = '/usr/share/locale'
gettext.bindtextdomain(APP, DIR)
gettext.textdomain(APP)


class Abstract_Quiz_Writer(object):
    """
    Implements the appending of the Quiz-data to the .drill-file.
    """
    def __init__(self, category_filter=None, question_filter=None, 
            answer_filter=None):
        self.quiz_dict = {}
        # Filtering #
        filter_dict = { "brackets" : self.filter_brackets, 
                None : self.filter_echo }
        self.category_filter = filter_dict[category_filter]
        self.question_filter = filter_dict[question_filter]
        self.answer_filter = filter_dict[answer_filter]
        #
        self.round_brackets_re = re.compile(r"\(.*?\)")
        self.waved_brackets_re = re.compile(r"\{.*?\}")
        self.quare_brackets_re = re.compile(r"\[.*?\]")

    # Writing Quiz_data #

    def write_quiz_data(self):
        """
        Append the quiz-data to the .drill-file.
        """
        str = ""
        categories = [ self.category_filter(cat) 
                for cat in self.quiz_dict.keys() ]
        categories.sort()
        for cat in categories:
            str += "\n\n\n[" + self.category_filter(cat) + "]\n"
            self.quiz_dict[cat].sort()
            for question in self.quiz_dict[cat]:
                str += "\n" + self.question_filter(question[0]) + " = " + \
                        self.answer_filter(question[1])
        self.append_file.write(str)

    def filter_echo(self, text):
        """
        Simple pass-through filter.
        """
        return text

    def filter_brackets(self, text):
        """
        Remove brackets as they often contain extra information, that isn't
        provided on all articles (so the user can't know when to type it and
        when not) and often not what the user wants to be tested on (e.g. 
        city name in a different language, which might not be (easily) typable.
        """
        text = self.round_brackets_re.sub("", text)
        text = self.waved_brackets_re.sub("", text)
        text = self.quare_brackets_re.sub("", text)
        return text


class Abstract_Drill_Handler(object):
    """
    Plugins for new sources for builder.py should subclass this.
    """
    ONLY_ONE_TAG_ALLOWED_TEXT = _('Warning: Only one tag $%s allowed.')

    def __init__(self, file_out, collected_head_tags, collected_build_tags, 
            tag_dict={}):
        self.file_out = file_out
        self.append_file = open(file_out, "a")
        self.collected_head_tags = collected_head_tags
        self.collected_build_tags = collected_build_tags
        self.tag_dict = { 'build_to': self.on_tag_build_to, 
                'filter': self.on_tag_filter, 'encoding': self.on_tag_encoding
                }
        self.tag_dict.update(tag_dict)
        # Default values #
        self.category_filter = self.question_filter = self.answer_filter = None
        self.encoding="utf-8"
        #
        self.process_build_tags()

    def parse(self, data_source):
        """
        Process the data_source to genearte a .dill-file.
        """
        try:
            self.read_data_source(data_source)
        except:
            self.append_file.write('# Warning: Building of this Quiz got ' 
                    'interrupted.\n')
            self.write_quiz_data()
            raise
        else:
            self.write_quiz_data()     # finally-clause isn't py2.4 compatible

    def process_build_tags(self):
        for tag, word_pair in self.collected_build_tags.iteritems():
            if tag in self.tag_dict:
                self.tag_dict[tag](word_pair)
            else:
                print _('Warning: $%s was not processed.') % tag

    def on_tag_build_to(self, word_pair_list):
        assert len(word_pair_list) == 1, \
                ONLY_ONE_TAG_ALLOWED_TEXT % 'build_to allowed'
        word_pair = word_pair_list[0]
        assert len(word_pair) == 3, \
                _('Error: Tag $build_to does not have exactly two "=".')
        self.category_tag = word_pair[0]
        self.question_tag = word_pair[1]
        self.answer_tag = word_pair[2]

    def on_tag_filter(self, word_pair_list):
        assert len(word_pair_list) == 1, \
                ONLY_ONE_TAG_ALLOWED_TEXT % 'filter'
        word_pair = word_pair_list[0]
        while len(word_pair) > 3: 
            word_pair.append(None)
        self.category_filter = word_pair[0]
        self.question_filter = word_pair[1]
        self.answer_filter = word_pair[2]

    def on_tag_encoding(self, word_pair_list):
        assert len(word_pair_list) == 1, \
                ONLY_ONE_TAG_ALLOWED_TEXT % 'encoding'
        word_pair = word_pair_list[0]
        self.encoding = word_pair[0]

class Drill_Builder(SaDrill):
    """
    Processes a .drill.builder-file and passes on to a plugin given by the 
    $builder-tag in the file which then outputs a .drill(.origninal)-file.
    """
    def __init__(self):
        tag_dict = { "builder" : self.on_tag_builder }
        self.on_default_build_tag = self.on_build_tag_collect_in_dict 
        self.on_unknown_build_tag = self.on_build_tag_collect_in_dict 
        mandatory_tags = [ "build_to", "builder" ]
        super(Drill_Builder, self).__init__({}, tag_dict, {}, mandatory_tags)

    def convert_drill_file(self, file, data_source):
        """
        Build a .drill-file from a .builder discription-file and a data-source
        (e.g. a wikipedia-dump).
        """
        file_out = file.replace(".builder", "") + ".original"
        self._fout = open(file_out, "w")
        self.parse(file)

        self._fout.close()
        builder = self.builder_class(file_out, self.collected_head_tags, 
                self.collected_build_tags)
        builder.parse(data_source)

    def on_tag_builder(self, as_text, word_pair, tag='builder', type='$'):
        """
        Finds out which quiz_builder_source_plugins should be used.
        """
        for entrypoint in iter_entry_points(
                "quiz_builder_source_plugins"):
            if entrypoint.name == word_pair[0]:
                self.builder_class = entrypoint.load()
                break
        else:
            print _('Error: Unknown builder "%s".') % word_pair[0]
            sys.exit(1)
        self.on_build_tag_collect_in_dict(as_text, word_pair, tag, type)

    def on_default_head_tag(self, as_text, word_pair=None, tag=None, type='#'):
        """
        Writes header-lines unfiltered to the new .drill-file and then passes 
        on to on_head_tag_collect_in_dict.
        """
        self._fout.write(as_text + "\n")
        self.on_head_tag_collect_in_dict(as_text, word_pair, tag, type)


def build():
    """
    A console script for our endusers. 
    """
    builder = Drill_Builder()
    if len(sys.argv) == 3:
        builder.convert_drill_file(sys.argv[1], sys.argv[2])
    else: 
        print _('Usage: %s [.drill.builder-file] [data_source-file]') \
                % sys.argv[0]

if __name__ == "__main__":
    build()

