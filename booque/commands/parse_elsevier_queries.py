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
from booque.util import field_map, PlPath, add_highlight, read_config


p = Parser()

@click.command()
@click.option("--highlight", is_flag=True, default=False, help="add highlighting to query")
@click.option("--output", default="elastic", type=click.Choice(["elastic", "list"]), help="the format of the output")
@click.option("--outdir", type=PlPath(file_okay=False, dir_okay=True, writable=True, resolve_path=True), default=pathlib.Path("./sdg-queries"), help="the path of the directory where the output will be stored", show_default=True)
@click.argument("infile", type=PlPath(exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True), default=pathlib.Path("SDG_queries_collated-20191010.xlsx"), required=True)
def run(infile, **kwargs):
    """
    Read the elsevier excel sheet containing their query definitions to
    find publications in scopus that are related to the UN Sustainable
    Development Goals (SDGs)

    INFILE: the path of excel sheet
    """
    read_config()

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

        if kwargs['output'] == "elastic":
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
            if kwargs['highlight']:
                add_highlight(result)
        elif kwargs['output'] == "list":
            result = list(set(p.as_list(tree)))

        outfile = outdir / f"elsevier_SDG-{sdg}-query.json"
        outfile.write_text(json.dumps(result))

if __name__ == '__main__':
    run()
