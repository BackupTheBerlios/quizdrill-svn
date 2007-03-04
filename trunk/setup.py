#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, Adam Schmalhofer
# Developed by Adam Schmalhofer <schmalhof@users.berlios.de>
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

from distutils.core import setup

setup(name='quizdrill', 
        version='0.1.1', 
        description='',
        author='Adam Schmalhofer',
        author_email='schmalhof@users.berlios.de',
        url='http://developer.berlios.de/projects/quizdrill/',
        py_modules=['quizdrill'],
        data_files=[('quizzes', ['quizzes/de-fr.drill', 'quizzes/en-fr.drill', 
            'quizzes/en-ja.drill', 'quizzes/en-ja_roma.drill', 
            'quizzes/sn-sv.drill', 'quizzes/fr_verb.drill']),
            ('po', ['po/de.po']),
            ('doc', ['README', 'TODO', 'GPL-2', 'Changelog'])]
        )
