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
from quiz import Weighted_Quiz, Notifier
from Quiz_Filer import Quiz_Filer, Quiz_Loader

import pygtk
pygtk.require('2.0')
import gobject, gtk, gtk.glade
import random
import os, os.path
from pkg_resources import resource_filename
try:
    import gconf
    HAS_GCONF = True
except:
    HAS_GCONF = False

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

    def __init__(self):
        self.timer_id = 0
        self.quiz_filer_list = []
        # gconf #
        self.gconf_watcher = Gconf_Prefs()
        quiz_file_path = self.gconf_watcher.gconf_client.get_string(
                self.gconf_watcher.DEFAULT_QUIZ_KEY)
        # widgets #
        xml = gtk.glade.XML(self.GLADE_FILE, "main_window", APP)
        gw = xml.get_widget
        self.main_window = gw("main_window")
        self.edit_menuitem = gw("edit_menuitem")
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
        # connect signals #
        xml.signal_autoconnect(self)
        self.load_quiz(quiz_file_path)

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
        for button in self.multi_question_buttons:
            button.set_label('-')
            button.set_sensitive(False)
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
        # show and hide notebookpanels #
        if quiz_filer.quiz_type in self.SHOW_TABS:
            quiz_type = self.quiz_filer.quiz_type
        else:
            print _('Warning: unknown quiz type "%s".') % quiz_filer.quiz_type
            quiz_type = "all"
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
        self.update_gui()

    # Timer #

    def start_relax_time(self, break_length=None, minimize=True):
        """
        Iconify window as a break and deiconify it when it's over

        Note: There is a race condition. However this should be harmless
        """
        def ms2min(ms):
            """
            Convert milliseconds to minutes.
            """
            return ms * 60000

        if not self.gconf_watcher.use_timer:
            return
        if break_length == None:
            break_length = self.gconf_watcher.break_length
        if self.timer_id:
            gobject.source_remove(self.timer_id)
        if minimize:
            self.main_window.iconify()
        self.timer_id = gobject.timeout_add(ms2min(break_length), 
                self.on_end_relax_time)

    def on_end_relax_time(self):
        self.main_window.deiconify()
        self.timer_id = 0

    # main_window handlers #

    ## all (or indebendant of) tabs ##

    def on_quit(self, widget):
        for filer in self.quiz_filer_list:
            filer.write_score_file()
        self.gconf_watcher.save_quiz_path(self.quiz_filer.file_path)
        gtk.main_quit()

    def on_main_window_window_state_event(self, widget, event):
        """ Snooze when minimized """
        if 'iconified' in event.new_window_state.value_nicks and \
                not self.timer_id:
            self.start_relax_time(self.gconf_watcher.snooze_length, False)
        elif not 'iconified' in event.new_window_state.value_nicks \
                and self.timer_id:
            gobject.source_remove(self.timer_id)
            self.timer_id = 0

    def on_about_activate(self, widget):
        gtk.glade.XML(self.GLADE_FILE, "aboutdialog1", APP)

    def on_preferences1_activate(self, widget):
        Gui_Preferences()

    def on_open1_activate(self, widget):
        "Creates an Open-File-Dialog, which selects a new Quiz"
        chooser = gtk.FileChooserDialog("Open Quiz", None, 
                gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, 
                gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        try:
            last_quiz_dir_path = os.path.abspath(os.path.dirname(
                self.quiz_filer.file_path))
        except AttributeError:
            pass
        else:
            chooser.set_current_folder(last_quiz_dir_path)
        response = chooser.run()
        chooser.hide()
        if response == gtk.RESPONSE_OK:
            try:
                self.load_quiz(chooser.get_filename())
            except (IOError, SaDrillError), e:
                message = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, 
                        buttons=gtk.BUTTONS_OK, message_format=e.str)
                message.run()
                message.destroy()
        chooser.destroy()

    def load_quiz(self, quiz_path):
        """
        Load the given quiz. 
        """
        self.quiz_filer_list = [ Quiz_Loader(quiz_path).read_quiz_file() ]
        self.switch_quiz(self.quiz_filer_list[0])

    def on_main_notebook_switch_page(self, widget, gpointer, new_tab):
        if new_tab == 2:  # "Simple Quiz"-tab
            self.simple_question_button.grab_default()

    ## words-/settings-tab ##

    def on_subquiz_combobox_changed(self, widget):
        new_status = widget.get_active()
        self.main_window.set_title(_('Quiz') + ': ' + widget.get_active_text())
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
    
    def on_simple_question_hint_button_clicked(self, widget, data=None):
        self.simple_answer_entry.set_text(
                self.quiz.hint(self.simple_answer_entry.get_text().strip()))

    def on_flash_question_button_clicked(self, widget, date=None):
        self.flash_answer_label.set_text(
                self.quiz.question[self.quiz.answer_to])
        self.flash_notebook.set_current_page(1)

    def on_flash_answer_button_clicked(self, widget, data=None):
        if isinstance(self.quiz, Weighted_Quiz):
            self.quiz.set_answer_quality(
                    self.flash_answer_buttons.index(widget))
        self.quiz.next()


