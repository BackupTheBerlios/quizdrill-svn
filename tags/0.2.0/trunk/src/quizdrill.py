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

import pygtk
pygtk.require('2.0')
import gobject, gtk, gtk.glade
import random
import os, os.path
from pkg_resources import resource_filename
import cPickle as pickle
# i18n #
import locale
import gettext
_ = gettext.gettext
APP = "quizdrill"
DIR = resource_filename(__name__, "data/locale")
if not os.path.exists(DIR):
    DIR = '/usr/share/locale'
locale.bindtextdomain(APP, DIR)
locale.textdomain(APP)
gettext.bindtextdomain(APP, DIR)
gettext.textdomain(APP)

class Gui:
    GLADE_FILE = resource_filename(__name__, "data/quizdrill.glade")
    SHOW_TABS = { "vocabulary" : [ True, True, True], 
            "questionnaire" : [ True, True, True ],
            "flashcard" : [ False, False, True ],
            "all" : [ True, True, True ] }
    break_length = 900000    # 900,000 ms: 15min
    snooze_length = 300000   # 300,000 ms:  5min

    def __init__(self):
        default_quiz = 'deu-fra.drill'
        self.timer_id = 0
        self.quiz_filer_list = []
        # widgets #
        xml = gtk.glade.XML(self.GLADE_FILE, "main_window", APP)
        gw = xml.get_widget
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
        self.flash_answer_buttons = [ 
                gw("flash_answer_button_no"), gw("flash_answer_button_yes") ]
        self.flash_answer_label = gw("flash_answer_label")
        self.progressbar1 = gw("progressbar1")
        sb = self.statusbar1 = gw("statusbar1")
        self.statusbar_contextid = { "last_answer" : 
                sb.get_context_id( "The answer to the last asked question." ) }
        # gconf #
        #try:
        #    import gconf
        #else:
        #    self._init_gconf()
        # start quiz #
        ### Find where the default quiz is ###
        for quiz_file in [ os.path.expanduser('~/.quizdrill/' + default_quiz),
                resource_filename(__name__, '../quizzes/'), 
                resource_filename(__name__, 
                    '../share/quizdrill/' + default_quiz),
                resource_filename(__name__, '../quizdrill/' + default_quiz),
                '/usr/share/quizdrill/', '/usr/locale/share/quizdrill/' ]:
            if os.path.exists(quiz_file + default_quiz):
                quiz_file_path = quiz_file + default_quiz
                break
        else:
            quiz_file_path = None
        try:
            self.quiz_filer_list.append(Quiz_Filer(quiz_file_path))
        except (IOError, SaDrillError):
            self.quiz_filer_list.append(Quiz_Filer())
        self.switch_quiz(self.quiz_filer_list[0])
        # connect signals #
        xml.signal_autoconnect(self)

    def _init_gconf(self):
        """ 
        Set configoptions from gconf.
        
        Note: Very experimenal; Needs additional errorhandling
        """
        USE_TIMER_KEY = '/apps/quizdrill/timer/use_timer'
        BREAK_LENGTH_KEY = '/apps/quizdrill/timer/break_length'
        SNOOZE_LENGTH_KEY = '/apps/quizdrill/timer/snooze_length'
        DEFAULT_QUIZ_KEY = '/apps/quizdrill/default_quiz'
        #
        client = self.gconf_client = gconf.client_get_default()
        #schema = 
        self.use_timer = client.get_bool(USE_TIMER_KEY)
        self.exam_length = client.get_int(EXAM_LENGTH_KEY)
        self.break_length = client.get_int(BREAK_LENGTH_KEY)
        self.snooze_length = client.get_int(SNOOZE_LENGTH_KEY)
        quiz_file_path = client.get_string(DEFAULT_QUIZ_KEY)
        # start quiz #
        self.quiz_filer_list.append(Quiz_Filer(quiz_file_path))
        self.switch_quiz(self.quiz_filer_list[0])

    def update_gui(self):
        """
        (re-)set all the user-non-editable text (labels etc.).
        Used when a new quiz is loaded, a new question is asked.
        """
        for label in self.question_labels:
            label.set_text(self.quiz.question[self.quiz.ask_from])
        self.simple_answer_entry.set_text("")
        self.progressbar1.set_fraction(
                float(self.quiz.answered) / self.quiz.session_length)
        # set multiquiz answers #
        for button, text in zip(self.multi_question_buttons, 
                self.quiz.multi_choices):
            button.set_label(text)
            button.set_sensitive(True)
        # set flash card to front side #
        self.flash_notebook.set_current_page(0)

    def redisplay_correctly_answered(self, last_question):
        """
        Displays the last answer (currently on the StatusBar). This is so
        the user has the possibility to review again especially after many
        faulty answers (simple quiz) or surprised/unknows right answer (multi
        choice). No use on flashcard.
        """
        # TRANSLATORS: This is displayed on the statusbar so try to keep it 
        #    short. The answer should be shown rather then the text or the 
        #    question if the bar is too short.
        text = _("'%(answer)s' to '%(question)s' was correct.") % {
                "answer" : last_question[self.quiz.answer_to],
                "question" : last_question[self.quiz.ask_from] }
        self.statusbar1.pop(self.statusbar_contextid["last_answer"])
        self.statusbar1.push(self.statusbar_contextid["last_answer"], text)

    def switch_quiz(self, quiz_filer=None):
        """
        Set the Userinterface to test a different Quiz (represented by a 
        Quiz_Filer object or randomly selected).
        """
        # disconnect old listeners #
        quiz_filer.quiz.disconnect('question_changed', self.update_gui)
        quiz_filer.quiz.disconnect('break_time', self.start_relax_time)
        # replace #
        if quiz_filer == None:
            quiz_filer = random.select(self.quiz_filer_list)
        self.quiz_filer = quiz_filer
        self.quiz = quiz_filer.quiz
        self.update_gui()
        # show and hide notebookpanels #
        if not quiz_filer.type in self.SHOW_TABS:
            print _('Warning: unknown quiz type "%s".') % quiz_filer.type
            type = "all"
        else:
            type = self.quiz_filer.type
        for tab, visi in zip(self.main_notbook_tabs.itervalues(),
                self.SHOW_TABS[type]):
            for widget in tab:   # tab is tab-label + tab-content
                if visi:
                    widget.show()
                else:
                    widget.hide()
        # show, hide and settext of combobox #
        if quiz_filer.all_subquizzes == []:
            self.subquiz_combobox.hide()
        else:
            for i in range(2):            # dirty clear combobox
                self.subquiz_combobox.remove_text(0)
            for subquiz in quiz_filer.all_subquizzes:
                self.subquiz_combobox.append_text(subquiz)
            self.subquiz_combobox.set_active(self.quiz.ask_from)
            self.subquiz_combobox.show()
        #
        for label in self.question_topic_labels:
            label.set_markup("<b>%s</b>" % 
                    quiz_filer.question_topic[self.quiz.ask_from])
        # treeview #
        ## Question/Answer-Columns ##
        for column in self.word_treeview.get_columns():
            self.word_treeview.remove_column(column)
        for i, title in enumerate(quiz_filer.data_name):
            tvcolumn = gtk.TreeViewColumn(title,
                    gtk.CellRendererText(), text=i)
            self.word_treeview.append_column(tvcolumn)
        ## toggler ##
        toggler = gtk.CellRendererToggle()
        toggler.connect( 'toggled', self.on_treeview_toogled )
        tvcolumn = gtk.TreeViewColumn(_("test"), toggler)
        tvcolumn.add_attribute(toggler, "active", 2)
        self.word_treeview.append_column(tvcolumn)
        self.word_treeview.set_model(quiz_filer.treestore)
        # clean statusbar #
        self.statusbar1.pop(self.statusbar_contextid["last_answer"])
        # connect listeners #
        quiz_filer.quiz.connect('question_changed', self.update_gui)
        quiz_filer.quiz.connect('break_time', self.start_relax_time)

    def get_quiz_from_treeview(self, row):
        return [ row[0], row[1] ]

    # Timer #

    def start_relax_time(self, break_length=None, minimize=True):
        """
        Iconify window as a break and deiconify it when it's over

        Note: There is a race condition. However this should be harmless
        """
        if break_length == None:
            break_length = self.break_length
        if self.timer_id:
            gobject.source_remove(self.timer_id)
        if minimize:
            self.main_window.iconify()
        self.timer_id = gobject.timeout_add(break_length, 
                self.on_end_relax_time)

    def on_end_relax_time(self):
        self.main_window.deiconify()
        self.timer_id = 0

    # main_window handlers #

    ## all (or indebendant of) tabs ##

    def on_quit(self, widget):
        for filer in self.quiz_filer_list:
            filer.write_score_file()
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
        chooser.set_current_folder(
                os.path.abspath(os.path.dirname(
                    self.quiz_filer.quiz_file_path)))
        response = chooser.run()
        chooser.hide()
        if response == gtk.RESPONSE_OK:
            try:
                self.quiz_filer_list = [Quiz_Filer(chooser.get_filename())]
            except (IOError, SaDrillError), e:
                message = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, 
                        buttons=gtk.BUTTONS_OK, message_format=e.str)
                message.run()
                message.destroy()
            else:
                self.switch_quiz(self.quiz_filer_list[0])
        chooser.destroy()

    def on_main_notebook_switch_page(self, widget, gpointer, new_tab):
        if new_tab == 2:  # "Simple Quiz"-tab
            self.simple_question_button.grab_default()

    ## words-/settings-tab ##

    def on_subquiz_combobox_changed(self, widget):
        new_status = widget.get_active()
        self.quiz.set_question_direction(new_status)
        if len(self.quiz_filer.question_topic) > 1:
            for label in self.question_topic_labels:
                label.set_text(self.quiz_filer.question_topic[new_status])
        self.quiz.new_question()

    def on_treeview_toogled(self, cell, path ):
        """ toggle selected CellRendererToggle Row """
        toggled_quizzes = []
        treestore = self.quiz_filer.treestore
        treestore[path][2] = not treestore[path][2]
        for child in treestore[path].iterchildren():
            if child[2] != treestore[path][2]:
                child[2] = treestore[path][2]
                toggled_quizzes.append(self.get_quiz_from_treeview(child))
        if treestore[path][2]:
            self.quiz.add_quizzes(toggled_quizzes)
        else:
            self.quiz.remove_quizzes(toggled_quizzes)

    ## questionaskting-tabs (simple/multi/flash) ##

    def on_multi_question_answer_button_clicked(self, widget, data=None):
        answer = widget.get_label()
        if self.quiz.check(answer):
            self.redisplay_correctly_answered(self.quiz.question)
            self.quiz.next()
        else:
            widget.set_sensitive(False)
            # statusbar1: show question to selected answer #
            text = _("To '%(quest)s' '%(ans)s' would be the correct answer.") \
                    % { "ans" : answer, 
                    "quest" : self.quiz.get_question_to_answer(answer) }
            self.statusbar1.pop(self.statusbar_contextid["last_answer"])
            self.statusbar1.push(self.statusbar_contextid["last_answer"], text)

    def on_simple_question_button_clicked(self, widget, data=None):
        if self.quiz.check(self.simple_answer_entry.get_text().strip()):
            self.redisplay_correctly_answered(self.quiz.question)
            self.quiz.next()
        else:
            self.statusbar1.pop(self.statusbar_contextid["last_answer"])
    
    def on_flash_question_button_clicked(self, widget, date=None):
        self.flash_answer_label.set_text(
                self.quiz.question[self.quiz.answer_to])
        self.flash_notebook.set_current_page(1)

    def on_flash_answer_button_clicked(self, widget, data=None):
        if isinstance(self.quiz, Weighted_Quiz):
            self.quiz.set_answer_quality(
                    self.flash_answer_buttons.index(widget))
        self.quiz.next()


