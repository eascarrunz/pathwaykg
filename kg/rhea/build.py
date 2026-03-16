#!/usr/bin/env python3

"""
Build RDF knowledge graphs from Rhea data
"""

import sys
import argparse
import kg.namespaces as ns
import kg.rhea.fetch
from rdflib import Graph, URIRef, Literal


def add_reaction(graph: Graph, reaction_node: dict) -> None:
    reaction_uri = URIRef(reaction_node["rhea"]["value"])
    graph.add((reaction_uri, ns.RDF.type, ns.KG["Reaction"]))
    ec_uri = URIRef(reaction_node["ec"]["value"])
    graph.add((reaction_uri, ns.KG["hasEC"], ec_uri))
    equation = Literal(reaction_node["equation"]["value"])
    graph.add((reaction_uri, ns.RDFS.label, equation))
    accession = Literal(reaction_node["accession"]["value"])
    graph.add((reaction_uri, ns.KG["accession"], accession))
    compound_uri = URIRef(reaction_node["compound"]["value"])
    graph.add((compound_uri, ns.RDF.type, ns.KG["Compound"]))
    chebi_uri = URIRef(reaction_node["chebi"]["value"])
    graph.add((compound_uri, ns.OWL.sameAs, chebi_uri))
    compound_label = Literal(reaction_node["compoundLabel"]["value"])
    graph.add((compound_uri, ns.RDFS.label, compound_label))

    if reaction_node["isSubstrate"]["value"] == "true":
        relation_to_compound = ns.KG["hasSubstrate"]
    else:
        relation_to_compound = ns.KG["hasProduct"]

    graph.add((reaction_uri, relation_to_compound, compound_uri))

    return None


def build_kg(reaction_nodes: list[dict]) -> Graph:
    graph = Graph()
    graph.bind("kg", ns.KG)
    graph.bind("rh", ns.RHEA)
    graph.bind("ec", ns.EC)
    graph.bind("owl", ns.OWL)
    graph.bind("rdfs", ns.RDFS)

    for reaction_node in reaction_nodes:
        add_reaction(graph, reaction_node)

    return graph


def main() -> int:
    arg_parser = argparse.ArgumentParser("Build Rhea", description="Build a Rhea RDS knowledge graph")
    arg_parser.add_argument("--ec", nargs="+", type=str, help="EC URIs")

    args = arg_parser.parse_args()

    ecs = [ns.EC[ec] for ec in args.ec]

    result = kg.rhea.fetch.fetch_ec_reactions(ecs)

    graph = build_kg(result)

    graph.serialize(sys.stdout.buffer, format="turtle")

    return 0


if __name__ == "__main__":
    main()
