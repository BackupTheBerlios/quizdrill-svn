#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, Adam Schmalhofer
# Developed by Adam Schmalhofer <schmalhof@users.berlios.de>
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

import pygtk
pygtk.require('2.0')
import gobject, gtk, gtk.glade
import random
import os, os.path
import cPickle as pickle
# i18n
import locale
import gettext
_ = gettext.gettext
APP = "quizdrill"
DIR = "locale"
locale.bindtextdomain(APP, DIR)
locale.textdomain(APP)
gettext.bindtextdomain(APP, DIR)
gettext.textdomain(APP)

class Quiz_Info:
    """
    TODO: move quiz settings from class Gui here, so quizzes can be switched
    nicely.

    Contains the parts of a quiz, that are not tested. A kind of "meta-data".
    """
    quiz_file_path = "quizzes/de-fr.drill"
    type = "vocabulary"
    subquiz = None
    treestore = None
    quiz = None

    def __init__(self, quiz_file_path=None):
        self.generate_quiz(quiz_file_path)

    def read_score_file(self, type="", score_file=None):
        # TODO: move here from Gui
        pass

    def write_score_file(self, score, type=""):
        # TODO: move here from Gui
        pass

    def _get_score_file(self, quiz_file, type):
        # TODO: move here from Gui
        pass

    def read_quiz_list(self, file):
        # TODO: move here from Gui
        pass

    def generate_quiz(self, quiz_file_path=None):
        # TODO: move here from Gui
        pass

    def next_question(self):
        # TODO: move part of Gui's here
        pass


