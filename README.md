# booque

Library to parse scopus-like boolean queries and translate them into
elasticsearch ones.

## Example

> `cat '"foo" W/3 ("bar" OR "baz")' | python parse_input.py |curl -s -XPOST 'http://localhost:9200/my_index/_search' -H 'Content-Type: application/json' -d '@-' ||jq '.hits.hits' |sed -e 's/HLSHL/`[0;91m/g' |sed -e 's/HLEHL/[0m/g'  |less -R`
