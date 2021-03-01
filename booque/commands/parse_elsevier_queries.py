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

import re
import pathlib

import json
import pandas as pd

import pyparsing

import click

from booque import Parser, SearchTerm


class PlPath(click.Path):
    """A Click path argument that returns a pathlib Path, not a string"""
    def convert(self, value, param, ctx):
        return pathlib.Path(super().convert(value, param, ctx))


field_map = {
        'TITLE': "description.title",
        'ABS': "description.abstract",
        'KEY': "description.keywords",
    }

p = Parser()

@click.command()
@click.option("--highlight", is_flag=True)
@click.option("--output", type=click.Choice(["elastic"]))
@click.option("--outdir", type=PlPath(file_okay=False, dir_okay=True, writable=True, resolve_path=True), default=pathlib.Path("./sdg-queries"))
@click.argument("infile", type=PlPath(exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True), default=pathlib.Path("SDG_queries_collated-20191010.xlsx"))
def run(infile, **kwargs):
    outdir = kwargs['outdir']
    if not outdir.exists():
        outdir.mkdir(parents=True)

    df = pd.read_excel(str(infile))
    for i, row in df.iterrows():
        if not isinstance(row['Query'], str):
            continue
        sdg = row['SDG']
        query = re.sub(r"\s+", " ", row['Query'])
        query = re.sub(r"[“”]", '"', query)
        fields, query = query.split(' ', 1)
        fields = fields.split('-')

        tree = p.parse(query)

        should = []
        for field in fields:
            clauses = p.to_elastic(tree, field_map[field])
            should.append(clauses)
        result = {
                'query': {
                    'bool': {'should': should}
                },
                'highlight': {
                    'pre_tags': [ "HLSHL" ],
                    'post_tags': [ "HLEHL" ],
                    'fields': { '*': {} },
                    'fragment_size': 2147483647
                },
                'track_total_hits': True,
            }
        outfile = outdir / f"elsevier_SDG-{sdg}-query.json"
        outfile.write_text(json.dumps(result))

if __name__ == '__main__':
    run()
