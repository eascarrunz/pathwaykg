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

KG_EDGE_PREDICATES = (
    ns.KG["hasOrtholog"],
    ns.KG["hasEC"],
    ns.KG["hasSubstrate"],
    ns.KG["hasProduct"],
)

COMPOUND_EDGE_PREDICATES = (
    ns.KG["hasSubstrate"],
    ns.KG["hasProduct"]
)


def color_by_type(uri: URIRef, graph: Graph) -> str:
    q = prepareQuery(
        f"SELECT ?nodetype WHERE{{ <{uri}> rdf:type ?nodetype }}",
        initNs={"rdf": ns.RDF},
    )
    result = graph.query(q)
    try:
        node_type = next(iter(result)).nodetype
    except StopIteration:
        return DEFAULT_COLOR

    return NODE_TYPE_PALETTE.get(node_type, DEFAULT_COLOR)


def get_node_config(
    uri: URIRef, graph: Graph, color_fn: Callable
) -> tuple[str, str, str]:
    q = prepareQuery(
        f"SELECT ?label WHERE{{ <{uri}> rdfs:label ?label }}", initNs={"rdfs": ns.RDFS}
    )
    result = graph.query(q)
    try:
        label = next(iter(result)).label
    except StopIteration:
        label = uri.split("/")[-1]

    q = prepareQuery(
        f"""
SELECT ?p ?o
WHERE{{
    <{uri}> ?p ?o .
    FILTER(isLiteral(?o))
    }}
""",
        initNs={"rdfs": ns.RDFS},
    )
    result = graph.query(q)

    metatip = "\n".join(
        f"{graph.namespace_manager.qname(row.p)}: {row.o}" for row in result
    )

    color = color_fn(uri, graph)

    return (label, metatip, color)


def build_kg_network(graph: Graph, color_fn: Callable = color_by_type) -> Network:
    nw = Network(directed=True)

    q = prepareQuery(
        f"""
SELECT ?s ?p ?o
WHERE{{
    ?s ?p ?o .
    FILTER(?p IN ({", ".join(f"<{p}>" for p in KG_EDGE_PREDICATES)}))
    }}
""",
        initNs={"kg": ns.KG},
    )
    result = graph.query(q)

    for row in result:
        s_label, s_metatip, s_color = get_node_config(row.s, graph, color_fn)
        nw.add_node(n_id=str(row.s), label=s_label, color=s_color, title=s_metatip)
        o_label, o_metatip, o_color = get_node_config(row.o, graph, color_fn)
        nw.add_node(n_id=str(row.o), label=o_label, color=o_color, title=o_metatip)
        nw.add_edge(str(row.s), str(row.o), title=graph.namespace_manager.qname(row.p))

    return nw


def build_ko_pathway_network(
    graph: Graph, color_fn: Callable = color_by_type
) -> Network:
    nw = Network(directed=True)

    q = prepareQuery("""
SELECT ?ko ?reaction (COUNT(?gene) AS ?geneCount) (GROUP_CONCAT(?geneId; separator=", ") AS ?genes)
WHERE {
    ?reaction rdf:type kg:Reaction .
    ?gene kg:hasOrtholog ?ko .
    ?gene kg:hasEC ?ec .
    ?reaction kg:hasEC ?ec .
    BIND(strafter(str(?gene), "/") AS ?geneId)
}
GROUP BY ?ko ?reaction
""", initNs={"kg": ns.KG, "rdf": ns.RDF})
    
    result = graph.query(q)

    for row in result:
        ko_label, ko_metatip, ko_color = get_node_config(row.ko, graph, color_fn)
        ko_metatip += f"\nGene count: {str(row.geneCount)}\nGenes: {row.genes}"
        nw.add_node(str(row.ko), label=ko_label, title=ko_metatip, color=ko_color)
        reaction_label, reaction_metatip, reaction_color = get_node_config(row.reaction, graph, color_fn)
        nw.add_node(str(row.reaction), label=reaction_label, title=reaction_metatip, color=reaction_color)
        nw.add_edge(str(row.ko), str(row.reaction), title="Catalyzes")

    q = prepareQuery(
        f"""
SELECT ?s ?p ?o
WHERE{{
    ?s ?p ?o .
    FILTER(?p IN ({", ".join(f"<{p}>" for p in COMPOUND_EDGE_PREDICATES)}))
    }}
""",
        initNs={"kg": ns.KG},
    )
    result = graph.query(q)

    for row in result:
        if str(row.s) in nw.node_ids:
            o_label, o_metatip, o_color = get_node_config(row.o, graph, color_fn)
            nw.add_node(str(row.o), label=o_label, title=o_metatip, color=o_color)
            if row.p == ns.KG["hasSubstrate"]:
                nw.add_edge(str(row.o), str(row.s), label="substrateOf")
            elif row.p == ns.KG["hasProduct"]:
                nw.add_edge(str(row.s), str(row.o), label="hasProduct")

    return nw


def main() -> int:
    arg_parser = argparse.ArgumentParser(
        prog="Visualize",
        description="Create a dynamic HTML plot of a pathway from a RDF graph",
    )
    arg_parser.add_argument(
        "-i", "--input", type=Path, help="Path to RDF file in Turtle format"
    )
    arg_parser.add_argument(
        "-o", "--output", type=Path, help="Path for output HTML file"
    )
    args = arg_parser.parse_args()

    graph = Graph()

    if args.input:
        with open(args.input) as infile:
            graph.parse(infile)
    else:
        graph.parse(sys.stdin.buffer)

    nw = build_ko_pathway_network(graph)

    if args.output:
        nw.save_graph(str(args.output))
    else:
        sys.stdout.write(nw.html)

    return 0


if __name__ == "__main__":
    main()
