# coding: utf-8
import logging
import json
import re
import lxml
import lxml.etree

from booque import Parser, SearchTerm

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

test = [
#        '( ( {extreme poverty}  OR  {poverty alleviation}  OR  {poverty eradication}  OR  {poverty reduction}  OR  {international poverty line}  OR  ( {financial aid}  AND  {poverty} )  OR  ( {financial aid}  AND  {poor} )  OR  ( {financial aid}  AND  {north-south divide} )  OR  ( {financial development}  AND  {poverty} )  OR  {financial empowerment}  OR  {distributional effect}  OR  {distributional effects}  OR  {child labor}  OR  {child labour}  OR  {development aid}  OR  {social protection}  OR  {social protection system}  OR  ( {social protection}  AND  access )  OR  microfinanc*  OR  micro-financ*  OR  {resilience of the poor}  OR  ( {safety net}  AND  {poor}  OR  {vulnerable} )  OR  ( {economic resource}  AND  access )  OR  ( {economic resources}  AND  access )  OR  {food bank}  OR  {food banks} ) )',
#        '( {financial aid}  AND  {poverty} )  OR  ( {financial aid}  AND  {poor} )  OR  ( {financial development}  AND  {poverty} )',
#        '("poverty" OR "income") W/3 ("inequalit*")',
#        '("social protection" OR "economic marginalization" OR "economic marginalisation" OR "poor*" OR " vulnerable") AND ("poverty" OR "income")',
        '("agricultur*") AND ("Doha development round")',
#        '("foo" AND "bar") OR "baz"',
#        'foo OR bar AND baz',
#        'foo AND bar OR baz',
#        'foo OR bar OR baz AND quux',
#        'foo bar OR baz',
#        '{foo} OR {bar}',
#        '"foo" "bar"',
#        '"foo" OR "bar"',
#        '"foo" AND NOT "bar"',
#        '"foo" AND NOT ("bar" OR "baz")',
#        '"foo" OR bar',
#        '("foo" OR "bar")',
#        '("foo" OR "bar") AND "haz"',
#        '( "eradicat*" OR "reduc*" AND "end" OR "ending" OR "alleviat*")',
#        '''( "eradicat*" OR "reduc*" OR "end" OR
#        "ending" OR "alleviat*")''',
#        '("poverty") W/3 ("chronic*" OR "extreme")',
#        '("poverty") W/3 "extreme"',
#        '("agricultur*") AND ( ("trade" OR "import" OR "export") W/3 ("restriction*" OR "distort*" OR "subsid*"))',
#        '("disaster*") W/3 ("risk reduction*") W/3 ("strateg*")',
#        '''                    ("ocean*" OR "marine" OR "coast*" OR "sea" OR "seas" OR "seawater*" OR "sea water*" OR "coral
#                            reef*" ) AND ("ecosystem*" OR "biodivers*" OR "protection" OR "environmental degradation" )
#                            '''
    ]

parser = Parser()
for t in test:
    t = re.sub(r"\s+", " ", t)
    result = parser.parse(t)
    #print(json.dumps(result, default=str))
    for op, clauses in result.items():
        es = parser.add_clauses(op, clauses, 'description.abstract')
        print(json.dumps({'query': es,
            'highlight': {
                'pre_tags': [ "HLSHL" ],
                'post_tags': [ "HLEHL" ],
                'fields': { '*': {} },
                'fragment_size': 2147483647
            }
            }))


