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

from quiz import Quiz, Weighted_Quiz, Queued_Quiz
import re

import unittest
from pmock import Mock, once, at_least_once, never

class Test_Quiz(unittest.TestCase):
    """
    Unittest for the class Quiz.
    """
    CLASS_TO_TEST = Quiz
    QUIZ_POOL = [ [ str(i), str(i*10) ] for i in range(10) ]

    def setUp(self):
        self.quiz = self.CLASS_TO_TEST(self.QUIZ_POOL[:])
        self.mock_listener = Mock()
        self.quiz.connect('break_time', self.mock_listener.break_time)
        self.quiz.connect('question_changed', 
                self.mock_listener.question_changed)

    ## Test add_quizzes and remove_quizzes ##

    def test_add_and_remove_quizzes(self):
        """
        Check that adding and removing quizzes come back to status quo.
        """
        old_quiz_pool = self.quiz.quiz_pool[:]
        new_quizzes = [ [ i , i * 100 ] for i in range(10, 20) ]
        self.quiz.add_quizzes(new_quizzes)
        self.quiz.remove_quizzes(new_quizzes)
        assert old_quiz_pool == self.quiz.quiz_pool, \
                "quiz_pool changed after adding then removing " \
                "%s from %s to %s" % \
                (new_quizzes, old_quiz_pool, self.quiz.quiz_pool)

    def test_remove_and_add_quizzes(self):
        """
        Removing all questions and then adding them again.
        """
        old_quiz_pool = self.quiz.quiz_pool[:]
        # Removing all questions #
        self.mock_listener.expects(once()).question_changed()
        self.quiz.remove_quizzes(self.quiz.quiz_pool[:])
        assert self.quiz.quiz_pool == [ ], \
                "quiz_pool still has %s after removing all quizzes" % \
                self.quiz.quiz_pool
        assert self.quiz.question == [ '', '' ], \
                "Non-empty question left though empty quiz_pool."
        # Adding original quizzes back. #
        self.mock_listener.expects(once()).question_changed()
        self.quiz.add_quizzes(old_quiz_pool[:])
        assert self.quiz.quiz_pool == old_quiz_pool, \
                "Adding %s to an empty quiz_pool leads to %s." % \
                (old_quiz_pool, self.quiz.quiz_pool)

    def test_remove_quizzes_from_multiple_choices(self):
        """
        Removing questions in the list of multiple choices.
        """
        self.mock_listener.expects(once()).question_changed()
        self.quiz.remove_quizzes([ self.quiz.multi_choices[0] ])
        self.mock_listener.expects(once()).question_changed()
        self.quiz.remove_quizzes([ self.quiz.multi_choices[-1] ])
        self.mock_listener.expects(once()).question_changed()
        self.quiz.remove_quizzes([ self.quiz.question ])
        assert self.quiz.question in self.quiz.quiz_pool, \
                "Question not in quiz_pool."

    def test_remove_quizzes_not_from_multiple_choices(self):
        """
        Removing questions NOT in the list of multiple choices shouldn't 
        change multiple choice list.
        """
        self.mock_listener.expects(never()).question_changed()
        self.quiz = Quiz(self.QUIZ_POOL[:])
        old_multi_choices = self.quiz.multi_choices[:]
        old_question = self.quiz.question[:]
        quiz_list = self.QUIZ_POOL[:]
        for quiz in old_multi_choices:
            quiz_list.remove(quiz)
        for quiz in quiz_list:
            self.quiz.remove_quizzes([quiz])
            assert self.quiz.multi_choices == old_multi_choices, \
                    "Multiple choice options changed after removing other "\
                    "quizzes. " "New: %s; Old: %s; Removed: %s." % \
                    (self.quiz.multi_choices, old_multi_choices, quiz)

    ## Single Method Tests ##

    hint_place_holder = '-'

    def test_first_hint_should_be_blank(self):
        """
        Test that hint() starts with letters replaced by underscores.
        """
        solution = self.quiz.question[self.quiz.answer_to]
        first_hint = self.quiz.hint()
        assert first_hint == re.sub('\w', self.hint_place_holder, solution)

    def test_hint_adds_two_lettres_each_time(self):
        """
        Test that hint starts with letters replaced by underscores and gives 
        two letters each next hint.
        """
        solution = self.quiz.question[self.quiz.answer_to]
        first_hint = self.quiz.hint()
        next_hint = first_hint
        for hint_num in \
                range((first_hint.count(self.hint_place_holder) + 1) // 2):
            assert next_hint.count(self.hint_place_holder) + hint_num * 2 == \
                    first_hint.count(self.hint_place_holder), \
                    ("Hint no. %s gives %s letters, but %s should have been " +
                            "given." )% \
                    (hint_num, first_hint.count(self.hint_place_holder) - 
                            next_hint.count(self.hint_place_holder), \
                            hint_num * 2)
            next_hint = self.quiz.hint(next_hint)
        assert next_hint == solution, \
                'Final hint ("%s") is not the solution ("%s").' % \
                (next_hint, solution)

    def test_hint_with_double_lettres(self):
        """
        Run previous test (test_hint_adds_two_lettres_each_time) with '0000'
        as double letters make comparison of solution and hint non-trivial.
        """
        self.quiz.question = ['0000', '0000']
        self.test_hint_adds_two_lettres_each_time()

    def test_invalid_previous_hint(self):
        """
        Test that a string which wasn't a hint still gives a valid hint.
        """
        solution = self.quiz.question[self.quiz.answer_to]
        first_hint = self.quiz.hint("spam")
        for hint_letter, solution_letter in zip(first_hint, solution):
            assert hint_letter == self.hint_place_holder or \
                    hint_letter == solution_letter, \
                    'Hint ("%s") does not match solution ("%s").' % \
                    (first_hint, solution)

    def test_hint_increments_tries(self):
        """
        Test that a hint counts as a try.
        """
        assert self.quiz.tries == 0
        self.quiz.hint()
        assert self.quiz.tries == 1
        self.quiz.hint()
        assert self.quiz.tries == 2

    def test_hint_does_not_change_correct_answer(self):
        assert self.quiz.hint(self.quiz.question[self.quiz.answer_to]) == \
                self.quiz.question[self.quiz.answer_to]

    def test_check(self):
        assert self.quiz.check(self.quiz.question[self.quiz.answer_to])

    def test__gen_multi_choices(self):
        multi_choices = self.quiz._gen_multi_choices()
        assert self.quiz.question in multi_choices, \
                "Question %s not in multiple choice options %s." % \
                (self.quiz.question, multi_choices)

    def test__gen_multi_choices_has_no_answers_double(self):
        """Test that no answers are double in multi_choices."""
        multi_choices = self.quiz._gen_multi_choices()
        for i, choice in enumerate(multi_choices):
            assert not choice in multi_choices[i+1:], \
                    '"%s" is double in multi_choices ("%s").' % \
                    (choice, multi_choices)

    def test__refit_multichoice_len(self):
        """
        Test length of multi_choices
        """
        self.mock_listener.expects(at_least_once()).question_changed()
        assert len(self.quiz.multi_choices) == self.quiz.DEFAULT_MULTICHOICE_LEN
        self.quiz.remove_quizzes(
                self.quiz.quiz_pool[self.quiz.DEFAULT_MULTICHOICE_LEN:])
        assert len(self.quiz.multi_choices) == \
                self.quiz.DEFAULT_MULTICHOICE_LEN, \
                "self.quiz.multi_choices has wrong length: %s instead of %s." \
                % (len(self.quiz.multi_choices), \
                self.quiz.DEFAULT_MULTICHOICE_LEN)
        self.quiz.remove_quizzes(
                self.quiz.quiz_pool[3:self.quiz.DEFAULT_MULTICHOICE_LEN])
        assert len(self.quiz.multi_choices) == 3, \
            "self.quiz.multi_choices has wrong length: %s instead of 3." % \
            len(self.quiz.multi_choices)
        self.quiz.remove_quizzes(self.quiz.quiz_pool[:3])
        assert len(self.quiz.multi_choices) == 1

    def test_get_answer_to_question(self):
        answer_to = self.quiz.answer_to
        ask_from = self.quiz.ask_from

        for question_pair in self.QUIZ_POOL:
            assert question_pair[answer_to] == \
                    self.quiz.get_answer_to_question(question_pair[ask_from]),\
                    "%s should be answer to question %s." % \
                    (question_pair[answer_to], question_pair[ask_from])

    def test_get_question_to_answer_from_multichoices(self):
        answer_to = self.quiz.answer_to
        ask_from = self.quiz.ask_from

        for question_pair in self.quiz.multi_choices:
            assert question_pair[answer_to] == \
                    self.quiz.get_answer_to_question(question_pair[ask_from]),\
                    "%s should be answer to question %s." % \
                    (question_pair[answer_to], question_pair[ask_from])

    def test_get_question_to_answer(self):
        answer_to = self.quiz.answer_to
        ask_from = self.quiz.ask_from

        for question_pair in self.QUIZ_POOL:
            assert question_pair[ask_from] == \
                    self.quiz.get_question_to_answer(question_pair[answer_to]),\
                    "%s should be question to answer %s." % \
                    (question_pair[ask_from], question_pair[answer_to])

    def test_notify(self):
        """
        Tests that new_question and next notify properly.
        """
        # test_new_question #
        for i in range(self.quiz.session_length * 2):
            self.mock_listener.expects(once()).question_changed()
            self.quiz.new_question()
        # test_next #
        for i in range(self.quiz.session_length - 1):
            self.mock_listener.expects(once()).question_changed()
            self.quiz.next()
        self.mock_listener.expects(once()).question_changed()
        self.mock_listener.expects(once()).break_time()
        self.quiz.next()

    #def test_set_question_direction(self):


class Test_Weighted_Quiz(Test_Quiz):
    """
    Unittest for the class Weighted_Quiz without predefined scores.
    """
    CLASS_TO_TEST = Weighted_Quiz

    def setUp(self):
        self.quiz = self.CLASS_TO_TEST(self.QUIZ_POOL[:])
        self.mock_listener = Mock()
        self.quiz.connect('break_time', self.mock_listener.break_time)
        self.quiz.connect('question_changed', 
                self.mock_listener.question_changed)

    #def add_quizzes(self):
    #def check(self):
    #def _gen_score_sum(self):
    #def get_worst_scores(self):
    #def remove_quizzes(self):
    #def _select_question(self):
    #def set_answer_quality(self):
    #def set_question_direction(self):
    #def _update_score(self):

class Test_Weighted_Quiz_with_scores(Test_Weighted_Quiz):
    """
    Unittest for the class Weighted_Quiz with predefined scores.

    questions form 0 to 29 with:
        0..9: Has no score; is selected.
        10..19: Has score; is selected.
        20..29: Has score; isn't selected.
        30..39: Has no score; isn't selected.
    """
    NOT_SELECTED_SCORED_QUIZZES = [ [str(i), str(i*10)] for i in range(20, 30) ]
    NOT_SELECTED_NOT_SCORED_QUIZZES = [ [str(i), str(i*10)] 
            for i in range(30, 40) ]
    QUIZ_POOL = [ [ str(i), str(i*10) ] for i in range(20) ]

    def setUp(self):
        self.SCORE = {}
        for question in range(10, 30):
            self.SCORE[question] = question / 10.
        self.quiz = self.CLASS_TO_TEST(self.QUIZ_POOL[:], self.SCORE)
        self.mock_listener = Mock()
        self.quiz.connect('break_time', self.mock_listener.break_time)
        self.quiz.connect('question_changed', 
                self.mock_listener.question_changed)


class Test_Queued_Quiz(Test_Weighted_Quiz_with_scores):
    """
    Unittest for the class Queued_Quiz.
    """
    CLASS_TO_TEST = Queued_Quiz

    #def add_quizzes(self):
    #def _increase_quiz_pool(self):
    #def _insure_min_quiz_num(self):
    #def remove_quizzes(self):
    #def _select_question(self):
    #def _update_score(self):


def testsuite():
    suite = unittest.TestSuite()
    for test in [ Test_Quiz, Test_Weighted_Quiz, 
            Test_Weighted_Quiz_with_scores, Test_Queued_Quiz ]:
        suite.addTest(unittest.makeSuite(test))
    return suite


if __name__ == '__main__':
    unittest.main()
