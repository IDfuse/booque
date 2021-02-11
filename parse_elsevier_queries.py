# coding: utf-8
import logging
import re
import json
import lxml
import lxml.etree
import pyparsing

import pandas as pd

from booque import Parser, SearchTerm

def add_clauses(operator, clauses, field):
    fquery = {}
    result_clauses = []
    if isinstance(clauses, str):
        raise ValueError("A STRING?!")
        return {'span_term': {field: clauses}}
    for clause in clauses:
        if isinstance(clause, dict):
            for suboperator, subclauses in clause.items():
                result_clauses.append(add_clauses(suboperator, subclauses, field))
        elif isinstance(clause, SearchTerm):
            if any(wildcard in str(clause) for wildcard in "*?"):
                result_clauses.append({'span_multi': {"match": {"wildcard": {field: {"value": str(clause)}}}}})
            elif clause.is_phrase:
                result_clauses.append({'match_phrase': {field: str(clause)}})
            else:
                result_clauses.append({'span_term': {field: str(clause)}})
    if operator[:2] == "W/":
        _, slop = operator.split("/", 1)
        return {'span_near': {'clauses': result_clauses, 'slop': slop, 'in_order': False}}
    elif operator == "OR":
        return {'span_or': {'clauses': result_clauses}}
    elif operator == "AND":
        # emulate and with unlimited slop, per
        # https://stackoverflow.com/a/39994490
        return {'span_near': {'clauses': result_clauses, 'slop': 2147483647, 'in_order': False}}
    elif operator == "AND NOT":
        return {'span_not': {'include': result_clauses[0], 'exclude': result_clauses[1] }}


field_map = {
        'TITLE': "description.title",
        'ABS': "description.abstract",
        'KEY': "description.keywords",
    }

p = Parser()

df = pd.read_excel("../elsevier/SDG_queries_collated_20191010.xlsx")
for i, row in df.iterrows():
    if not isinstance(row['Query'], str):
        continue
    sdg = row['SDG']
    query = re.sub(r"\s+", " ", row['Query'])
    query = re.sub(r"[“”]", '"', query)
    fields, query = query.split(' ', 1)
    fields = fields.split('-')

    print("*" * 80, "\n SDG:", i)
    print("QUERY:", query)
    tree = p.parse(query)
    print(i, "TREE:", tree)

    should = []
    for field in fields:
        for operator, clauses in tree.items():
            result = p.add_clauses(operator, clauses, field_map[field])
            should.append(result)
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
    with open(f"es/elsevier_SDG-{sdg}-query.json", "w") as fh:
        json.dump(result, fh)
    print("=" * 80)