class Gconf_Prefs(object):
    """
    Processes loading, saving and watching of gconf-keys. Gives nice default
    values if gconf is not availible.
    """
    DIR_KEY = '/apps/quizdrill/timer'
    USE_TIMER_KEY = DIR_KEY + '/use_timer'
    EXAM_LENGTH_KEY = DIR_KEY + '/exam_length'
    BREAK_LENGTH_KEY = DIR_KEY + '/break_length'
    SNOOZE_LENGTH_KEY = DIR_KEY + '/snooze_length'
    DEFAULT_QUIZ_KEY = DIR_KEY + '/default_quiz'
    #
    GCONF_KEYS = [ USE_TIMER_KEY, EXAM_LENGTH_KEY, BREAK_LENGTH_KEY, 
            SNOOZE_LENGTH_KEY, DEFAULT_QUIZ_KEY ]
    NOTIFIER_KEYS = [ 'use_timer', 'exam_length', 'break_length', 
            'snooze_length', 'default_quiz' ]

    def __init__(self):
        # Notifier #
        self.notifier = Notifier(self.NOTIFIER_KEYS)
        self.notify = self.notifier.notify
        self.connect = self.notifier.connect
        self.disconnect = self.notifier.disconnect
        #
        if HAS_GCONF:
            self.gconf_client = gconf.client_get_default()
            self.quiz_file_path = \
                    self.gconf_client.get_string(self.DEFAULT_QUIZ_KEY)
            self.use_timer = self.gconf_client.get_bool(self.USE_TIMER_KEY)
            self.exam_length = self.gconf_client.get_int(self.EXAM_LENGTH_KEY)
            self.break_length = \
                    self.gconf_client.get_int(self.BREAK_LENGTH_KEY)
            self.snooze_length = \
                    self.gconf_client.get_int(self.SNOOZE_LENGTH_KEY)
            self.gconf_client.add_dir(self.DIR_KEY, gconf.CLIENT_PRELOAD_NONE)
            for gconf_key, notifier_key in zip(self.GCONF_KEYS, 
                    self.NOTIFIER_KEYS):
                self._add_listener(gconf_key, 
                        notifier_key, self.value_is_in_range)
            for notifier_key in self.NOTIFIER_KEYS:
                self.connect(notifier_key, self.on_key_changed)
        else:
            self.edit_menuitem.set_visibility(False)
            # Default values #
            self.use_timer = True
            self.exam_length = 20
            self.break_length = 15
            self.snooze_length = 5
            self.quiz_file_path = resource_filename(__name__, 
                    '../quizzes/deu-fra.drill')
        if not os.path.exists(self.quiz_file_path):
            self.quiz_file_path = None

    def save_quiz_path(self, path):
        """
        Saves the given path to gconf.
        """
        try:
            self.gconf_client.set_string(self.DEFAULT_QUIZ_KEY, path)
            return True
        except:
            return False

    def _add_listener(self, gconf_key, notifier_key, eval_func=None):
        """
        Connects the gconf-notify with the notifier. For information about 
        eval_func see _report_gconf_changed.
        """
        self.gconf_client.notify_add(gconf_key, self._report_gconf_changed, 
                [gconf_key, notifier_key, eval_func])

    def _report_gconf_changed(self, client, gconf_id, gconf_entry, 
            keys, **kwargs):
        """
        Reports to the notifier, what a gconf-key changed to if it's new 
        value is feasible. Keys should be a tuple of the gconf_key, 
        notifier_key and a function which evaluates if the new value is 
        feasible (returning True of False, given gconf_key and new_value).
        """
        gconf_key, notifier_key, eval_func = keys
        new_value = client.get_value(gconf_key)
        if eval_func == None or eval_func(gconf_key, new_value):
            self.notify(notifier_key, [notifier_key, new_value])

    def value_is_in_range(self, gconf_key, new_value):
        range_dict = {
                self.USE_TIMER_KEY: [ False, None ],
                self.EXAM_LENGTH_KEY: [ 5, 100 ],
                self.BREAK_LENGTH_KEY: [ 0, 600 ],
                self.SNOOZE_LENGTH_KEY: [ 0, 300 ],
                self.DEFAULT_QUIZ_KEY: [ '', None ] 
                }
        min_value, max_value = range_dict[gconf_key]
        if type(min_value) == type(new_value) and (max_value == None or \
                min_value <= new_value <= max_value):
            return True
        else:
            return False

    def on_key_changed(self, message):
        """Update to the new value."""
        notifier_key, new_value = message
        self.__setattr__(notifier_key, new_value)


