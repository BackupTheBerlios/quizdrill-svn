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

from SaDrill import SaDrill, SaDrillError
from quiz import Weighted_Quiz

import pygtk
pygtk.require('2.0')
from gtk import TreeStore
import os, os.path
from pkg_resources import resource_filename
import cPickle as pickle
import gettext
_ = gettext.gettext

class Quiz_Data_Builder(object):
    """
    Creates the treestore and the list of quizzes. This is then used to create
    a quiz_data-object.
    """
    def __init__(self):
        self.treestore = TreeStore(str, str, bool)
        self.quiz_list = []
        self.last_added_section = None

    def append_section(self, title):
        """
        Adds a new section to the treestore. The given "title" must be a either
        a list with maximum 2 title for the question and answer or a str.
        """
        if len(title) < 2:
            title.append("")
        elif isinstance(title, str):
            title = [title, ""]
        column = []; column.extend(title)
        column.append(True)
        self.last_added_section = self.treestore.append(None, column)

    def append_question(self, question, is_selected=True):
        """
        Add a new question/answer-pair to the current section 
        (last_added_section).
        """
        self.quiz_list.append(question)
        column = []; column.extend(question)
        column.append(is_selected)
        self.treestore.append(self.last_added_section, column)


class Quiz_Data(object):
    """
    Manages the pool of questions and sections of a quiz and the (de-)selecting
    of them.
    """
    def __init__(self, quiz_data_builder=None):
        if quiz_data_builder == None:
            self.treestore = TreeStore(str, str, bool)
            self.quiz_list = [['', '']]
        else:
            self.treestore = quiz_data_builder.treestore
            self.quiz_list = quiz_data_builder.quiz_list

    def toggle_questions(self, treestore_path, toggle_to=None):
        """
        Given a row from the treestore it switches if it is being asked or not.
        If toggle_to is passed it is switched to the value of toggle_to.
        """
        treestore = self.treestore
        if toggle_to == None:
            toggle_to = not treestore[treestore_path][2]
        treestore[treestore_path][2] = toggle_to
        toggled_quizzes = []
        for child in treestore[treestore_path].iterchildren():
            if child[2] != toggle_to:
                child[2] = toggle_to
                toggled_quizzes.append(self._get_quiz_from_treestore(child))
        return toggle_to, toggled_quizzes

    def _get_quiz_from_treestore(self, row):
        """
        Given a row from the treestore it returns the Question Answer pair in
        it.
        """
        return [ row[0], row[1] ]


class Quiz_Header(object):
    """
    Contains the parts of a quiz, that are not tested. A kind of "meta-data" as
    well as loading and saving.
    """
    def __init__(self, file_path, quiz_type="vocabulary", 
            question_topic=[ _("What is this?"), _("What is this?") ],
            data_name=[ _("Question"), _("Answer") ],
            all_subquizzes=[]):
        self.file_path = file_path
        self.quiz_type = quiz_type
        self.question_topic = question_topic
        self.data_name = data_name
        self.all_subquizzes = all_subquizzes


class Quiz_Filer(Quiz_Data, Quiz_Header):
    """
    Contains the parts of a quiz, that are not tested. A kind of "meta-data" as
    well as loading and saving.

    Note that the quiz-words are saved in a treestore.
    """

    def __init__(self, quiz_header=None, quiz_data_builder=None, 
            score_filer=None):
        if quiz_header == None:
            Quiz_Header.__init__(self, 'no_file.drill')
        else:
            Quiz_Header.__init__(self, quiz_header.file_path, 
                    quiz_header.quiz_type, quiz_header.question_topic, 
                    quiz_header.data_name, quiz_header.all_subquizzes)
        if quiz_data_builder == None:
            Quiz_Data.__init__(self)
        else:
            Quiz_Data.__init__(self, quiz_data_builder)
        if score_filer == None:
            self.score_filer = Score_Filer(self.file_path)
        else:
            self.score_filer = score_filer
        self.quiz = Weighted_Quiz(self.quiz_list, 
                self.score_filer.question_score)
        self.quiz.next()

    def set_question_direction(self, question, answer):
        """
        Sets which column of the quiz contains the questions and which the 
        answers.

        Note: If either of the question or answer columns was not used before
          the .drill-file will be read again. (TODO)
        """
        if question == self.quiz.ask_from and answer == self.quiz.answer_to:
            return
        elif question == self.quiz.answer_to and answer == self.quiz.ask_from:
            self.quiz.set_question_direction(question)
        else:
            # TODO: Needed once quizzes can have more question/answer pairs
            print "Error: Not implemented yet!"

    def write_score_file(self, score_file=None):
        """
        Saves the score_file to disk (if the quiz is "Weighted" otherwise it
        just passes). Optionally a file name can be given to save it somewhere
        else.
        """
        if isinstance(self.quiz, Weighted_Quiz):
            self.score_filer.write_score_file(score_file)

    def toggle_questions(self, treestore_path, toggle_to=None):
        """
        Given a row from the treestore it switches if it is being asked or not.
        If toggle_to is passed it is switched to the value of toggle_to.
        """
        toggle_to, toggled_quizzes = super(Quiz_Filer, self).toggle_questions(
                treestore_path, toggle_to)
        if toggle_to:
            self.quiz.add_quizzes(toggled_quizzes)
        else:
            self.quiz.remove_quizzes(toggled_quizzes)
        return toggle_to, toggled_quizzes


