#!/usr/bin/env python3

"""Build an RDF knowledge graph for a metabolic pathway aggregating data from the KEGG and Rhea databases"""

import sys
import argparse
import kg.kegg.build
import kg.kegg.fetch
import kg.rhea.build
import kg.rhea.fetch
from pathlib import Path
from typing import Iterable
from Bio.KEGG import Gene
from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery
import kg.namespaces as ns

def build_kg(organism_id: str, records: Iterable[Gene.Record]) -> Graph:
    kegg_graph = kg.kegg.build.build_kg(records, organism_id)

    q = prepareQuery("SELECT ?ec WHERE { ?g kg:hasEC ?ec }", initNs={"kg": ns.KG})
    ec_result = kegg_graph.query(q)
    ecs = [row.ec for row in ec_result]

    rhea_graph = kg.rhea.build.build_kg(kg.rhea.fetch.fetch_ec_reactions(ecs))

    return kegg_graph + rhea_graph

def main() -> int:
    arg_parser = argparse.ArgumentParser("BuildKG", description="Build an RDF knowledge graph for a pathway")
    arg_parser.add_argument("--file", "-f", type=Path, help="Path to KEGG pathway file")
    arg_parser.add_argument("--organism", "-o", type=str, help="KEGG organism ID")
    arg_parser.add_argument("--pathway", "-p", type=str, help="KEGG pathway ID")

    args = arg_parser.parse_args()

    records: Iterable[Gene.Record] | None = None

    if args.organism:
        if args.file:
            records = kg.kegg.build.load_records_from_file(args.file)
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
    
    total_graph = build_kg(args.organism, records)

    total_graph.serialize(sys.stdout.buffer, format="turtle")

    return 0

if __name__ == "__main__":
    main()
