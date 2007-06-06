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

from SaDrill import SaDrillError
from quiz import Weighted_Quiz
from Quiz_Filer import Quiz_Filer, Quiz_Loader

import pygtk
pygtk.require('2.0')
import gobject, gtk, gtk.glade
import random
import os, os.path
from pkg_resources import resource_filename
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

class Gui(object):
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
            self.quiz_filer_list.append(
                    Quiz_Loader(quiz_file_path).read_quiz_file())
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
            button.set_label(text[self.quiz.answer_to])
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
        if not quiz_filer.quiz_type in self.SHOW_TABS:
            print _('Warning: unknown quiz type "%s".') % quiz_filer.quiz_type
            quiz_type = "all"
        else:
            quiz_type = self.quiz_filer.quiz_type
        for tab, visi in zip(self.main_notbook_tabs.itervalues(),
                self.SHOW_TABS[quiz_type]):
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
        self.quiz_filer.toggle_questions(path)

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
                    % { "ans" : answer, "quest" : \
                    self.quiz.get_question_to_answer_from_multichoices(answer)
                    }
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


class Gui_Statistics(object):
    GLADE_FILE = resource_filename(__name__, "data/quizdrill.glade")

    def __init__(self, quiz_filer):
        xml = gtk.glade.XML(self.GLADE_FILE, "statistics_window", APP)
        gw = xml.get_widget
        window = gw("statistics_window")
        vbox = gw("statistics_vbox")
        treeview = gw("statistics_treeview")
        treestore = gtk.TreeStore(str, str)
        for i, title in enumerate(quiz_filer.data_name):
            tvcolumn = gtk.TreeViewColumn(title,
                    gtk.CellRendererText(), text=i)
            treeview.append_column(tvcolumn)
        print quiz_filer.quiz.get_worst_scores(5)
        for score, quiz in quiz_filer.quiz.get_worst_scores(5):
            treestore.append(None, quiz)
        treeview.set_model(treestore)


def main():
    gui = Gui()
    gtk.main()

if __name__ == "__main__":
    main()
