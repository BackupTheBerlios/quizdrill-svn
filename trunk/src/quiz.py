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

import random
import re
from difflib import SequenceMatcher
import gettext
_ = gettext.gettext

class Notifier(object):
    def __init__(self, keys):
        self.listoners = {}
        for new_key in keys:
            self.listoners[new_key] = []

    def connect(self, key, func):
        """ 
        Register a method func to be called when an event (key) happens.
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


class Quiz(object):
    """
    A simple random-selecting vocabulary test, with simple quiz and 
    multiple choice
    """
    DEFAULT_MULTICHOICE_LEN = 7

    def __init__(self, quiz_pool, ask_from=0, exam_length=15):
        self.notifier = Notifier(["break_time", "question_changed", 
            "direction_changed"])
        self.notify = self.notifier.notify
        self.connect = self.notifier.connect
        self.disconnect = self.notifier.disconnect
        #
        self.quiz_pool = []
        self.answered = 0
        self.correct_answered = 0
        self.exam_length = exam_length
        self.session_length = exam_length
        self.ask_from = ask_from
        self.answer_to = 1 - ask_from
        self.add_quizzes(quiz_pool)

    def get_answer_to_question(self, question):
        """
        Finds an answer to the given question from the pool of all 
        quizzes.
        """
        for q in self.quiz_pool:
            if q[self.ask_from] == question:
                return q[self.answer_to]
        else:
            return None

    def get_question_to_answer(self, answer):
        """
        Finds a question to the given answer from the pool of all 
        quizzes. If possible use get_question_to_answer_from_multichoices() 
        instead as it is a lot faster.
        """
        for q in self.quiz_pool:
            if q[self.answer_to] == answer:
                return q[self.ask_from]
        else:
            return None

    def get_question_to_answer_from_multichoices(self, answer):
        """
        Finds a question to the given answer from the current quizzes in the 
        multi_choices-pool. 
        """
        for q in self.multi_choices:
            if q[self.answer_to] == answer:
                return q[self.ask_from]
        else:
            return None

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
        if self.quiz_pool:
            self.question = random.choice(self.quiz_pool)
        else:
            self.question = [ "", "" ]

    def _gen_multi_choices(self):
        """ Returns a list of multichoice options """
        choices = [ self.question ]
        while len(choices) < self.multichoice_len:
            r = random.randrange(len(self.quiz_pool))
            quest_pair = random.choice(self.quiz_pool)
            if not quest_pair in choices:
                choices.append(quest_pair)
        random.shuffle(choices)
        return choices

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
        """
        Add a list of new quizzes.
        """
        pool_was_small = len(self.quiz_pool) < self.DEFAULT_MULTICHOICE_LEN
        self.quiz_pool.extend(new_quizzes)
        self._refit_multichoice_len()
        if pool_was_small:
            self.new_question()

    def remove_quizzes(self, rm_quizzes):
        for quiz in rm_quizzes:
            self.quiz_pool.remove(quiz)
        for mc in self.multi_choices:
            if mc in rm_quizzes:
                self._refit_multichoice_len()
                self.new_question()
                return

    def _refit_multichoice_len(self):
        if len(self.quiz_pool) < self.DEFAULT_MULTICHOICE_LEN:
            self.multichoice_len = len(self.quiz_pool)
        else:
            self.multichoice_len = self.DEFAULT_MULTICHOICE_LEN

    def hint(self, previous_hint=None):
        """
        Gives a hint to the current question. If previous_hint is given it will
        use difflib to take over the "correct" parts, fill the rest with 
        underscores and fill in two additional letters. Otherwise all letters
        will be replaces with underscores.
        """
        def differ_only_in_underscores(first_text, second_text):
            if len(first_text) != len(second_text):
                return False
            else:
                for first_char, second_char in zip(first_text, second_text):
                    if first_char != second_char and first_char != '_':
                        return False
                return True
            
        self.tries += 1
        correct_answer = self.question[self.answer_to]
        if previous_hint == None or previous_hint == '':
            return re.sub('\w', '_', correct_answer)
        else:
            if differ_only_in_underscores(previous_hint, correct_answer):
                if previous_hint.count('_') <= 2:
                    return correct_answer
                else:
                    index_of_underscores = []
                    for i, char in enumerate(previous_hint):
                        if char == '_':
                            index_of_underscores.append(i)
                    L = random.sample(index_of_underscores, 2)
                    L.sort()
                    i, j = L
                    return previous_hint[:i] + correct_answer[i] + \
                            previous_hint[i+1:j] + correct_answer[j] + \
                            previous_hint[j+1:]
            else:
                hint_string = ''
                s = SequenceMatcher('', previous_hint, correct_answer)
                for opcode in s.get_opcodes():
                    if opcode[0] == 'insert' or opcode[0] == 'replace':
                        hint_string += re.sub('\w', '_', 
                                correct_answer[opcode[3]:opcode[4]])
                    elif opcode[0] == 'equal':
                        hint_string += correct_answer[opcode[3]:opcode[4]]
                return hint_string


class Weighted_Quiz(Quiz):
    """
    A quiz with weighted question selection of a vocabulary test. The more 
    questions are answered wrong (in comparison to the other questions the 
    more often they are asked. More recent answers are weighted stronger.

    score is form 0 (worst) to 1 (best).

    The score is recorded by question (as opposed to by answer) as 
    non-vocabulary answers may be identical.
    """

    EMPTY_SCORE = {'': 0.}

    def __init__(self, quiz_pool, 
            question_score=None, ask_from=0, exam_length=15):
        if question_score == None:
            self.question_score = self.EMPTY_SCORE
        else:
            self.question_score = question_score
        self.score_sum = 0.
        super(Weighted_Quiz, self).__init__(quiz_pool, ask_from, exam_length)
        self.score_sum = self._gen_score_sum()

    def _select_question(self):
        """ select next question """
        while True:
            super(Weighted_Quiz, self)._select_question()
            bound = random.random() * 1.01     # to avoid infinit loops
            if not self.question[self.ask_from] in self.question_score or \
                    self.question_score[self.question[self.ask_from]] <= bound:
                return

    def check(self, solution):
        """ 
        Check if a given answer is correct.

        Note: This changes the score of a given question (on correct answers).
        """
        if super(Weighted_Quiz, self).check(solution):
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
        Updates the score (and score_sum) of word, depending on whether
        it was answered correctly.
        """
        self.score_sum -= self.question_score[word]
        self.question_score[word] = (self.question_score[word] * 3
                + correct_answered ) / 4
        self.score_sum += self.question_score[word]

    def _gen_score_sum(self, quizzes=None, cleanup=False):
        """ 
        Creates the sum of all sores in quiz_pool in the current question 
        direction and fills all unknown scores with 0. If cleanup=True it
        also removes scores without a corresponding question.
        """
        score_sum = 0.
        if quizzes == None:
            quizzes = self.quiz_pool
        question_score_copy = self.question_score.copy()
        for question in quizzes:
            if question[self.ask_from] in question_score_copy:
                score_sum += question_score_copy[question[self.ask_from]]
                question_score_copy.pop(question[self.ask_from])
            else:
                self.question_score[question[self.ask_from]] = 0.
        if cleanup:
            for score_without_question in question_score_copy:
                self.question_score.pop(score_without_question)
        return score_sum

    def set_question_direction(self, direction, score_dict=None):
        super(Weighted_Quiz, self).set_question_direction(direction)
        if score_dict != None:
            self.question_score = score_dict
        self.score_sum = self._gen_score_sum()

    def add_quizzes(self, new_quizzes):
        super(Weighted_Quiz, self).add_quizzes(new_quizzes)
        self.score_sum += self._gen_score_sum(new_quizzes)

    def remove_quizzes(self, rm_quizzes):
        super(Weighted_Quiz, self).remove_quizzes(rm_quizzes)
        self.score_sum -= self._gen_score_sum(rm_quizzes)

    def get_worst_scores(self, n):
        """
        Returns the n quizzes with the worst score including the score:
            [ [ worst_score, [worst_question, worst_answer] ], ... ].
        """
        low_scored = []
        for quiz in self.quiz_pool[:n]:
            low_scored.append( 
                    [ self.question_score[quiz[self.ask_from]], quiz ] )
        low_scored.sort()
        best_low_score = low_scored[-1][0]

        for question, score in self.quiz_pool[n:]:
            if score < best_low_score:
                for index, badly_scored in enumerate(low_scored):
                    if score > badly_scored[0]:
                        low_scored.insert(index, [ score, question ])
                        low_scored = low_scored[:n]
                        best_low_score = low_scored[-1][0]
                        break
        return low_scored


class Queued_Quiz(Weighted_Quiz):
    """ 
    Previously not asked questions are added one-after-each-other once only a 
    few questions still are below a certain score.
    """
    def __init__(self, question_pool, question_score=None, ask_from=0, 
            exam_length=15, bad_score=.4, min_num_bad_scores=3, 
            min_question_num=20, batch_length=5):
        self.new_quiz_pool = []
        self.num_bad_scores = 0
        self.bad_score = bad_score
        self.min_num_bad_scores = min_num_bad_scores
        self.min_question_num = min_question_num
        self.batch_length = batch_length
        super(Queued_Quiz, self).__init__([], question_score, ask_from, 
                exam_length)
        self.add_quizzes(question_pool)

    def _update_score(self, question, correct_answered):
        """
        updates the score (and score_sum) of question, depending on whether
        it was answered correctly.
        """
        if self.question_score[question] < self.bad_score:
            self.num_bad_scores -= 1
        super(Queued_Quiz, self)._update_score(question, correct_answered)
        if self.question_score[question] < self.bad_score:
            self.num_bad_scores += 1

    def _select_question(self):
        "select next question"
        if self.num_bad_scores < self.min_num_bad_scores:
            self._increase_quiz_pool()
        super(Queued_Quiz, self)._select_question()

    def _increase_quiz_pool(self, num=None):
        "Add quizzes from the new_quiz_pool to the quiz_pool"
        if num == None:
            num = self.batch_length
        new_quizzes = []
        for i in range(min(num, len(self.new_quiz_pool))):
            new_quizzes.append(self.new_quiz_pool.pop(0))
        self.num_bad_scores += num
        super(Queued_Quiz, self).add_quizzes(new_quizzes)

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
        super(Queued_Quiz, self).add_quizzes(scored_quizzes)
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
        super(Queued_Quiz, self).remove_quizzes(rm_scored_quizzes)
        self._insure_min_quiz_num()
