#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (c) 2012, Peter Levi <peterlevi@peterlevi.com>
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE
import sys
import os
import unittest

from tests import setup_test_logging

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from variety.AttrDict import AttrDict

setup_test_logging()


class TestAttrDict(unittest.TestCase):
    def test_attr_dict(self):
        a = AttrDict({'a': {'b': 1}})
        self.assertFalse(bool(a.deep.inside))
        self.assertTrue(bool(a.a))
        self.assertEqual(1, a.a.b)
        a.l.k = 3
        self.assertEqual(3, a.l.k)
        a.f.g.h = 2
        self.assertEqual(2, a.f.g.h)
        a["x"]["y"]["z"] = 1
        self.assertEqual(1, a["x"]["y"]["z"])

        b = AttrDict(x=1, y=2)
        self.assertFalse(bool(b.deep.inside))
        self.assertEqual(1, b.x)
        self.assertEqual(2, b.y)

        b.c = {'z': 3}
        self.assertEqual(3, b.c.z)
        self.assertFalse(bool(b.c.dredrefre))


if __name__ == '__main__':
    unittest.main()
