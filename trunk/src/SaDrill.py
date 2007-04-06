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
    Simple API for .drill.
    Accessing Quizdrill files similar to SAX (Simple API for XML).

    Note: This is not functional yet, nor is it used anywhere (yet).
    """

    def parse(self, drill_file):
        self.drill_file = drill_file
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
                        print _('Warning: unknown tag "%s".') % tag
                elif line[0] == '[':
                    line = line[1:-1]
                    word_pair = [ w.strip() for w in line.split("=", 1) ]
                    if len(word_pair) < 2:
                        word_pair.append("")
                    column = []; column.extend(word_pair)
                    column.append(True)
                    section = self.treestore.append(None, column)
                elif line[0] == '$':
                    line = line[1:-1]
                else:
                    word_pair = [ w.strip() for w in line.split("=") ]
                    assert len(word_pair) == 2, 'Fileformaterror in "%s": \
                            Not exactly one "=" in line %s' % ( file, i+1 )
                    quizlist.append(word_pair)
                    column = []; column.extend(word_pair)
                    column.append(True)
                    self.treestore.append(section, column)
        f.close()
        return quizlist

    def startSection(self, name):
        pass

    def endSection(self, name):
        pass
