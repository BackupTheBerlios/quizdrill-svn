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

import os.path
from pkg_resources import resource_filename
from gettext import gettext, ngettext
_ = gettext

class SaDrillError(Exception):
    """
    Abstract Error that all Errors in SaDrill should be a subclass of.
    """
    def __init__(self, file):
        self.file = file
        self.str = _('Error in file "%s".') % file

class MissingTagsError(SaDrillError):
    """
    This Error is raised when tags that have been listed as mandatory where not
    found in the parsed file.
    """
    def __init__(self, file, tags):
        self.file = file
        self.tags = tags
        self.str = ngettext('Error: Missing mandatory tag "%(t)s" in %(f)s.', 
                'Error: Missing mandatory tags "%(t)s in %(f)s".', 
                len(tags))% { "t" : tags, "f" : file }

class WordPairError(SaDrillError):
    """
    This Error is raised when a 'word_pair's has a wrong number of elements. 
    This is equivilent to a wrong number of '='s in a line.
    """
    WRONG_NUMBER_OF_WORDPAIRS = 0
    NON_CLOSING_TAG = 1

    def __init__(self, file, line, type=WRONG_NUMBER_OF_WORDPAIRS):
        self.line = line
        self.file = file
        if type == self.WRONG_NUMBER_OF_WORDPAIRS:
            self.str = _('Error: Wrong number of "=" in line %(l)s of'
                ' file %(f)s.') % { "l" : line, "f" : file }
        elif type == self.NON_CLOSING_TAG:
            self.str = _('Error: Tag in line %(l)s of file %(f)s does not'
                ' declare its end with a ":".') % { "l" : line, "f" : file }

class MissingQuestionsError(SaDrillError):
    """
    This Error is raised when no questions or answers are found in a quiz
    file. On builder files this is normal and this error should not be
    raised.
    """
    def __init__(self, file):
        self.file = file
        self.str = _('Error: No questions found in file "%s".') % file

class SaDrill:
    """
    Simple API for .drill or a .build of it.
    Accessing Quizdrill files inspired by SAX (Simple API for XML).

    Calls different methods (on_*) depending on each line.
    Meta- (!) and build-headers ($) call corresponding method registered
    in self.head_tag_dict and self.build_tag_dict.
    """

    def __init__(self, head_tag_dict={}, build_tag_dict={}, 
            mandatory_head_tags=[], mandatory_build_tags=[],
            mandatory_has_questions=False):
        self.head_tag_dict = { 
                " " : self.on_unknown_head_tag,
                "language" : self.on_default_head_tag, 
                "question" : self.on_default_head_tag, 
                "type" : self.on_default_head_tag,
                "media" : self.on_default_head_tag,
                "generator" : self.on_default_head_tag 
                }
        self.build_tag_dict = { 
                " " : self.on_unknown_build_tag,
                "build_to" : self.on_default_build_tag, 
                "builder" : self.on_default_build_tag, 
                "filter" : self.on_default_build_tag
                }
        self.head_tag_dict.update(head_tag_dict)
        self.build_tag_dict.update(build_tag_dict)
        self.mandatory_head_tags=set(mandatory_head_tags)
        self.mandatory_build_tags=set(mandatory_build_tags)
        self.mandatory_has_questions=mandatory_has_questions

    def parse(self, drill_file):
        """
        Parse a .drill or .build file.
        """
        self.current_drill_file = drill_file
        f = open(drill_file)
        head_tag_dict = self.head_tag_dict
        build_tag_dict = self.build_tag_dict
        mandatory_head_tags = self.mandatory_head_tags
        mandatory_build_tags = self.mandatory_build_tags
        used_mandatory_head_tags=set([])
        used_mandatory_build_tags=set([])
        has_questions = False

        def _parse_taged_line(type, tag_dict, mandatory_tags,
                used_mandatory_tags):
            try:
                colon = line.index(":")
            except ValueError:
                raise WordPairError(drill_file, i+1, 
                        WordPairError.NON_CLOSING_TAG)
            else:
                tag = line[1:colon]
                word_pair = [ w.strip() for w in line[colon+1:].split("=")]
                if tag in tag_dict:
                    if tag in mandatory_tags and not tag in used_mandatory_tags:
                        used_mandatory_tags.add(tag)
                    tag_dict[tag](line, word_pair, tag, type)
                else:
                    tag_dict[" "](line, word_pair, tag, type)

        for i, line in enumerate(f.readlines()):
            line = line.strip()
            if len(line) > 0:
                type = line[0]
                if type == '#':
                    self.on_comment(line, None, None, type)
                elif type == '!':
                    _parse_taged_line(type, head_tag_dict, 
                            mandatory_head_tags, used_mandatory_head_tags)
                elif type == '[':
                    line = line[1:-1]
                    word_pair = [ w.strip() for w in line.split("=", 1) ]
                    if len(word_pair) < 2:
                        word_pair.append("")
                    self.on_section(line, word_pair, None, type)
                elif type == '$':
                    _parse_taged_line(type, build_tag_dict, 
                            mandatory_build_tags, used_mandatory_build_tags)
                else:
                    type = ''
                    word_pair = [ w.strip() for w in line.split("=") ]
                    if len(word_pair) != 2:
                        raise WordPairError(drill_file, i+1)
                    else:
                        has_questions = True
                        self.on_question(line, word_pair, None, type)
        f.close()
        self.current_drill_file = None
        # check if all mandatory tags were present #
        missing_tags = ( self.mandatory_head_tags - used_mandatory_head_tags )\
                | ( self.mandatory_build_tags - used_mandatory_build_tags )
        if missing_tags != set([]):
            raise MissingTagsError(drill_file, missing_tags)
        if (not has_questions) and self.mandatory_has_questions:
            raise MissingQuestionsError(drill_file)

    def on_comment(self, as_text, word_pair=None, tag=None, type='#'):
        """
        Processes a comment line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        pass

    def on_section(self, as_text, word_pair, tag=None, type='['):
        """
        Processes a section line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        pass

    def on_question(self, as_text, word_pair, tag=None, type=''):
        """
        Processes a question-answer line of an .drill or .build file. Overload 
        this method so something is actually done.
        """
        pass

    def on_default_head_tag(self, as_text, word_pair, tag, type='!'):
        """
        Processes a header line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        pass

    def on_unknown_head_tag(self, as_text, word_pair, tag, type='!'):
        """
        Processes a header line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        print _('Warning: Unknown head-tag "%s".') % tag

    def on_default_build_tag(self, as_text, word_pair, tag, type='$'):
        """
        Processes a builder line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        pass

    def on_unknown_build_tag(self, as_text, word_pair, tag, type='$'):
        """
        Processes a builder line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        print _('Warning: Unknown build-tag "%s".') % tag
