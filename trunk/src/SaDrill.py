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

from pkg_resources import resource_filename
import gettext
_ = gettext.gettext
APP = "quizdrill"
DIR = resource_filename(__name__, "../locale")

class SaDrill:
    """
    Simple API for .drill or a .build of it.
    Accessing Quizdrill files inspired by SAX (Simple API for XML).

    Calls different methods (on_*) depending on each line.
    Meta- (!) and build-headers ($) call corresponding method registered
    in self.head_tag_dict and self.build_tag_dict.
    """

    def __init__(self, head_tag_dict={}, build_tag_dict={}, 
            mandatory_head_tags=[], mandatory_build_tags=[]):
        self.head_tag_dict = { 
                "language" : self.on_default_head_tag, 
                "question" : self.on_default_head_tag, 
                "type" : self.on_default_head_tag,
                "media" : self.on_default_head_tag,
                "generator" : self.on_default_head_tag 
                }
        self.build_tag_dict = { 
                "build_to" : self.on_default_build_tag, 
                "builder" : self.on_default_build_tag, 
                "filter" : self.on_default_build_tag
                }
        self.head_tag_dict.update(head_tag_dict)
        self.build_tag_dict.update(build_tag_dict)
        self.mandatory_head_tags=set(mandatory_head_tags)
        self.mandatory_build_tags=set(mandatory_build_tags)

    def parse(self, drill_file):
        """
        Parse a .drill or .build file.
        """
        self.current_drill_file = drill_file
        f = open(drill_file)
        head_tag_dict = self.head_tag_dict
        build_tag_dict = self.build_tag_dict
        used_mandatory_head_tags=set([])
        used_mandatory_build_tags=set([])

        for i, line in enumerate(f.readlines()):
            line = line.strip()
            if len(line) > 0:
                type = line[0]
                if type == '#':
                    self.on_comment(line, None, None, type)
                elif type == '!':
                    colon = line.index(":")
                    tag = line[1:colon]
                    word_pair = [ w.strip() for w in line[colon+1:].split("=")]
                    if tag in head_tag_dict:
                        if tag in self.mandatory_head_tags and \
                                not tag in used_mandatory_head_tags:
                            used_mandatory_head_tags.add(tag)
                        head_tag_dict[tag](line, word_pair, None, type)
                    else:
                        print _('Warning: unknown head-tag "%s".') % tag
                elif type == '[':
                    line = line[1:-1]
                    word_pair = [ w.strip() for w in line.split("=", 1) ]
                    if len(word_pair) < 2:
                        word_pair.append("")
                    self.on_section(line, word_pair, None, type)
                elif type == '$':
                    colon = line.index(":")
                    tag = line[1:colon]
                    word_pair = [ w.strip() for w in line[colon+1:].split("=")]
                    if tag in build_tag_dict:
                        if tag in self.mandatory_build_tags and \
                                not tag in used_mandatory_build_tags:
                            used_mandatory_build_tags.add(tag)
                        build_tag_dict[tag](line, word_pair, None, type)
                    else:
                        print _('Warning: unknown build-tag "%s".') % tag
                else:
                    type = ''
                    word_pair = [ w.strip() for w in line.split("=") ]
                    assert_str = 'Fileformaterror in "%s": Not exactly ' + \
                            'one "=" in line %s'
                    assert len(word_pair) == 2, 'Fileformaterror in "%s": \
                            Not exactly one "=" in line %s' % ( file, i+1 )
                    self.on_question(line, word_pair, None, type)
        f.close()
        self.current_drill_file = None
        # check if all mandatory tags were present #
        missing_tags = ( self.mandatory_head_tags - used_mandatory_head_tags )\
                | ( self.mandatory_build_tags - used_mandatory_build_tags )
        if missing_tags != set([]):
            print _('Error: missing mandatory tag "%s".') % missing_tags

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

    def on_default_build_tag(self, as_text, word_pair, tag, type='$'):
        """
        Processes a builder line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        pass

