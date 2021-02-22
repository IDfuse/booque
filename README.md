# booque

Library to parse scopus-like boolean queries and translate them into
elasticsearch ones.

## Example

> `cat '"foo" W/3 ("bar" OR "baz")' | booque_parse |curl -s -XPOST 'http://localhost:9200/my_index/_search' -H 'Content-Type: application/json' -d '@-' ||jq '.hits.hits' |less`
