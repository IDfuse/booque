# coding: utf-8
import logging
import json
import re
import lxml
import lxml.etree
import pyparsing
from pyparsing import(
        QuotedString, quotedString, Word,
        Literal, Regex,
        NotAny, FollowedBy, Combine, Optional, oneOf,
        alphanums,
    )

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

pyparsing.ParserElement.enablePackrat()

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
            (andop, 2, pyparsing.opAssoc.RIGHT),
            (andnotop, 2, pyparsing.opAssoc.RIGHT),
            (nearop, 2, pyparsing.opAssoc.RIGHT),
        ],
    )

class SearchTerm(object):
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
        self.term = term

    def __repr__(self):
        return self.term + ("[Q]" if self.has_quotes else "[]") + ("[P]" if self.is_phrase else "[]")

    def __str__(self):
        return self.term

class Parser(object):
    expr = pyparsing.infixNotation(
            term,
            [
                (implicitandop, 2, pyparsing.opAssoc.RIGHT),
                (orop, 2, pyparsing.opAssoc.LEFT),
                (andop, 2, pyparsing.opAssoc.RIGHT),
                (andnotop, 2, pyparsing.opAssoc.RIGHT),
                (nearop, 2, pyparsing.opAssoc.RIGHT),
            ],
        )
    def to_prefix(self, e):
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
        try:
            result = self.expr.parseString(query, parseAll=True)
        except pyparsing.ParseException as exc:
            print("Parse error:")
            print("  {0}:{1} HERE {2}".format(exc.lineno, exc.col, exc.markInputline()))
            raise
        result = self.to_prefix(result[0])
        return result

    def add_clauses(self, operator, clauses, field, in_near=False):
        fquery = {}
        result_clauses = []
        if operator[:2] == "W/":
            in_near = True
        if isinstance(clauses, str):
            return {'match': {field: clauses}}
        for clause in clauses:
            if isinstance(clause, dict):
                for suboperator, subclauses in clause.items():
                    result_clauses.append(self.add_clauses(suboperator, subclauses, field, in_near=in_near))
            elif isinstance(clause, SearchTerm):
                if clause.has_quotes and " " in str(clause) and not in_near:
                    if any(wildcard in str(clause) for wildcard in "*?"):
                        result_clauses.append({'intervals': { field: {'wildcard': { 'pattern': str(clause) } } } })
                    else:
                        result_clauses.append({'intervals': { field: {'match': { 'ordered': True, 'query': str(clause), 'max_gaps': 0 } } } })
                elif any(wildcard in str(clause) for wildcard in "*?"):
                    if in_near:
                        result_clauses.append({'span_multi': {"match": {"wildcard": {field: {"value": str(clause), "rewrite": "top_terms_50"}}}}})
                    else:
                        result_clauses.append({"wildcard": {field: {"value": str(clause)}}})
                elif clause.is_phrase:
                    result_clauses.append({'match_phrase': {field: str(clause)}})
                else:
                    if in_near:
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
