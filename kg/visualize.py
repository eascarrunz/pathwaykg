#!/usr/bin/env python3

import argparse
from pyvis.network import Network
from rdflib import Graph, URIRef
from rdflib.plugins.sparql import prepareQuery
from typing import Callable
import kg.namespaces as ns

NODE_TYPE_PALETTE = {
    ns.KG["Gene"]: "#4A90D9",
    ns.KG["Reaction"]: "#E8813A",
    ns.KG["Compound"]: "#5DB85D",
    ns.KG["KOTerm"]: "#9B59B6",
}
DEFAULT_COLOR = "#999999"

def color_by_type(uri: URIRef, graph: Graph) -> str:
    q = prepareQuery(f"SELECT ?nodetype WHERE{{ <{uri}> rdf:type ?nodetype }}", initNs={"rdf": ns.RDF})
    result = graph.query(q)
    try:
        node_type = next(iter(result)).nodetype
    except StopIteration:
        return DEFAULT_COLOR

    return NODE_TYPE_PALETTE.get(node_type, DEFAULT_COLOR)


def get_node_config(uri: URIRef, graph: Graph, color_fn: Callable) -> tuple[str, str, str]:
    q = prepareQuery(f"SELECT ?label WHERE{{ <{uri}> rdfs:label ?label }}", initNs={"rdfs": ns.RDFS})
    result = graph.query(q)
    try:
        label = next(iter(result)).label
    except StopIteration:
        label = uri.split('/')[-1]

    q = prepareQuery(f"""
SELECT ?p ?o
WHERE{{
    <{uri}> ?p ?o .
    FILTER(isLiteral(?o))
    }}
""", initNs={"rdfs": ns.RDFS})
    result = graph.query(q)

    metatip = ""
    for row in result:
        metatip += f"<b>{graph.namespace_manager.qname(row.p)}</b>: {row.o}<br>"

    color = color_fn(uri, graph)

    return (label, metatip, color)


def build_network(graph: Graph, color_fn: Callable = color_by_type) -> Network:
    pass

def main() -> int:
    pass
