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

from collections import defaultdict
import json


class AttrDict(defaultdict):
    @staticmethod
    def converted(v):
        if isinstance(v, AttrDict):
            return v
        elif isinstance(v, dict):
            return AttrDict(v)
        elif isinstance(v, (list, tuple)):
            r = list(map(AttrDict.converted, v))
            return tuple(r) if isinstance(v, tuple) else r
        else:
            return v

    def merge(self, arg):
        if hasattr(arg, 'items'):
            self.merge(arg.items())
        else:
            for k, v in arg:
                self[k] = AttrDict.converted(v)

    def asdict(self):
        return json.loads(json.dumps(self))

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(AttrDict)
        if len(args) == 1:
            self.merge(args[0])
        elif len(args) > 1:
            raise TypeError("AttrDict expected at most 1 argument that is a map, got %i" % len(args))
        self.merge(kwargs)

    def __setitem__(self, k, v):
        return super(AttrDict, self).__setitem__(k, AttrDict.converted(v))

    __getattr__ = defaultdict.__getitem__
    __setattr__ = __setitem__


