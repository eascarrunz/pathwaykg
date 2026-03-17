#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path
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

EDGE_PREDICATES = (
    ns.KG["hasOrtholog"],
    ns.KG["hasEC"],
    ns.KG["hasSubstrate"],
    ns.KG["hasProduct"],
)

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

    metatip = '\n'.join(f"{graph.namespace_manager.qname(row.p)}: {row.o}" for row in result)

    color = color_fn(uri, graph)

    return (label, metatip, color)


def build_network(graph: Graph, color_fn: Callable = color_by_type) -> Network:
    nw = Network(directed=True)

    q = prepareQuery(f"""
SELECT ?s ?p ?o
WHERE{{
    ?s ?p ?o .
    FILTER(?p IN ({ ", ".join(f"<{p}>" for p in EDGE_PREDICATES) }))
    }}
""", initNs={"kg": ns.KG})
    result = graph.query(q)

    for row in result:
        s_label, s_metatip, s_color = get_node_config(row.s, graph, color_fn)
        nw.add_node(n_id=str(row.s), label=s_label, color=s_color, title=s_metatip)
        o_label, o_metatip, o_color = get_node_config(row.o, graph, color_fn)
        nw.add_node(n_id=str(row.o), label=o_label, color=o_color, title=o_metatip)
        if row.p == ns.KG["hasSubstrate"]:
            nw.add_edge(str(row.o), str(row.s), title="substrateOf")
        else:
            nw.add_edge(str(row.s), str(row.o), title=graph.namespace_manager.qname(row.p))

    return nw

def main() -> int:
    arg_parser = argparse.ArgumentParser(prog="Visualize", description="Create a dynamic HTML plot of a pathway from a RDF graph")
    arg_parser.add_argument("-i", "--input", type=Path, help="Path to RDF file in Turtle format")
    arg_parser.add_argument("-o", "--output", type=Path, help="Path for output HTML file")
    args = arg_parser.parse_args()

    graph = Graph()

    if args.input:
        with open(args.input) as infile:
            graph.parse(infile)
    else:
        graph.parse(sys.stdin.buffer)

    nw = build_network(graph)

    if args.output:
        nw.save_graph(str(args.output))
    else:
        sys.stdout.write(nw.html)

    return 0

if __name__ == "__main__":
    main()