class Quiz_Filer(SaDrill):
    """
    Contains the parts of a quiz, that are not tested. A kind of "meta-data" as
    well as loading and saving.

    Note that the quiz-words are saved in a treestore.
    """

    def __init__(self, quiz_file_path=None):
        tag_dict = { "language" : self.on_tag_language, 
                "question" : self.on_tag_question, 
                "type" : self.on_tag_type,
                "media" : self.on_tag_media,
                "generator" : self.on_tag_generator }
        SaDrill.__init__(self, head_tag_dict=tag_dict, 
                mandatory_has_questions=True)
        self.SCORE_PATH = os.path.expanduser("~/.quizdrill/scores/")
        self.type = "vocabulary"
        self.all_subquizzes = []
        self.question_topic = [ _("What is this?"), _("What is this?") ]
        self.data_name = [ _("Question"), _("Answer") ]
        self.treestore = gtk.TreeStore(gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_BOOLEAN )
        if quiz_file_path != None:
            self.quiz_file_path = quiz_file_path
            quizlist = self.read_quiz_list(self.quiz_file_path)
            score = self.read_score_file()
        else:
            self.quiz_file_path = resource_filename(__name__, 
                    "../quizzes/no-file.drill")
            quizlist = [["", ""]]
            score = {"": 0}
        self.quiz = Weighted_Quiz(quizlist, score)
        self.quiz.next()

    # read and write files

    def read_score_file(self, type="", score_file=None):
        " Reads a score-file for a given quiz_file "
        if score_file == None:
            score_file = self._get_score_file(self.quiz_file_path, type)
        try:
            f = open(score_file)
        except IOError:
            return {}
        return pickle.load(f)

    def write_score_file(self, type=""):
        " Reads a score-file for a given quiz_file "
        if isinstance(self.quiz, Weighted_Quiz):
            score_file = self._get_score_file(self.quiz_file_path, type)
            if not os.path.exists(os.path.dirname(score_file)):
                os.makedirs(os.path.dirname(score_file))
            f = open(score_file, "w")
            pickle.dump(self.quiz.question_score, f)
            f.close()

    def _get_score_file(self, quiz_file, type):
        return self.SCORE_PATH + os.path.basename(quiz_file) + \
                '_' + type + ".score"

    def read_quiz_list(self, file):
        """
        Reads a .drill-file
        """
        # Read file and add to quizlist and treestore
        self.temp_quizlist = []
        self.temp_section = None
        self.parse(file)
        quizlist = self.temp_quizlist
        del self.temp_quizlist
        del self.temp_section
        return quizlist

    # SaDrill-API methods #

    def on_section(self, as_text, word_pair, tag=None, type='['):
        if len(word_pair) < 2:
            word_pair.append("")
        column = []; column.extend(word_pair)
        column.append(True)
        self.temp_section = self.treestore.append(None, column)

    def on_question(self, as_text, word_pair, tag=None, type=''):
        #assert len(word_pair) == 2, 'Fileformaterror in "%s": \
        #        Not exactly one "=" in line %s' % ( file, i+1 )
        self.temp_quizlist.append(word_pair)
        column = []; column.extend(word_pair)
        column.append(True)
        self.treestore.append(self.temp_section, column)

    # Process "heading-tags" on reading quiz-files [see read_quiz_list(file)] #

    def on_tag_language(self, as_text, word_pair, tag='language', type='!'):
        self.data_name = word_pair
        self.all_subquizzes = [ word_pair[0] + " → " + word_pair[1],
                word_pair[1] + " → " + word_pair[0] ]

    def on_tag_question(self, as_text, word_pair=["$what"], 
            tag='question', type='!'):
        common = { "$what" : _("What is this?"), 
                "$voc_test" : _("Please translate:") }
        if word_pair[0] in common:
            word_pair = [ common[word_pair[0]], common[word_pair[0]] ]
        elif len(word_pair) == 1:
            word_pair.append(word_pair[0])
        self.question_topic = word_pair

    def on_tag_type(self, as_text, word_pair=None, tag='type', type='!'):
        self.type = word_pair[0]

    def on_tag_media(self, as_text, word_pair, tag='media', type='!'):
        # TODO (Only needed with gstreamer support)
        pass

    def on_tag_generator(self, as_text, word_pair, tag='generator', type='!'):
        # TODO
        pass


