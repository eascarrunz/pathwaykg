#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path
from pyvis.network import Network
from rdflib import Graph, URIRef
from rdflib.plugins.sparql import prepareQuery
from typing import Callable, TextIO
import kg.namespaces as ns

NODE_OVERLAP_PALETTE = {
    "a": "#66c2a5",
    "b": "#fc8d62",
    "common": "#8da0cb",
    "unk": "#000000",
}

NODE_TYPE_PALETTE = {
    ns.KG["Gene"]: "#386cb0",
    ns.KG["Reaction"]: "#beaed4",
    ns.KG["Compound"]: "#ffff99",
    ns.KG["KOTerm"]: "#7fc97f",
}
DEFAULT_COLOR = "#999999"

KG_EDGE_PREDICATES = (
    ns.KG["hasOrtholog"],
    ns.KG["hasEC"],
    ns.KG["hasSubstrate"],
    ns.KG["hasProduct"],
)

COMPOUND_EDGE_PREDICATES = (ns.KG["hasSubstrate"], ns.KG["hasProduct"])


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


def make_overlap_color_fn(graph_a: Graph, graph_b: Graph) -> Callable:
    nodes_a = set(graph_a.subjects())
    nodes_b = set(graph_b.subjects())
    nodes_a_only = nodes_a.difference(nodes_b)
    nodes_b_only = nodes_b.difference(nodes_a)
    nodes_common = nodes_a.intersection(nodes_b)
    nodes_a = nodes_b = None

    def color_by_overlap(uri: URIRef, _: Graph) -> str:
        if uri in nodes_common:
            return NODE_OVERLAP_PALETTE["common"]
        elif uri in nodes_a_only:
            return NODE_OVERLAP_PALETTE["a"]
        elif uri in nodes_b_only:
            return NODE_OVERLAP_PALETTE["b"]
        else:
            return NODE_OVERLAP_PALETTE["unk"]

    return color_by_overlap


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
    nw = Network(directed=True, cdn_resources="in_line")

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
    nw = Network(directed=True, cdn_resources="in_line")

    q = prepareQuery(
        """
SELECT ?ko ?reaction (COUNT(?gene) AS ?geneCount) (GROUP_CONCAT(?geneId; separator=", ") AS ?genes)
WHERE {
    ?gene kg:catalyzes ?reaction .
    ?gene kg:hasOrtholog ?ko .
    BIND(strafter(str(?gene), "/") AS ?geneId)
}
GROUP BY ?ko ?reaction
""",
        initNs={"kg": ns.KG, "rdf": ns.RDF},
    )

    result = graph.query(q)

    for row in result:
        ko_label, ko_metatip, ko_color = get_node_config(row.ko, graph, color_fn)
        ko_metatip += f"\nGene count: {str(row.geneCount)}\nGenes: {row.genes}"
        nw.add_node(str(row.ko), label=ko_label, title=ko_metatip, color=ko_color)
        reaction_label, reaction_metatip, reaction_color = get_node_config(
            row.reaction, graph, color_fn
        )
        nw.add_node(
            str(row.reaction),
            label=reaction_label,
            title=reaction_metatip,
            color=reaction_color,
            shape="diamond",
        )
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
            nw.add_node(
                str(row.o),
                label=o_label,
                title=o_metatip,
                color=o_color,
                shape="square",
            )
            if row.p == ns.KG["hasSubstrate"]:
                nw.add_edge(str(row.o), str(row.s), label="substrateOf")
            elif row.p == ns.KG["hasProduct"]:
                nw.add_edge(str(row.s), str(row.o), label="hasProduct")

    return nw


def visualize_single_graph(infile: TextIO) -> Network:
    graph = Graph()
    graph.parse(infile)

    return build_ko_pathway_network(graph, color_fn=color_by_type)


def visualize_graph_overlap(infile_a: TextIO, infile_b: TextIO) -> Network:
    graph_a = Graph()
    graph_a.parse(infile_a)

    graph_b = Graph()
    graph_b.parse(infile_b)

    color_fn = make_overlap_color_fn(graph_a, graph_b)

    graph_ab = graph_a + graph_b    # Magick!

    return build_ko_pathway_network(graph_ab, color_fn=color_fn)


def main() -> int:
    arg_parser = argparse.ArgumentParser(
        prog="Visualize",
        description="Create a dynamic HTML plot of a pathway from a RDF graph",
    )
    arg_parser.add_argument(
        "-i", "--input", nargs='+', type=Path, help="Path to RDF file in Turtle format, include a second file to visualize the graph overlap"
    )
    arg_parser.add_argument(
        "-o", "--output", type=Path, help="Path for output HTML file"
    )
    args = arg_parser.parse_args()

    if args.input:
        if len(args.input) == 1:
            with open(args.input[0]) as infile:
                nw = visualize_single_graph(infile)
        elif len(args.input) == 2:
            with open(args.input[0]) as infile_a, open(args.input[1]) as infile_b:
                nw = visualize_graph_overlap(infile_a, infile_b)
        else:
            print("Must provide either one or two input RDF graph files", file=sys.stderr)

            return 1
    else:
        nw = visualize_single_graph(sys.stdin.buffer)

    if args.output:
        nw.save_graph(str(args.output))
    else:
        sys.stdout.write(nw.html)

    return 0


if __name__ == "__main__":
    main()