class Gui_Statistics(object):
    """
    The statistics window.
    """
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

class Gui_Preferences(object):
    GLADE_FILE = resource_filename(__name__, "data/quizdrill.glade")
    DIR_KEY = '/apps/quizdrill/timer'
    USE_TIMER_KEY = DIR_KEY + '/use_timer'
    EXAM_LENGTH_KEY = DIR_KEY + '/exam_length'
    BREAK_LENGTH_KEY = DIR_KEY + '/break_length'
    SNOOZE_LENGTH_KEY = DIR_KEY + '/snooze_length'
    DEFAULT_QUIZ_KEY = DIR_KEY + '/default_quiz'

    def __init__(self):
        xml = gtk.glade.XML(self.GLADE_FILE, "pref_window", APP)
        gw = xml.get_widget
        self.window = gw("pref_window")
        self.use_timer_checkbutton = gw("use_timer_checkbutton")
        self.timer_subprefs_table = gw("timer_subprefs_table")
        self.exam_length_spinbutton = gw("exam_length_spinbutton")
        self.break_length_spinbutton = gw("break_length_spinbutton")
        self.snooze_length_spinbutton = gw("snooze_length_spinbutton")
        xml.signal_autoconnect(self)
        # gconf #
        self.gconf_client = gconf.client_get_default()
        self.set_use_timer(self.gconf_client.get_bool(self.USE_TIMER_KEY))
        for widget, key in [
                [ self.exam_length_spinbutton, self.EXAM_LENGTH_KEY ], 
                [ self.break_length_spinbutton, self.BREAK_LENGTH_KEY ],
                [ self.snooze_length_spinbutton, self.SNOOZE_LENGTH_KEY ]]:
            widget.set_value(self.gconf_client.get_int(key))
        self.gconf_client.add_dir(self.DIR_KEY, gconf.CLIENT_PRELOAD_NONE)
        self.gconf_client.notify_add(self.USE_TIMER_KEY, 
                self.use_timer_listener)
        for widget, key in [
                [ self.exam_length_spinbutton, self.EXAM_LENGTH_KEY ],
                [ self.break_length_spinbutton, self.BREAK_LENGTH_KEY ],
                [ self.snooze_length_spinbutton, self.SNOOZE_LENGTH_KEY]]:
            self.gconf_client.notify_add(key, self.timer_lengths_listener, 
                    [ widget, key ])

    def on_use_timer_checkbutton_toggled(self, widget):
        is_active = widget.get_active()
        self.timer_subprefs_table.set_sensitive(is_active)
        self.gconf_client.set_bool(self.USE_TIMER_KEY, is_active)

    def set_use_timer(self, value):
        self.timer_subprefs_table.set_sensitive(value)
        self.use_timer_checkbutton.set_active(value)

    def use_timer_listener(self, client, *args, **kwargs):
        self.set_use_timer(client.get_bool(self.USE_TIMER_KEY))

    def timer_lengths_listener(self, client, gconf_id, gconf_entry, 
            widget_key_pair, **kwargs):
        widget, key = widget_key_pair
        widget.set_value(client.get_int(key))

    def on_exam_length_spinbutton_value_changed(self, widget):
        self.gconf_client.set_int(self.EXAM_LENGTH_KEY, 
                widget.get_value_as_int())

    def on_break_length_spinbutton_value_changed(self, widget):
        self.gconf_client.set_int(self.BREAK_LENGTH_KEY, 
                widget.get_value_as_int())

    def on_snooze_length_spinbutton_value_changed(self, widget):
        self.gconf_client.set_int(self.SNOOZE_LENGTH_KEY, 
                widget.get_value_as_int())

    def on_close_preferences_button_clicked(self, widget):
        self.window.destroy()


def main():
    gui = Gui()
    gtk.main()

if __name__ == "__main__":
    main()
