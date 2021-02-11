# coding: utf-8
import logging
import re
import json
import lxml
import lxml.etree
import pyparsing

from booque import Parser, SearchTerm

def old_add_clauses(operator, clauses, field):
    fquery = {}
    resultclauses = []
    if isinstance(clauses, str):
        return {'span_term': {field: clauses}}
    for clause in clauses:
        if isinstance(clause, dict):
            for suboperator, subclauses in clause.items():
                resultclauses.append(add_clauses(suboperator, subclauses, field))
        elif isinstance(clause, SearchTerm):
            if "*" in str(clause):
                resultclauses.append({'span_multi': {"match": {"wildcard": {field: {"value": str(clause)}}}}})
            else:
                resultclauses.append({'span_term': {field: str(clause)}})
    if operator[:2] == "W/":
        _, slop = operator.split("/", 1)
        return {'span_near': {'clauses': resultclauses, 'slop': slop, 'in_order': False}}
    elif operator == "OR":
        return {'span_or': {'clauses': resultclauses}}
    elif operator == "AND":
        # emulate and with unlimited slop, per
        # https://stackoverflow.com/a/39994490
        return {'span_near': {'clauses': resultclauses, 'slop': 2147483647, 'in_order': False}}
    elif operator == "AND NOT":
        return {'span_not': {'include': resultclauses[0], 'exclude': resultclauses[1] }}


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
#            if not (sdg == 3 and sq_id == "2" and n == 0):
#                print("SKIPPING")
#                continue
            fields = line.get("field").split("-")
#            print("  FIELDS:", fields)
            searchstring = re.sub(r"\s+", " ", line.text)
            print("  QUERY", n, ":",searchstring)
            tree = p.parse(searchstring)
            print("  TREE", tree)
            i_should = []
            for field in fields:
#                if field != 'ABS':
#                    continue
                for operator, clauses in tree.items():
                    result = p.add_clauses(operator, clauses, field_map[field])
                    i_should.append(result)
            t_should.append({
                    'bool': { 'should': i_should, 'minimum_should_match': 1 }
                })
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
                }
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
