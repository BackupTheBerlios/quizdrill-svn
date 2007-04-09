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

class SaDrill:
    """
    Simple API for .drill or a .build of it.
    Accessing Quizdrill files similar to SAX (Simple API for XML).

    Note: This is not used anywhere yet.
    """

    def __init__(self, head_tag_dict={}, build_tag_dict={}):
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

    def parse(self, drill_file):
        """
        Parse a .drill or .build file.
        """
        self.current_drill_file = drill_file
        f = open(drill_file)
        head_tag_dict = self.head_tag_dict
        build_tag_dict = self.build_tag_dict

        for i, line in enumerate(f.readlines()):
            line = line.strip()
            if len(line) > 0:
                type = line[0]
                if type == '#':
                    on_comment(line, None, None, type)
                elif type == '!':
                    colon = line.index(":")
                    tag = line[1:colon]
                    word_pair = [ w.strip() for w in line[colon+1:].split("=")]
                    if tag in head_tag_dict:
                        head_tag_dict[tag](word_pair)
                    else:
                        print _('Warning: unknown head-tag "%s".') % tag
                elif type == '[':
                    line = line[1:-1]
                    word_pair = [ w.strip() for w in line.split("=", 1) ]
                    if len(word_pair) < 2:
                        word_pair.append("")
                    on_section(line, word_pair, None, type)
                elif type == '$':
                    colon = line.index(":")
                    tag = line[1:colon]
                    word_pair = [ w.strip() for w in line[colon+1:].split("=")]
                    if tag in build_tag_dict:
                        build_tag_dict[tag](word_pair)
                    else:
                        print _('Warning: unknown build-tag "%s".') % tag
                else:
                    type = ''
                    word_pair = [ w.strip() for w in line.split("=") ]
                    assert len(word_pair) == 2, 'Fileformaterror in "%s": \
                            Not exactly one "=" in line %s' % ( file, i+1 )
                    on_question(line, word_pair, None, type)
        f.close()
        self.current_drill_file = None

    def on_comment(as_text, word_pair=None, tag=None, type='#'):
        """
        Processes a comment line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        pass

    def on_section(as_text, word_pair, tag=None, type='['):
        """
        Processes a section line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        pass

    def on_question(as_text, word_pair, tag=None, type=''):
        """
        Processes a question-answer line of an .drill or .build file. Overload 
        this method so something is actually done.
        """
        pass

    def on_default_head_tag(as_text, word_pair, tag, type='!'):
        """
        Processes a header line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        pass

    def on_default_build_tag(as_text, word_pair, tag, type='$'):
        """
        Processes a builder line of an .drill or .build file. Overload this
        method so something is actually done.
        """
        pass

