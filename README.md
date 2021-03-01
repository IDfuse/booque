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

* run `booque_aurora_parse --indir /path/to/sdg-queries --outdir /path/to/output_directory`

  This loops over the xml files from the sdg-queries repository and writes json files containing
  a elasticsearch query for each target per SDG and also a combined query for each SDG

### Elsevier

* Download the [Elsevier data](https://data.mendeley.com/datasets/87txkw7khs/1)

* run `booque_elsevier_parse /path/to/SDG_queries_collated_20191010.xlsx --putdir /path/to/output_directory`

### Common option

* each script accepts a `--help` option that has summary information about how to call it

* the `--outdir` option defaults to `./es/`, so if that's an acceptable location, there is no need to specify it

* they all read `$HOME/.config/booque/config.json`. Currently this can only contain a fields object/dict
  that maps the scopus field names to the elasticsearch field names. If this file doesn't exist, it
  will be filled with the default mapping
