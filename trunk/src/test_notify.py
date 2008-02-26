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

from notify import Notifier
import unittest
from pmock import Mock, once, never, same

class Test_Notifier(unittest.TestCase):
    """
    Unittest for the class Notifier.
    """

    def setUp(self):
        self.notifier = Notifier(['simple_key', 'key_with_message'])
        self.mock_listener = Mock()
        self.first_key_heared = self.mock_listener.first_key_heared
        self.first_key_heared_again = self.mock_listener.first_key_heared_again
        self.second_key_heared = self.mock_listener.second_key_heared
        self.notifier.connect('simple_key', self.first_key_heared)
        self.notifier.connect('simple_key', self.first_key_heared_again)
        self.notifier.connect('key_with_message', self.second_key_heared)

    def test_notifier(self):
        self.mock_listener.expects(once()).first_key_heared()
        self.mock_listener.expects(once()).first_key_heared_again()
        self.mock_listener.expects(never()).second_key_heared()
        self.notifier.notify('simple_key')
        self.mock_listener.verify()

    def test_notifier_with_message(self):
        self.mock_listener.expects(never()).first_key_heared()
        self.mock_listener.expects(never()).first_key_heared_again()
        self.mock_listener.expects(once()).method('second_key_heared').\
                with_at_least(same('little message'))
        self.notifier.notify('key_with_message', 'little message')
        self.mock_listener.verify()

    def test_disconnect(self):
        self.mock_listener.expects(once()).first_key_heared()
        self.mock_listener.expects(never()).first_key_heared_again()
        self.notifier.disconnect('simple_key', self.first_key_heared_again)
        self.notifier.notify('simple_key')
        self.mock_listener.verify()

    def test_reconnect(self):
        self.mock_listener.expects(once()).first_key_heared()
        self.mock_listener.expects(once()).first_key_heared_again()
        self.notifier.disconnect('simple_key', self.first_key_heared_again)
        self.notifier.connect('simple_key', self.first_key_heared_again)
        self.notifier.notify('simple_key')
        self.mock_listener.verify()


def testsuite():
    suite = unittest.TestSuite()
    for test in [ Test_Notifier ]:
        suite.addTest(unittest.makeSuite(test))
    return suite


if __name__ == '__main__':
    unittest.main()
