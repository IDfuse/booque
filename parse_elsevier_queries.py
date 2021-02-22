# coding: utf-8
import logging
import re
import json
import lxml
import lxml.etree
import pyparsing

import pandas as pd

from booque import Parser, SearchTerm


field_map = {
        'TITLE': "description.title",
        'ABS': "description.abstract",
        'KEY': "description.keywords",
    }

p = Parser()

df = pd.read_excel("./elsevier/SDG_queries_collated_20191010.xlsx")
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
    with open(f"es/elsevier_SDG-{sdg}-query.json", "w") as fh:
        json.dump(result, fh)
