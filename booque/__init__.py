# coding: utf-8
#import logging

import json
import re

import pyparsing
from pyparsing import(
        QuotedString, quotedString, Word,
        Literal, Regex,
        NotAny, FollowedBy, Combine, Optional, oneOf,
        alphanums,
    )

#logging.basicConfig(level=logging.DEBUG)
#logger = logging.getLogger(__name__)

# enable a pyparsing caching mechanism that speeds things up a lot
pyparsing.ParserElement.enablePackrat()


class SearchTerm(object):
    """
        Class to encapsulate a search term
    """
    def __init__(self, term):
        super().__init__()
        self.has_quotes = False
        self.is_phrase = False
        if term[0] in ['"', "'"]:
            term = term[1:-1]
            self.has_quotes = True
        elif term[0] == "{":
            term = term[1:-1]
            self.is_phrase = True
        # workaround for some queries that have a space at the end of a quoted term
        self.term = term.strip()

    def __repr__(self):
        return self.term + ("[Q]" if self.has_quotes else "[]") + ("[P]" if self.is_phrase else "[]")

    def __str__(self):
        return self.term

    def intervals_split(self):
        it = iter(self.term.split())
        result = []

        prev = None
        while True:
            try:
                term = next(it)
            except StopIteration:
                if prev is not None:
                    result.append(prev)
                break
            if prev is None:
                if any(wildcard in term for wildcard in "*?"):
                    result.append(term)
                else:
                    prev = term
                continue
            if any(wildcard in term for wildcard in "*?"):
                result.append(prev)
                result.append(term)
                prev = None
            else:
                prev = f"{prev} {term}"
        return result
    def token_split(self):
        return re.split(r"[- ]", self.term)

