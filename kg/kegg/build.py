#!/usr/bin/env python3

"""Build RDF knowledge graphs from KEGG data"""

import sys
import argparse
from pathlib import Path
from typing import Generator, Any, Iterable
from Bio.KEGG import Gene
from rdflib import Namespace, Graph, Literal, URIRef
import kg.namespaces as ns
import kg.kegg.fetch
import regex


def load_records_from_file(filepath: str | Path) -> Generator[Gene.Record, Any, None]:
    with open(filepath) as file:
        yield from Gene.parse(file)


def extract_ec(description: str) -> list[str]:
    return [ec for block in regex.findall(r"\[EC:([\d\.\- ]+)\]", description) for ec in block.split()]


def extract_dblinks(record: Gene.Record) -> dict[str, list]:
    return {key: value for key, value in record.dblinks}


def add_enzyme(
    graph: Graph, record: Gene.Record, organism_namespace: Namespace
) -> None:
    gene_uri = organism_namespace[record.entry.split(":")[-1]]
    gene_dblinks = extract_dblinks(record)

    graph.add((gene_uri, ns.RDF.type, ns.KG["Gene"]))
    for name in record.name:
        graph.add((gene_uri, ns.RDFS.label, Literal(name)))
    graph.add((gene_uri, ns.KG["keggID"], URIRef(f"https://www.kegg.jp/entry/{record.entry}")))
    for accession in gene_dblinks.get("UniProt", []):
        graph.add((gene_uri, ns.OWL.sameAs, ns.UNIPROT[accession]))

    for ko, description in record.orthology:
        graph.add((gene_uri, ns.KG["hasOrtholog"], ns.KEGG[ko]))

        for ec in extract_ec(description):
            graph.add((gene_uri, ns.KG["hasEC"], ns.EC[ec]))

        graph.add((ns.KEGG[ko], ns.RDF.type, ns.KG["KOTerm"]))
        graph.add((ns.KEGG[ko], ns.RDFS.label, Literal(description)))

    return None


def build_kg(records: Iterable[Gene.Record], organism_id: str) -> Graph:
    organism_namespace = ns.create_organism_namespace(organism_id)
    graph = Graph()
    graph.bind(organism_id, organism_namespace)

    for record in records:
        add_enzyme(graph, record, organism_namespace)

    return graph


def main() -> int:
    arg_parser = argparse.ArgumentParser("BuildKG", description="Build an RDF knowledge graph for a pathway")
    arg_parser.add_argument("--file", "-f", type=Path, help="Path to KEGG pathway file")
    arg_parser.add_argument("--organism", "-o", type=str, help="KEGG organism ID")
    arg_parser.add_argument("--pathway", "-p", type=str, help="KEGG pathway ID")

    args = arg_parser.parse_args()

    records: Iterable[Gene.Record] | None = None

    if args.organism:
        if args.file:
            records = load_records_from_file(args.file)
        else:
            if args.pathway:
                text = kg.kegg.fetch.fetch_pathway_genes(args.organism, args.pathway)
                gene_ids = kg.kegg.fetch.extract_gene_ids(text)
                records = kg.kegg.fetch.fetch_gene_records(gene_ids)
            else:
                print("You must provide either a KEGG pathway ID or a KEGG pathway file")

                return 1
    else:
        print("You must provide a KEGG organism ID")

        return 1
    
    g = build_kg(records, args.organism)

    g.serialize(sys.stdout.buffer, "turtle")

    return 0

if __name__ == "__main__":
    main()
