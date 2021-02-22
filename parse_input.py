# coding: utf-8
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
