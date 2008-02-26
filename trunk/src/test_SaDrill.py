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

from SaDrill import SaDrill, MissingTagsError, MissingQuestionsError, \
        WordPairError
import unittest
from pmock import Mock, once, at_least_once, never, same

class Mocked_SaDrill(SaDrill):
    """
    Hooks for SaDrill which call a pmock-object on tag, comment and question
    processing.
    """

    def __init__(self, head_tag_dict={}, build_tag_dict={}, 
            mandatory_head_tags=[], mandatory_build_tags=[],
            mandatory_has_questions=False):
        self.mock_hooks = Mock()
        mocked_head_tag_dict = { 
                ' ': self.mock_hooks.on_default_header,
                'a_header': self.mock_hooks.on_a_header, 
                'an_other_header': self.mock_hooks.on_an_other_header
                }
        mocked_build_tag_dict = { 
                ' ': self.mock_hooks.on_default_builder,
                'a_builder': self.mock_hooks.on_a_builder, 
                'an_other_builder': self.mock_hooks.on_an_other_builder 
                }
        mocked_head_tag_dict.update(head_tag_dict)
        mocked_build_tag_dict.update(build_tag_dict)
        super(Mocked_SaDrill, self).__init__(mocked_head_tag_dict, 
                mocked_build_tag_dict, mandatory_head_tags, 
                mandatory_build_tags, mandatory_has_questions)
        self.on_comment = self.mock_hooks.on_comment
        self.on_section = self.mock_hooks.on_section
        self.on_question = self.mock_hooks.on_question
        #self.on_comment = self.mock_hooks.on_comment


class Test_SaDrill_without_mandatory_tags(unittest.TestCase):
    """
    Unittest for the class SaDrill.
    """

    def setUp(self):
        self.sadrill = Mocked_SaDrill()

    def test_empty_file(self):
        self.sadrill.parse('/dev/null')

    def test_default_header(self):
        self.sadrill.mock_hooks.expects(once()).method('on_default_header')
        self.sadrill.parse('test_data/sadrill_unknown_header.drill')
        self.sadrill.mock_hooks.verify()

    def test_single_header(self):
        self.sadrill.mock_hooks.expects(once()).method('on_a_header')
        self.sadrill.parse('test_data/sadrill_one_header.drill')
        self.sadrill.mock_hooks.verify()

    def test_two_headers(self):
        self.sadrill.mock_hooks.expects(once()).method('on_a_header')
        self.sadrill.mock_hooks.expects(once()).method('on_an_other_header').\
                after('on_a_header')
        self.sadrill.parse('test_data/sadrill_two_headers.drill')
        self.sadrill.mock_hooks.verify()

    def test_default_builder(self):
        self.sadrill.mock_hooks.expects(once()).method('on_default_builder')
        self.sadrill.parse('test_data/sadrill_unknown_builder.drill')
        self.sadrill.mock_hooks.verify()

    def test_single_builder(self):
        self.sadrill.mock_hooks.expects(once()).method('on_a_builder')
        self.sadrill.parse('test_data/sadrill_one_builder.drill')
        self.sadrill.mock_hooks.verify()

    def test_two_builders(self):
        self.sadrill.mock_hooks.expects(once()).method('on_a_builder')
        self.sadrill.mock_hooks.expects(once()).method('on_an_other_builder')
        self.sadrill.parse('test_data/sadrill_two_builders.drill')
        self.sadrill.mock_hooks.verify()

    def test_one_comment(self):
        self.sadrill.mock_hooks.expects(once()).method('on_comment')
        self.sadrill.parse('test_data/sadrill_one_comment.drill')
        self.sadrill.mock_hooks.verify()

    def test_section_with_translation(self):
        self.sadrill.mock_hooks.expects(once()).method('on_section')
        self.sadrill.parse('test_data/sadrill_section_with_translation.drill')
        self.sadrill.mock_hooks.verify()

    def test_section_without_translation(self):
        self.sadrill.mock_hooks.expects(once()).method('on_section')
        self.sadrill.parse(
                'test_data/sadrill_section_without_translation.drill')
        self.sadrill.mock_hooks.verify()

    def test_half_question_fails(self):
        self.assertRaises(WordPairError, 
                self.sadrill.parse, 'test_data/sadrill_half_question.drill')

    def test_broken_header_fails(self):
        self.assertRaises(WordPairError, 
                self.sadrill.parse, 'test_data/sadrill_broken_header.drill')

    def test_broken_builder_fails(self):
        self.assertRaises(WordPairError, 
                self.sadrill.parse, 'test_data/sadrill_broken_builder.drill')


class Test_SaDrill_with_mandatory_tags(unittest.TestCase):
    """
    Unittest for the class SaDrill.
    """

    def test_missing_mandatory_header(self):
        sadrill = Mocked_SaDrill(mandatory_head_tags=['an_other_header'])
        sadrill.mock_hooks.expects(once()).method('on_a_header')
        self.assertRaises(MissingTagsError, 
                sadrill.parse, 'test_data/sadrill_one_header.drill')
        sadrill.mock_hooks.verify()

    def test_accepts_mandatory_header(self):
        sadrill = Mocked_SaDrill(mandatory_head_tags=['a_header'])
        sadrill.mock_hooks.expects(once()).method('on_a_header')
        sadrill.parse('test_data/sadrill_one_header.drill')
        sadrill.mock_hooks.verify()

    def test_missing_mandatory_builder(self):
        sadrill = Mocked_SaDrill(mandatory_build_tags=['an_other_builder'])
        sadrill.mock_hooks.expects(once()).method('on_a_builder')
        self.assertRaises(MissingTagsError, 
                sadrill.parse, 'test_data/sadrill_one_builder.drill')
        sadrill.mock_hooks.verify()

    def test_accepts_mandatory_builder(self):
        sadrill = Mocked_SaDrill(mandatory_build_tags=['a_builder'])
        sadrill.mock_hooks.expects(once()).method('on_a_builder')
        sadrill.parse('test_data/sadrill_one_builder.drill')
        sadrill.mock_hooks.verify()

    def test_missing_mandatory_questions(self):
        sadrill = Mocked_SaDrill(mandatory_has_questions=True)
        sadrill.mock_hooks.expects(once()).method('on_a_header')
        self.assertRaises(MissingQuestionsError, 
                sadrill.parse, 'test_data/sadrill_one_header.drill')
        sadrill.mock_hooks.verify()

    def test_accepts_mandatory_questions(self):
        sadrill = Mocked_SaDrill(mandatory_has_questions=True)
        sadrill.mock_hooks.expects(once()).method('on_question')
        sadrill.parse('test_data/sadrill_one_question.drill')
        sadrill.mock_hooks.verify()

def testsuite():
    suite = unittest.TestSuite()
    for test in [ Test_SaDrill_without_mandatory_tags, 
            Test_SaDrill_with_mandatory_tags ]:
        suite.addTest(unittest.makeSuite(test))
    return suite


if __name__ == '__main__':
    unittest.main()
