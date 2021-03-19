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
import lxml
import lxml.etree

import pyparsing

import click

from booque import Parser, SearchTerm
from booque.util import field_map, PlPath, add_highlight, read_config


ns_map = {
        'dc': "http://dublincore.org/documents/dcmi-namespace/",
        'aqd': "http://aurora-network.global/queries/namespace/",
    }

p = Parser()
@click.command()
@click.option("--highlight", is_flag=True, default=False, help="add highlighting to query")
@click.option("--output", default="list", type=click.Choice(["list", "elastic"]), help="the format of the output")
@click.option("--outdir", type=PlPath(file_okay=False, dir_okay=True, writable=True, resolve_path=True), default=pathlib.Path("./es"), help="the path of the directory where the output will be stored", show_default=True)
@click.option("--indir", type=PlPath(exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True), default=pathlib.Path("./sdg-queries"), help="the directory of the aurora xml query files", show_default=True)
def run(**kwargs):
    """
    Read the aurora SDG query xml and translate the queries to
    elasticsearch query language
    """

    read_config()

    indir = kwargs['indir']
    outdir = kwargs['outdir']

    if not outdir.exists():
        outdir.mkdir(parents=True)


    for sdg in range(1,18):
        infile = indir / f"query_SDG{sdg}.xml"
        with infile.open(mode="r") as fh:
            xml = lxml.etree.parse(fh)

        xpe = lxml.etree.XPathEvaluator(xml, namespaces=ns_map)

        queries = xpe('//aqd:query-definition')
        should = []
        for query in queries:
            qxpe = lxml.etree.XPathEvaluator(query, namespaces=ns_map)
            identifier = next(iter(qxpe("./dc:identifier/text()")), None)
            sq_id = next(iter(qxpe("./aqd:subquery-identifier/text()")), "0")
            print("IDENTIFIER:", identifier, sq_id)
            lines = qxpe("./aqd:query-lines/aqd:query-line")
            t_should = []
            for n, line in enumerate(lines):
                fields = line.get("field").split("-")
                searchstring = re.sub(r"\s+", " ", line.text)
                #print("  QUERY", n, ":",searchstring)
                tree = p.parse(searchstring)
                #print("  TREE", tree)
                if kwargs['output'] == "elastic":
                    i_should = []
                    for field in fields:
                        clauses = p.to_elastic(tree, field_map[field])
                        i_should.append(clauses)
                    t_should.append({
                            'bool': { 'should': i_should, 'minimum_should_match': 1 }
                        })
                elif kwargs['output'] == "list":
                    t_should = list(set(p.as_list(tree)))

            #print(t_should)
            if kwargs['output'] == "elastic":
                should.append({
                        'bool': { 'should': t_should, 'minimum_should_match': 1 }
                    })
                result = {
                        'query': {
                            'bool': {'should': t_should, 'minimum_should_match': 1}
                        },
                        'track_total_hits': True,
                    }
                if kwargs['highlight']:
                    add_highlight(result)
            elif kwargs['output'] == "list":
                should.extend(t_should)
                result = t_should

            outfile = outdir / f"aurora_SDG-{sdg}.{sq_id}-query.json"
            outfile.write_text(json.dumps(result))
        if kwargs['output'] == "elastic":
            result = {
                    'query': {
                        'bool': {'should': should, 'minimum_should_match': 1},
                    },
                    'track_total_hits': True,
                }
            if kwargs['highlight']:
                add_highlight(result)
        elif kwargs['output'] == "list":
            result = list(set(should))

        outfile = outdir / f"aurora_SDG-{sdg}-query.json"
        outfile.write_text(json.dumps(result))
        print()

if __name__ == '__main__':
    run()