class Parser(object):
    """
        Parse Elsevier SCOPUS queries. Based on the (sparse) documentation at http://schema.elsevier.com/dtds/document/bkapi/search/SCOPUSSearchTips.htm
    """
    term = (
                QuotedString("{", endQuoteChar="}", unquoteResults=False) |
                quotedString |
                Combine(Word(alphanums.lower() + "-" + "*" + "?"))
        )

    orop = Literal("OR")
    andnotop = Literal("AND NOT")
    nearop = pyparsing.Regex(r"W\/\d+")
    andop = Literal("AND") + NotAny(Literal("NOT"))
    implicitandop = Regex(r"\s+").sub("AND").leaveWhitespace() + FollowedBy(term)
    expr = pyparsing.infixNotation(
            term,
            [
                (implicitandop, 2, pyparsing.opAssoc.RIGHT),
                (orop, 2, pyparsing.opAssoc.LEFT),
                (nearop, 2, pyparsing.opAssoc.RIGHT),
                (andop, 2, pyparsing.opAssoc.RIGHT),
                (andnotop, 2, pyparsing.opAssoc.RIGHT),
            ],
        )
    def to_prefix(self, e):
        """
            Turn the parsed infix query into a prefix tree
        """
        if isinstance(e, str):
            return {'OR': [SearchTerm(e)]}
        if len(e) == 2:
            op = e[0]
            term = e[1]
            if isinstance(term, pyparsing.ParseResults):
                term = self.to_prefix(term)
            elif isinstance(term, str):
                term = SearchTerm(term)
            return {op: term}
        elif len(e) == 3:
            left, op, right = e
            if isinstance(left, pyparsing.ParseResults):
                left = self.to_prefix(left)
            elif isinstance(left, str):
                left = SearchTerm(left)
            if isinstance(right, pyparsing.ParseResults):
                right = self.to_prefix(right)
            elif isinstance(right, str):
                right = SearchTerm(right)
            return {op: [left, right]}
        else:
            left = e[0]
            if isinstance(left, pyparsing.ParseResults):
                left = self.to_prefix(left)
            elif isinstance(left, str):
                left = SearchTerm(left)
            op = e[1]
            if op != "OR":
                raise ValueError("EEP!", e)
            result = [left]

            for t in e[2:]:
                if isinstance(t, pyparsing.ParseResults):
                    t = self.to_prefix(t)
                elif t == "OR":
                    continue
                elif isinstance(t, str):
                    t = SearchTerm(t)
                result.append(t)
            return {op: result}

    def parse(self, query):
        """
            Use a pyparsing grammar of the SCOPUS boolean query syntax to parse a query
        """
        try:
            result = self.expr.parseString(query, parseAll=True)
        except pyparsing.ParseException as exc:
            print("Parse error:")
            print("  {0}:{1} HERE {2}".format(exc.lineno, exc.col, exc.markInputline()))
            raise
        result = self.to_prefix(result[0])
        return result

    def to_elastic(self, d, field):
        """
            Turn a query parse tree into a elasticsearch query
        """
        if len(d) > 1:
            raise ValueError("Expecting a tree with only one root")
        for k, v in d.items():
            return self._add_clauses(k, v, field)

    def _add_clauses(self, operator, clauses, field, in_near=False):
        fquery = {}
        result_clauses = []
        if operator[:2] == "W/":
            in_near = True
        if isinstance(clauses, str):
            return {'match': {field: clauses}}
        for clause in clauses:
            if isinstance(clause, dict):
                for suboperator, subclauses in clause.items():
                    result_clauses.append(self._add_clauses(suboperator, subclauses, field, in_near=in_near))
            elif isinstance(clause, SearchTerm):
                if clause.has_quotes and " " in str(clause) and not in_near:
                    if any(wildcard in str(clause) for wildcard in "*?"):
                        if not any(wildcard in str(clause)[:-1] for wildcard in "*?"):
                            # for a multi-token clause with a wildcard only at the end, remove the wildcard to
                            # turn it into a match_phrase_prefix query. this avoids getting too many expansions
                            # on the wildcarded final token.
                            result_clauses.append({'match_phrase_prefix': {field: {"query": str(clause)[:-1]}}})
                        else:
                            # if there's wildcards in other places, that's not possible. The next best thing is
                            # an intervals query, but there are some words in the aurora queries that expand to
                            # too many tokens. These are hardcoded here, and use a span query instead
                            # TODO: come up with a solution that doesn't need any hardcoding
                            if any(exception in str(clause) for exception in ("develop*", "human*","work*","labo*")):
                                # elastic splits tokens both on space and dash, so we need to do the same for
                                # span clauses to work
                                subclauses = clause.token_split()
                                subclauses = [{'span_multi': {'match': {'wildcard': {field: {'value': str(clause), 'rewrite': "top_terms_50"}}}}} if any(wildcard in clause for wildcard in "*?") else {'span_term': { field: str(clause)}} for clause in subclauses]
                                result_clauses.append({'span_near': {'clauses': subclauses, 'slop': 0, 'in_order': True}})
                            else:
                                subclauses = clause.intervals_split()
                                subclauses = [{'wildcard': {'pattern': clause}} if any(wildcard in clause for wildcard in "*?") else {'match': { 'query': clause}} for clause in subclauses]

                                result_clauses.append({'intervals': { field: { 'all_of': {'ordered': True, 'max_gaps': 0, 'intervals': subclauses } } } })
                    else:
                        result_clauses.append({'intervals': { field: {'match': { 'ordered': True, 'query': str(clause), 'max_gaps': 0 } } } })
                elif any(wildcard in str(clause) for wildcard in "*?"):
                    if in_near:
                        if re.search(r"[- ]", str(clause)):
                            subclauses = clause.token_split()
                            subclauses = [{'span_multi': {'match': {'wildcard': {field: {'value': str(clause), 'rewrite': "top_terms_50"}}}}} if any(wildcard in clause for wildcard in "*?") else {'span_term': { field: str(clause)}} for clause in subclauses]
                            result_clauses.append({'span_near': {'clauses': subclauses, 'slop': 0, 'in_order': True}})
                        else:
                            result_clauses.append({'span_multi': {"match": {"wildcard": {field: {"value": str(clause), "rewrite": "top_terms_50"}}}}})
                    else:
                        result_clauses.append({"wildcard": {field: {"value": str(clause)}}})
                elif clause.is_phrase:
                    result_clauses.append({'match_phrase': {field: str(clause)}})
                else:
                    if in_near:
                        if re.search(r"[- ]", str(clause)):
                            subclauses = clause.token_split()
                            subclauses = [{'span_term': { field: str(clause)}} for clause in subclauses]
                            result_clauses.append({'span_near': {'clauses': subclauses, 'slop': 0, 'in_order': True}})
                        else:
                            result_clauses.append({'span_term': {field: str(clause)}})
                    else:
                        result_clauses.append({'match': {field: str(clause)}})
        if operator[:2] == "W/":
            _, slop = operator.split("/", 1)
            return {'span_near': {'clauses': result_clauses, 'slop': slop, 'in_order': False}}
        elif operator == "OR":
            if in_near:
                return {'span_or': {'clauses': result_clauses}}
            else:
                return {'bool': {'should': result_clauses, 'minimum_should_match': 1}}
        elif operator == "AND":
            if in_near:
                return {'span_near': {'clauses': result_clauses, 'slop': 2147483647, 'in_order': False}}
            else:
                return {'bool': {'must': result_clauses }}
        elif operator == "AND NOT":
            if in_near:
                return {'span_not': {'include': result_clauses[0], 'exclude': result_clauses[1] }}
            else:
                return {'bool': {'should': result_clauses[0], 'must_not': result_clauses[1], 'minimum_should_match': 1}}
