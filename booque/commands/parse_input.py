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

import click
from booque import Parser, SearchTerm
from booque.util import field_map, PlPath, add_highlight, read_config


parser = Parser()

@click.command()
@click.option("--highlight", is_flag=True, help="add highlighting to the query")
@click.option("--output", default="elastic", type=click.Choice(["elastic", "list"]), help="the format of the output query")
@click.option("--field", default="ABS", show_default=True, help="which scopus field to query")
def run(**kwargs):
    """
    Read a line from STDIN containing a scopus query and translate
    it to elasticsearch query language
    """

    read_config()

    query = sys.stdin.readlines()
    if len(query) > 1:
        raise ValueError("Only enter one query(line)")

    query = re.sub(r"\s+", " ", query[0].strip())
    result = parser.parse(query)
    if len(result) > 1:
        raise ValueError("Expected a tree with a single root")

    if kwargs['output'] == "elastic":
        es = parser.to_elastic(result, field_map[kwargs['field']])
        result = {
                    'query': es,
                }
        if kwargs['highlight']:
            add_highlight(result)
        print(json.dumps(result))
    elif kwargs['output'] == "list":
        termlist = parser.as_list(result)
        for term in termlist:
            print(term)

if __name__ == '__main__':
    run()
