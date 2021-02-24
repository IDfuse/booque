# booque

Library to parse scopus-like boolean queries and translate them into
elasticsearch ones.

## Installation

> `git clone https://github.com/martijnvanbeers/booque`

> create/activate a conda/virtualenv environment

> `pip install .`

or when you plan to make changes:

> `pip install -e .`

## Example

> `cat '"foo" W/3 ("bar" OR "baz")' | booque_parse |curl -s -XPOST 'http://localhost:9200/my_index/_search' -H 'Content-Type: application/json' -d '@-' |jq '.hits.hits[]' |less`

or if you want to see the resulting json:

> `cat '"foo" W/3 ("bar" OR "baz")' | booque_parse

## Translating the aurora and elsevier queries with the provided scripts

### Aurora

* clone the auroa repository: `git clone https://github.com/Aurora-Network-Global/sdg-queries`
  (the `parse_aurora_queries.py` script expects this to be in a `aurora-sdg-queries/` directory relative to its location)

* create an `es` directory for the output

* run `python parse_aurora_queries.py`

### Elsevier

* Download the [Elsevier data](https://data.mendeley.com/datasets/87txkw7khs/1)

* The `parse_elsevier_queries.py` script expects the spreadsheet with the queries in an `elsevier` directory relative to its location)

* create an es directory for the output

* run `python parse_elsevier_queries.py`
