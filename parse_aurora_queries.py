# coding: utf-8
import logging
import re
import json
import lxml
import lxml.etree
import pyparsing

from booque import Parser, SearchTerm

ns_map = {
        'dc': "http://dublincore.org/documents/dcmi-namespace/",
        'aqd': "http://aurora-network.global/queries/namespace/",
    }

field_map = {
        'TITLE': "description.title",
        'ABS': "description.abstract",
        'KEY': "description.keywords",
    }

p = Parser()

for sdg in range(1,18):
    with open(f"./aurora-sdg-queries/query_SDG{sdg}.xml", "r") as fh:
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
            print("  QUERY", n, ":",searchstring)
            tree = p.parse(searchstring)
            print("  TREE", tree)
            i_should = []
            for field in fields:
                clauses = p.to_elastic(tree, field_map[field])
                i_should.append(clauses)
            t_should.append({
                    'bool': { 'should': i_should, 'minimum_should_match': 1 }
                })
        print(t_should)
        should.append({
                'bool': { 'should': t_should, 'minimum_should_match': 1 }
            })
        result = {
                'query': {
                    'bool': {'should': t_should, 'minimum_should_match': 1}
                },
                'highlight': {
                    'pre_tags': [ "HLSHL" ],
                    'post_tags': [ "HLEHL" ],
                    'fields': { '*': {} },
                    'fragment_size': 2147483647
                },
                'track_total_hits': True,
            }
        with open(f"es/cnes_SDG-{sdg}.{sq_id}-query.json", "w") as fh:
            json.dump(result, fh)
    result = {
            'query': {
                'bool': {'should': should, 'minimum_should_match': 1},
            },
            'highlight': {
                'pre_tags': [ "HLSHL" ],
                'post_tags': [ "HLEHL" ],
                'fields': { '*': {} },
                'fragment_size': 2147483647
            },
            'track_total_hits': True,
        }
    with open(f"es/cnes_SDG-{sdg}-query.json", "w") as fh:
        json.dump(result, fh)
        print()
