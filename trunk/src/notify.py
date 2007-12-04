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

class Notifier(object):
    """
    Small class to inform registered objects to different keys by calling the 
    given method. Should be replaced by something more standard in the future.
    """
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

    def notify(self, key, message=None):
        """ 
        Call the registered functions for a given key. See connect for
        more information.
        """
        if message == None:
            for func in self.listoners[key]:
                func()
        else:
            for func in self.listoners[key]:
                func(message)
