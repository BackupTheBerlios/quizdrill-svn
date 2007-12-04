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

import unittest
import test_quiz, test_notify, test_SaDrill


__all__=['gtk-ui', 'quiz', 'Quiz_Filer', 'SaDrill', 'builder', 'wiki_builder']

def testsuite():
    suite = unittest.TestSuite()
    for test_module in [ test_quiz, test_notify, test_SaDrill ]:
        suite.addTest(test_module.testsuite())
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(testsuite())