class Gui:
    GLADE_FILE = "quizdrill.glade"
    SCORE_PATH = os.path.expanduser("~/.quizdrill/scores/")
    quiz_file_path = "quizzes/de-fr.drill"
    break_length = 900000    # 900,000 ms: 15min
    snooze_length = 300000   # 300,000 ms:  5min
    timer_id = 0

    def __init__(self):
        xml = gtk.glade.XML(self.GLADE_FILE, "main_window", APP)
        gw = xml.get_widget
        ## widgets
        self.main_window = gw("main_window")
        self.main_notbook_tabs = {
                "multi"  : [ gw("multi_tab_label"), gw("multi_tab_vbox") ], 
                "simple" : [ gw("simple_tab_label"), gw("simple_tab_vbox") ], 
                "flash"  : [ gw("flash_tab_label"), gw("flash_tab_vbox") ] }
        self.subquiz_combobox = gw("subquiz_combobox")
        self.word_treeview = gw("word_treeview")
        self.multi_answer_vbuttonbox = gw("multi_answer_vbuttonbox")
        self.simple_answer_entry = gw("simple_answer_entry")
        self.question_topic_labels = [ gw("multi_question_topic_label"),
                gw("simple_question_topic_label"),
                gw("flash_question_topic_label") ]
        self.question_labels = [ gw("multi_question_label"), 
                gw("simple_question_label"), gw("flash_question_label") ]
        self.multi_question_buttons = [ gw("button11"), 
                gw("button12"), gw("button13"), gw("button14"), 
                gw("button15"), gw("button16"), gw("button17") ]
        self.simple_question_button = gw("simple_question_button")
        self.flash_notebook = gw("flash_notebook")
        self.flash_answer_buttons = [ gw("flash_answer_button0"), 
                gw("flash_answer_button1"), gw("flash_answer_button2"), 
                gw("flash_answer_button3"), gw("flash_answer_button4"), 
                gw("flash_answer_button5") ]
        self.flash_answer_label = gw("flash_answer_label")
        self.progressbar1 = gw("progressbar1")
        ### start quiz
        self.generate_quiz()
        ## signals
        xml.signal_autoconnect(self)

    def generate_quiz(self, quiz_file_path=None):
        if quiz_file_path != None:
            self.quiz_file_path = quiz_file_path
        score = self.read_score_file()
        self.read_quiz_list(self.quiz_file_path)
        self.quiz = Queued_Quiz(self.quizlist, score)
        self.next_question()

    def next_question(self):
        if not self.quiz.next():
            self.start_relax_time(self.break_length)
        for label in self.question_labels:
            label.set_text(self.quiz.question[self.quiz.ask_from])
        self.simple_answer_entry.set_text("")
        self.progressbar1.set_fraction(
                float(self.quiz.answered) / self.quiz.session_length)
        # set multiquiz answers
        for button, text in zip(
                self.multi_question_buttons,self.quiz.multi_choices):
            button.set_label(text)
            button.set_sensitive(True)

    def switch_Quiz(self, quiz_info=None):
        """
        Set the Userinterface to test a different Quiz (represented by a 
        Info_Quiz object or randomly selected).
        """
        pass

    # Timer

    def start_relax_time(self, break_length, minimize=True):
        """
        Iconify window as a break and deiconify it when it's over

        Note: There is a race condition. However this should be harmless
        """
        if self.timer_id:
            gobject.source_remove(self.timer_id)
        if minimize:
            self.main_window.iconify()
        self.timer_id = gobject.timeout_add(break_length, 
                self.on_end_relax_time)

    def on_end_relax_time(self):
        self.main_window.deiconify()
        self.timer_id = 0

    # read/write files

    def read_score_file(self, type="", score_file=None):
        " Reads a score-file for a given quiz_file "
        if score_file == None:
            score_file = self._get_score_file(self.quiz_file_path, type)
        try:
            f = open(score_file)
        except IOError:
            return {}
        return pickle.load(f)

    def write_score_file(self, score, type=""):
        " Reads a score-file for a given quiz_file "
        score_file = self._get_score_file(self.quiz_file_path, type)
        if not os.path.exists(os.path.dirname(score_file)):
            os.makedirs(os.path.dirname(score_file))
        f = open(score_file, "w")
        pickle.dump(score, f)
        f.close()

    def _get_score_file(self, quiz_file, type):
        return self.SCORE_PATH + os.path.basename(quiz_file) + \
                '_' + type + ".score"

    def read_quiz_list(self, file):
        """
        Reads a .drill-file and builds a quizlist,
        TODO: a TreeStore and set it in word_treeview
        """
        tag_dict = { "language" : self.on_tag_language, 
                "question" : self.on_tag_question, 
                "type" : self.on_tag_type,
                "media" : self.on_tag_media,
                "generator" : self.on_tag_generator }
        # Prepare TreeView
        self.treestore = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_STRING,
                gobject.TYPE_BOOLEAN )
        # Read file and add to quizlist and treestore
        f = open(file)
        self.quizlist = []
        section = None

        self.set_default_tags()
        for i, line in enumerate(f.readlines()):
            line = line.strip()
            if len(line) > 0:
                if line[0] == '#':
                    continue
                elif line[0] == '!':
                    colon = line.index(":")
                    tag = line[1:colon]
                    word_pair = [ w.strip() for w in line[colon+1:].split("=")]
                    if tag in tag_dict:
                        tag_dict[tag](word_pair)
                    else:
                        print _('Warning: unknown tag "%s"') % tag
                elif line[0] == '[':
                    line = line[1:-1]
                    word_pair = [ w.strip() for w in line.split("=", 1) ]
                    if len(word_pair) < 2:
                        word_pair.append("")
                    column = []; column.extend(word_pair)
                    column.append(True)
                    section = self.treestore.append(None, column)
                else:
                    word_pair = [ w.strip() for w in line.split("=") ]
                    assert len(word_pair) == 2, 'Fileformaterror in "%s": \
                            Not exactly one "=" in line %s' % ( file, i+1 )
                    self.quizlist.append(word_pair)
                    column = []; column.extend(word_pair)
                    column.append(True)
                    self.treestore.append(section, column)
        # toggler
        toggler = gtk.CellRendererToggle()
        toggler.connect( 'toggled', self.on_treeview_toogled )
        self.tvcolumn = gtk.TreeViewColumn(_("test"), toggler)
        self.tvcolumn.add_attribute(toggler, "active", 2)
        self.word_treeview.append_column(self.tvcolumn)
        self.word_treeview.set_model(self.treestore)
        #
        f.close()

    def get_quiz_from_treeview(self, row):
        return [ row[0], row[1] ]

    # Process "heading-tags" on reading quiz-files [see read_quiz_list(file)]

    def set_default_tags(self):
        self.on_tag_question()
        self.on_tag_type()

    def on_tag_language(self, word_pair):
        for i, title in enumerate(word_pair):
            self.tvcolumn = gtk.TreeViewColumn(title,
                    gtk.CellRendererText(), text=i)
            self.word_treeview.append_column(self.tvcolumn)
        self.subquiz_combobox.append_text(
                word_pair[0] + " → " + word_pair[1])
        self.subquiz_combobox.append_text(
                word_pair[1] + " → " + word_pair[0])
        self.subquiz_combobox.set_active(0)

    def on_tag_question(self, word_pair=["$what"]):
        common = { "$what" : _("What is this?"), 
                "$voc_test" : _("Please translate:") }
        if word_pair[0] in common:
            word_pair = [ common[word_pair[0]] ]
        else:
            self.question_topic = word_pair
        for label in self.question_topic_labels:
            label.set_markup("<b>%s</b>" % word_pair[0])

    def on_tag_type(self, word_pair=None):
        # show and hide combobox
        if word_pair == None or word_pair[0] == "vocabulary":
            self.subquiz_combobox.show()
            visible_tabs = [ True, True, False ]
        elif word_pair[0] == "questionnaire":
            self.subquiz_combobox.hide()
            visible_tabs = [ True, True, False ]
        elif word_pair[0] == "flashcard":
            self.subquiz_combobox.hide()
            visible_tabs = [ False, False, True ]
        else:
            print _('Warning: unknown quiz type "%s"') % word_pair[0]
            visible_tabs = [ True, True, True ]
        # show and hide notebookpanels
        for tab, visi in zip(self.main_notbook_tabs.itervalues(),visible_tabs):
            for widget in tab:
                if visi:
                    widget.show()
                else:
                    widget.hide()

    def on_tag_media(self, word_pair):
        # TODO (Only needed with gstreamer support)
        pass

    def on_tag_generator(self, word_pair):
        # TODO
        pass

    # main_window handlers #

    def on_treeview_toogled(self, cell, path ):
        """ toggle selected CellRendererToggle Row """
        toggled_quizzes = []
        self.treestore[path][2] = not self.treestore[path][2]
        for child in self.treestore[path].iterchildren():
            if child[2] != self.treestore[path][2]:
                child[2] = self.treestore[path][2]
                toggled_quizzes.append(self.get_quiz_from_treeview(child))
        if self.treestore[path][2]:
            self.quiz.add_quizzes(toggled_quizzes)
        else:
            self.quiz.remove_quizzes(toggled_quizzes)

    def on_quit(self, widget):
        try:
            if isinstance(self.quiz, Weighted_Quiz):
                self.write_score_file(self.quiz.question_score)
        finally:
            gtk.main_quit()

    def on_main_window_window_state_event(self, widget, event):
        """ Snooze when minimized """
        if 'iconified' in event.new_window_state.value_nicks and \
                not self.timer_id:
            self.start_relax_time(self.snooze_length, False)
        elif not 'iconified' in event.new_window_state.value_nicks \
                and self.timer_id:
            gobject.source_remove(self.timer_id)
            self.timer_id = 0

    def on_about_activate(self, widget):
        gtk.glade.XML(self.GLADE_FILE, "aboutdialog1", APP)

    def on_preferences1_activate(self, widget):
        gtk.glade.XML(self.GLADE_FILE, "pref_window", APP)

    def on_open1_activate(self, widget):
        "Creates an Open-File-Dialog, which selects a new Quiz"
        chooser = gtk.FileChooserDialog("Open Quiz", None, 
                gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, 
                gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        chooser.set_current_folder(os.path.dirname(self.quiz_file_path))
        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            self.generate_quiz(chooser.get_filename())
        chooser.destroy()

    def on_multi_question_answer_button_clicked(self, widget, data=None):
        if self.quiz.check(widget.get_label()):
            self.next_question()
        else:
            widget.set_sensitive(False)

    def on_simple_question_button_clicked(self, widget, data=None):
        if self.quiz.check(self.simple_answer_entry.get_text().strip()):
            self.next_question()
    
    def on_flash_question_button_clicked(self, widget, date=None):
        self.flash_answer_label.set_text(
                self.quiz.question[self.quiz.answer_to])
        self.flash_notebook.set_current_page(1)

    def on_flash_answer_button_clicked(self, widget, data=None):
        if isinstance(self.quiz, Weighted_Quiz):
            self.quiz.set_answer_quality(
                    self.flash_answer_buttons.index(widget))
        self.next_question()
        self.flash_notebook.set_current_page(0)

    def on_subquiz_combobox_changed(self, widget):
        new_status = widget.get_active()
        self.quiz.set_question_direction(new_status)
        if len(self.question_topic) > 1:
            for label in self.question_topic_labels:
                label.set_text(self.question_topic[new_status])
        self.next_question()

    def on_main_notebook_switch_page(self, widget, gpointer, new_tab):
        if new_tab == 2:  # "Simple Quiz"-tab
            self.simple_question_button.grab_default()


class Quiz:
    """
    A simple random-selecting vocabulary test, with simple quiz and 
    multiple quiz
    """
    DEFAULT_MULTICHOICE_LEN = 7
    quiz_pool = []

    def __init__(self, quiz_pool, ask_from=0, exam_length=15):
        self.answered = 0
        self.correct_answered = 0
        self.exam_length = exam_length
        self.session_length = exam_length
        self.ask_from = ask_from
        self.answer_to = 1 - ask_from
        self.add_quizzes(quiz_pool)

    def next(self):
        # Generate new Test
        self.tries = 0
        self._select_question()
        self.multi_choices = self._gen_multi_choices()
        # Time for relaxing ?
        if self.answered == self.session_length:
            self.session_length += self.exam_length
            return False
        else:
            return True

    def _select_question(self):
        "select next question"
        self.question = random.choice(self.quiz_pool)

    def _gen_multi_choices(self):
        list = [ self.question[self.answer_to] ]
        while len(list) < self.multichoice_len:
            r = random.randrange(len(self.quiz_pool))
            word = self.quiz_pool[r][self.answer_to]
            if not word in list:
                list.append(word)
        random.shuffle(list)
        return list

    def check(self, solution):
        """
        Checks if the given solution is correct
        and returns the corresponding boolean
        """
        if solution == self.question[self.answer_to]:
            if self.tries == 0:
                self.correct_answered += 1
            self.answered += 1
            return True
        else:
            self.tries += 1
            return False

    def set_question_direction(self, direction):
        if direction in [0, 1]:
            self.ask_from = direction
            self.answer_to = 1 - direction

    def add_quizzes(self, new_quizzes):
        self.quiz_pool.extend(new_quizzes)
        self._refit_multichoice_len()

    def remove_quizzes(self, rm_quizzes):
        for quiz in rm_quizzes:
            self.quiz_pool.remove(quiz)
        self._refit_multichoice_len()

    def _refit_multichoice_len(self):
        if len(self.quiz_pool) < self.DEFAULT_MULTICHOICE_LEN:
            self.multichoice_len = len(self.quiz_pool)
        else:
            self.multichoice_len = self.DEFAULT_MULTICHOICE_LEN

class Weighted_Quiz(Quiz):
    """
    A quiz with weighted question selection of a vocabulary test. The more 
    questions are answered wrong (in comparison to the other questions the 
    more often they are asked. More recent answers are weighted stronger.

    score is form 0 (worst) to 1 (best).

    The score is recorded by question (as opposed to by answer) as 
    non-vocabulary answers may be identical.
    """

    def __init__(self, quiz_pool, 
            question_score={}, ask_from=0, exam_length=15):
        self.question_score = question_score
        self.score_sum = 0.
        Quiz.__init__(self, quiz_pool, ask_from, exam_length)
        self.score_sum = self._gen_score_sum()

    def _select_question(self):
        "selcet next question"
        while True:
            Quiz._select_question(self)
            bound = random.random() * 1.01     # to avoid infinit loops
            if self.question_score[self.question[self.ask_from]] <= bound:
                return

    def check(self, solution):
        if Quiz.check(self, solution):
            self._update_score(self.question[self.ask_from], 
                    self.tries == 0)
            return True
        else:
            return False

    def set_answer_quality(self, quality):
        self._update_score(self.question[self.ask_from], quality > 3)

    def _update_score(self, word, correct_answered):
        """
        updates the score (and score_sum) of word, depending on whether
        it was answered correctly
        """
        self.score_sum -= self.question_score[word]
        self.question_score[word] = (self.question_score[word] * 3
                + correct_answered ) / 4
        self.score_sum += self.question_score[word]

    def _gen_score_sum(self, quizzes=None):
        """ 
        Creates the sum of all sores in quiz_pool in the current question 
        direction and fills all unknown scores with 0
        """
        score_sum = 0.
        if quizzes == None:
            quizzes = self.quiz_pool
        for question in quizzes:
            if question[self.ask_from] in self.question_score:
                score_sum += self.question_score[question[self.ask_from]]
            else:
                least_score = 0.
                self.question_score[question[self.ask_from]] = 0.
        return score_sum

    def set_question_direction(self, direction):
        Quiz.set_question_direction(self, direction)
        self.score_sum = self._gen_score_sum()

    def add_quizzes(self, new_quizzes):
        Quiz.add_quizzes(self, new_quizzes)
        self.score_sum += self._gen_score_sum(new_quizzes)

    def remove_quizzes(self, rm_quizzes):
        Quiz.remove_quizzes(self, rm_quizzes)
        self.score_sum -= self._gen_score_sum(rm_quizzes)

class Queued_Quiz(Weighted_Quiz):
    """ 
    Previously not asked questions are added one-after-each-other once only a 
    few questions still are below a certain score.
    """
    def __init__(self, question_pool, question_score={}, ask_from=0, 
            exam_length=15, bad_score=.4, min_num_bad_scores=3, 
            min_question_num=20, batch_length=5):
        self.new_quiz_pool = []
        self.num_bad_scores = 0
        self.bad_score = bad_score
        self.min_num_bad_scores = min_num_bad_scores
        self.min_question_num = min_question_num
        self.batch_length = batch_length
        Weighted_Quiz.__init__(self, [], question_score, ask_from, exam_length)
        self.add_quizzes(question_pool)

    def _update_score(self, question, correct_answered):
        """
        updates the score (and score_sum) of question, depending on whether
        it was answered correctly.
        """
        if self.question_score[question] < self.bad_score:
            self.num_bad_scores -= 1
        Weighted_Quiz._update_score(self, question, correct_answered)
        if self.question_score[question] < self.bad_score:
            self.num_bad_scores += 1

    def _select_question(self):
        "select next question"
        if self.num_bad_scores < self.min_num_bad_scores:
            self._increase_quiz_pool()
        Weighted_Quiz._select_question(self)

    def _increase_quiz_pool(self, num=None):
        "Add quizzes from the new_quiz_pool to the quiz_pool"
        if num == None:
            num = self.batch_length
        new_quizzes = []
        for i in range(min(num, len(self.new_quiz_pool))):
            new_quizzes.append(self.new_quiz_pool.pop(0))
        self.num_bad_scores += num
        Weighted_Quiz.add_quizzes(self, new_quizzes)

    def add_quizzes(self, new_quizzes):
        """
        Add quizzes with score to quiz_pool; without to new_quiz_pool
        """
        scored_quizzes = []
        un_scored_quizzes = []
        for quiz in new_quizzes:
            question = quiz[self.ask_from]
            if question in self.question_score:
                scored_quizzes.append(quiz)
                if self.question_score[question] < self.bad_score:
                    self.num_bad_scores += 1
            else:
                un_scored_quizzes.append(quiz)
        self.new_quiz_pool.extend(un_scored_quizzes)
        Weighted_Quiz.add_quizzes(self, scored_quizzes)
        self._insure_min_quiz_num()

    def _insure_min_quiz_num(self):
        """ Make sure not too few questions are in the quiz_pool """
        num_missing = min( len(self.new_quiz_pool),
                self.min_question_num - len(self.quiz_pool) )
        if num_missing > 0:
            self._increase_quiz_pool(num_missing)

    def remove_quizzes(self, rm_quizzes):
        rm_scored_quizzes = []
        for quiz in rm_quizzes:
            try:
                self.new_quiz_pool.remove(quiz)
            except:
                rm_scored_quizzes.append(quiz)
        Weighted_Quiz.remove_quizzes(self, rm_scored_quizzes)
        self._insure_min_quiz_num()
                
if __name__ == "__main__":
    gui = Gui()
    gtk.main()