class Score_Filer(object):
    """
    Processes the loading and saving of scores.
    """
    def __init__(self, quiz_file_path, score_type="", score_path=None):
        if score_path == None:
            self.SCORE_PATH = os.path.expanduser("~/.gnome2/quizdrill/")
        else:
            self.SCORE_PATH = score_path
        self.score_type = score_type
        self.score_file = self._get_default_score_file(quiz_file_path)
        self.question_score = self.read_score_file()

    def read_score_file(self, score_file=None):
        """ 
        Reads a score-file for a given quiz_file. If it can't be read an
        empty score_file is returned.
        """
        if score_file == None:
            score_file = self.score_file
        try:
            f = open(score_file)
            score = pickle.load(f)
            f.close()
        except:
            score = None
        if score == None:
            score = Weighted_Quiz.EMPTY_SCORE
        elif not score.has_key(''):     # for backwards compatibility
            score[''] = 0.
        return score

    def write_score_file(self, score_file=None):
        " Reads a score-file for a given quiz_file "
        if score_file == None:
            score_file = self.score_file
        if not os.path.exists(os.path.dirname(score_file)):
            os.makedirs(os.path.dirname(score_file))
        f = open(score_file, "w")
        pickle.dump(self.question_score, f)
        f.close()

    def _get_default_score_file(self, quiz_file_path):
        """
        Based on the given path of a quiz it determens the default score_file
        also based on the score_type and SCORE_PATH.
        """
        return self.SCORE_PATH + os.path.basename(quiz_file_path) + \
                '_' + self.score_type + ".score"


class Quiz_Loader(SaDrill):
    """
    Processes the loading of quizzes.
    """
    def __init__(self, quiz_file_path=None, question_column=0, answer_column=1):
        tag_dict = { "language" : self.on_tag_language, 
                "question" : self.on_tag_question, 
                "type" : self.on_tag_type,
                "media" : self.on_tag_media,
                "generator" : self.on_tag_generator }
        super(Quiz_Loader, self).__init__(head_tag_dict=tag_dict, 
                mandatory_has_questions=True)
        self.question_column = question_column
        self.answer_column = answer_column
        if quiz_file_path != None:
            self.quiz_file_path = quiz_file_path
        else:
            quiz_file_path = resource_filename(__name__, 
                    "../quizzes/no-file.drill")
        self.quiz_header = Quiz_Header(quiz_file_path)
        self.quiz_data_builder = Quiz_Data_Builder()

    def read_quiz_file(self, question_column=0, answer_column=1):
        """
        Reads the quiz_file and return a Quiz_Filer-object.
        """
        self.parse(self.quiz_file_path)
        return Quiz_Filer(self.quiz_header, self.quiz_data_builder)

    # SaDrill-API methods #

    def on_section(self, as_text, word_pair, tag=None, type='['):
        self.quiz_data_builder.append_section(word_pair)

    def on_question(self, as_text, word_pair, tag=None, type=''):
        #assert len(word_pair) == 2, 'Fileformaterror in "%s": \
        #        Not exactly one "=" in line %s' % ( file, i+1 )
        self.quiz_data_builder.append_question(word_pair)

    # Process "heading-tags" on reading quiz-files [see parse(file)] #

    def on_tag_language(self, as_text, word_pair, tag='language', type='!'):
        self.data_name = word_pair
        self.quiz_header.all_subquizzes = [ 
                word_pair[0] + " → " + word_pair[1],
                word_pair[1] + " → " + word_pair[0] ]

    def on_tag_question(self, as_text, word_pair=["$what"], 
            tag='question', type='!'):
        common = { "$what" : _("What is this?"), 
                "$voc_test" : _("Please translate:") }
        if word_pair[0] in common:
            word_pair = [ common[word_pair[0]], common[word_pair[0]] ]
        elif len(word_pair) == 1:
            word_pair.append(word_pair[0])
        self.quiz_header.question_topic = word_pair

    def on_tag_type(self, as_text, word_pair=None, tag='type', type='!'):
        self.quiz_header.quiz_type = word_pair[0]

    def on_tag_media(self, as_text, word_pair, tag='media', type='!'):
        # TODO (Only needed with gstreamer support)
        pass

    def on_tag_generator(self, as_text, word_pair, tag='generator', type='!'):
        # TODO
        pass