class Quiz:
    """
    A simple random-selecting vocabulary test, with simple quiz and 
    multiple choice
    """
    DEFAULT_MULTICHOICE_LEN = 7

    def __init__(self, quiz_pool, ask_from=0, exam_length=15):
        self.listoners = {"break_time" : [], "question_changed" : [],
                "direction_changed" : [] }
        self.quiz_pool = []
        self.answered = 0
        self.correct_answered = 0
        self.exam_length = exam_length
        self.session_length = exam_length
        self.ask_from = ask_from
        self.answer_to = 1 - ask_from
        self.add_quizzes(quiz_pool)

    def connect(self, key, func):
        """ 
        Register a method func to be called when an event (key) happens.
        Possible keys are:
            'break_time'
            'question_changed'
        """
        self.listoners[key].append(func)

    def disconnect(self, key, func):
        """
        Unregister a method, previously registered with connect. See connect
        for more information.
        """
        if func in self.listoners[key]:
            self.listoners[key].remove(func)

    def notify(self, key):
        """ 
        Call the registered functions for a given key. See connect for
        more information.
        """
        for func in self.listoners[key]:
            func()

    def get_question_to_answer(self, answer):
        # Might get removed after release of 0.2.0, as it won't be needed.
        for q in self.quiz_pool:
            if q[self.answer_to] == answer:
                return q[self.ask_from]

    def new_question(self):
        """
        Discard current question and ask a new one. 
        """
        self.tries = 0
        self._select_question()
        self.multi_choices = self._gen_multi_choices()
        self.notify('question_changed')

    def next(self):
        """ ask next question """
        # Generate new Test
        self.new_question()
        # Time for relaxing ?
        if self.answered == self.session_length:
            self.session_length += self.exam_length
            self.notify('break_time')

    def _select_question(self):
        """ select next question """
        self.question = random.choice(self.quiz_pool)

    def _gen_multi_choices(self):
        """ Returns a list of multichoice options """
        # TODO: After 0.2.0 release we should change the multic_choice-list
        # to contain both answer and questions.
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
        """
        Set which part is the question and which the answer.
        Only makes sense with vocabulary-like quizzes.

        Note: Most likely you will want to ask for a next question.
        """
        if direction in [0, 1] and self.ask_from != direction:
            self.ask_from = direction
            self.answer_to = 1 - direction
            self.notify('direction_changed')

    def add_quizzes(self, new_quizzes):
        self.quiz_pool.extend(new_quizzes)
        self._refit_multichoice_len()

    def remove_quizzes(self, rm_quizzes):
        for quiz in rm_quizzes:
            self.quiz_pool.remove(quiz)
        self._refit_multichoice_len()
        if self.question in rm_quizzes:
            self.new_question()
        else:
            for mc in self.multi_choices:
                for rm in rm_quizzes:
                    if rm[self.answer_to] == mc:
                        self.new_question()
                        return

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
        """ selcet next question """
        while True:
            Quiz._select_question(self)
            bound = random.random() * 1.01     # to avoid infinit loops
            if self.question_score[self.question[self.ask_from]] <= bound:
                return

    def check(self, solution):
        """ 
        Check if a given answer is correct.

        Note: This changes the score of a given question (on correct answers).
        """
        if Quiz.check(self, solution):
            self._update_score(self.question[self.ask_from], 
                    self.tries == 0)
            return True
        else:
            return False

    def set_answer_quality(self, quality):
        """
        The equivalent to 'check' for flashcard tests. 0: Wrong, 1: Correct.
        
        Future: Rating will be on a score from 0 (worst) to 5 (best) for the 
        SM-2 Algor.
        """
        self._update_score(self.question[self.ask_from], quality == 1)

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
            if quiz in self.new_quiz_pool:
                self.new_quiz_pool.remove(quiz)
            else:
                rm_scored_quizzes.append(quiz)
        Weighted_Quiz.remove_quizzes(self, rm_scored_quizzes)
        self._insure_min_quiz_num()


def main():
    gui = Gui()
    gtk.main()

if __name__ == "__main__":
    main()
