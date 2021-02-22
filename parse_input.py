# coding: utf-8

# This file is part of booque
# booque - A library to parse and translate scopus-like boolean queries
# Copyright (C) 2021  Impacter B.V.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import re
import sys

from booque import Parser, SearchTerm

query = sys.stdin.readlines()
if len(query) > 1:
    raise ValueError("Only enter one query(line)")

parser = Parser()

query = re.sub(r"\s+", " ", query[0].strip())
result = parser.parse(query)
if len(result) > 1:
    raise ValueError("Expected a tree with a single root")

for op, clauses in result.items():
    es = parser.to_elastic(result, 'description.abstract')
    result = json.dumps(
            {
                'query': es,
                'highlight': {
                    'pre_tags': [ "HLSHL" ],
                    'post_tags': [ "HLEHL" ],
                    'fields': { '*': {} },
                    'fragment_size': 2147483647
                }
            }
        )
    print(result)
