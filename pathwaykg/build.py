#!/usr/bin/env python3

"""Build RDF knowledge graphs from KEGG data"""

import sys
import argparse
from tqdm import tqdm
from pathlib import Path
from typing import Generator, Any, Iterable
from Bio.KEGG import Gene, Compound
from rdflib.plugins.sparql import prepareQuery
from rdflib import Namespace, Graph, Literal, URIRef
import pathwaykg.namespaces as ns
from pathwaykg.fetch import fetch_pathway_kgml, parse_kgml, KGMLData, fetch_gene_records, fetch_reaction_records, fetch_compound_records
import regex

def add_reaction(graph: Graph, reaction_record: dict) -> None:
    reaction_uri = ns.KEGG[reaction_record["id"]]
    graph.add((reaction_uri, ns.RDF.type, ns.KG["Reaction"]))
    graph.add((reaction_uri, ns.RDFS.label, Literal(reaction_record["definition"])))
    
    for id in reaction_record["substrates"]:
        compound_uri = ns.KEGG[id]
        graph.add((reaction_uri, ns.KG["hasSubstrate"], compound_uri))

    for id in reaction_record["products"]:
        compound_uri = ns.KEGG[id]
        graph.add((reaction_uri, ns.KG["hasProduct"], compound_uri))

    for ec in reaction_record.get("enzymes", []):
        graph.add((reaction_uri, ns.KG["hasEC"], ns.EC[ec]))

    return None


def add_compound(graph: Graph, compound_record: Compound.Record) -> None:
    compound_uri = ns.KEGG[compound_record.entry]

    graph.add((compound_uri, ns.RDF.type, ns.KG["Compound"]))
    graph.add((compound_uri, ns.RDFS.label, Literal(compound_record.name[0])))

    return None


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
            graph.add((ns.KEGG[ko], ns.KG["hasEC"], ns.EC[ec]))
            graph.add((gene_uri, ns.KG["hasEC"], ns.EC[ec]))

        graph.add((ns.KEGG[ko], ns.RDF.type, ns.KG["KOTerm"]))
        graph.add((ns.KEGG[ko], ns.RDFS.label, Literal(description)))

    return None


def build_kg(organism_id: str, kgml_data: KGMLData) -> Graph:
    organism_namespace = ns.create_organism_namespace(organism_id)
    graph = Graph()
    graph.bind(organism_id, organism_namespace)
    graph.bind("kg", ns.KG)
    graph.bind("kegg", ns.KEGG)
    graph.bind("ec", ns.EC)

    gene_records = fetch_gene_records(kgml_data.gene_ids)
    prog_desc = "Fetching gene data"
    for record in tqdm(gene_records, total=len(kgml_data.gene_ids), desc= prog_desc, file=sys.stderr):
        add_enzyme(graph, record, organism_namespace)

    reaction_records = fetch_reaction_records(kgml_data.reaction_ids)
    prog_desc = "Fetching reaction data"
    for record in tqdm(reaction_records, total=len(kgml_data.reaction_ids), desc=prog_desc, file=sys.stderr):
        add_reaction(graph, record)

    q = prepareQuery("""
SELECT DISTINCT ?compound WHERE {
    { ?reaction kg:hasSubstrate ?compound }
    UNION
    { ?reaction kg:hasProduct ?compound }
}
""", initNs={"kg": ns.KG})

    compound_ids = {str(row.compound).split("/")[-1] for row in graph.query(q)}

    compound_records = fetch_compound_records(compound_ids)
    prog_desc = "Fetching compound data"
    for record in tqdm(compound_records, total=len(compound_ids), desc=prog_desc, file=sys.stderr):
        add_compound(graph, record)

    for gene_id, reactions in kgml_data.gene_reactions.items():
        gene_uri = organism_namespace[gene_id.split(':')[-1]]
        for reaction in reactions:
            reaction_uri = ns.KEGG[reaction]
            graph.add((gene_uri, ns.KG["catalyzes"], reaction_uri))

    return graph


def main() -> int:
    arg_parser = argparse.ArgumentParser("BuildKG", description="Build an RDF knowledge graph for a pathway")
    arg_parser.add_argument("--organism", "-o", type=str, help="KEGG organism ID")
    arg_parser.add_argument("--pathway", "-p", type=str, help="KEGG pathway ID")

    args = arg_parser.parse_args()

    if not args.organism:
        print("You must provide a KEGG organism ID")

        return 1
    
    if not args.pathway:
        print("You must provide a KEGG pathway ID")

        return 1
    
    kgml_data = parse_kgml(fetch_pathway_kgml(args.organism, args.pathway))

    g = build_kg(args.organism, kgml_data)

    g.serialize(sys.stdout.buffer, "turtle")

    return 0

if __name__ == "__main__":
    main()
