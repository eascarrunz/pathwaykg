#!/usr/bin/env python3

"""Functions for fetching data to build pathway knowledge graphs"""

import sys
from dataclasses import dataclass, field
from xml.etree import ElementTree
import io
import urllib
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)
from typing import Generator, Any, TextIO, Iterable
import itertools
from Bio.KEGG import Gene, REST, Compound

KEGG_REST_GET_BATCH_LIMIT = 10

WAIT_EXPONENTIAL_ARGS = {
    "multiplier": 1,
    "min": 2,
    "max": 10
}

@dataclass
class KGMLData:
    gene_ids: set[str] = field(default_factory=set)
    ko_ids: set[str] = field(default_factory=set)
    ko_reactions: dict[str, set[str]] = field(default_factory=dict)
    gene_reactions: dict[str, set[str]] = field(default_factory=dict)
    reaction_ids: set[str] = field(default_factory=set)
    compound_ids: set[str] = field(default_factory=set)


@retry(
    wait=wait_exponential(**WAIT_EXPONENTIAL_ARGS),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(urllib.error.URLError),
)
def fetch_pathway_kgml(organism_id: str, pathway_id: str) -> TextIO:
    return REST.kegg_get(f"{organism_id}{pathway_id}", "kgml")

def parse_kgml(handle: TextIO) -> KGMLData:
    data = KGMLData()
    root = ElementTree.parse(handle).getroot()

    for entry in root.findall("entry"):
        entry_ids = entry.get("name").split()
        reaction_string = entry.get("reaction")

        match entry.get("type"):
            case "gene":
                data.gene_ids.update(entry_ids)
                if reaction_string:
                    reaction_ids = [s.split(':')[-1] for s in reaction_string.split()]
                    for gene_id in entry_ids:
                        data.gene_reactions.setdefault(gene_id, set()).update(reaction_ids)
                    data.reaction_ids.update(reaction_ids)
            case "ortholog":
                ortholog_ids = [s.split(':')[-1] for s in entry_ids]
                data.ko_ids.update(ortholog_ids)
                if reaction_string:
                    reaction_ids = [s.split(':')[-1] for s in reaction_string.split()]
                    for ko_id in ortholog_ids:
                        data.ko_reactions.setdefault(ko_id, set()).update(reaction_ids)
            case "compound":
                data.compound_ids.update([s.split(':')[-1] for s in entry_ids])

    return data

@retry(
    wait=wait_exponential(**WAIT_EXPONENTIAL_ARGS),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(urllib.error.URLError),
)
def _fetch_batch(batch_ids: list[str]) -> io.TextIOWrapper:
    # print(batch_ids, file=sys.stderr)
    return REST.kegg_get(batch_ids)


def fetch_generic_records(ids: Iterable[str]) -> Generator[str, Any, None]:
    for batch_ids in itertools.batched(ids, KEGG_REST_GET_BATCH_LIMIT):
        yield from (block for block in _fetch_batch(list(batch_ids)).read().split("///") if block.strip())


"""
The relevant bits of a typical reaction entry look like this:

ENTRY       R00341                      Reaction
NAME        ATP:oxaloacetate carboxy-lyase (transphosphorylating;phosphoenolpyruvate-forming)
DEFINITION  ATP + Oxaloacetate <=> ADP + Phosphoenolpyruvate + CO2
EQUATION    C00002 + C00036 <=> C00008 + C00074 + C00011
"""
def parse_reaction_record(text: str) -> dict:
    data = {}

    for line in text.splitlines():
        keyword = line[0:12].strip()
        match keyword:
            case "ENTRY":
                data["id"] = line[12:].split()[0].strip()
            case "DEFINITION":
                data["definition"] = line[12:].strip()
            case "EQUATION":
                left, right = [part.strip() for part in line[12:].split("<=>")]
                data["substrates"] = [substrate.split()[-1].strip() for substrate in left.split('+')]
                data["products"] = [product.split()[-1].strip() for product in right.split('+')]
            case "ENZYME":
                data["enzymes"] = line[12:].split()
            case _:
                pass

    return data


def fetch_reaction_records(reaction_ids: set[str]) -> Generator[dict, Any, None]:
    for block in fetch_generic_records(reaction_ids):
        yield parse_reaction_record(block)


def fetch_compound_records(compound_ids: set[str]) -> Generator[Compound.Record, Any, None]:
    for batch_ids in itertools.batched(compound_ids, KEGG_REST_GET_BATCH_LIMIT):
        yield from Compound.parse(_fetch_batch(list(batch_ids)))



@retry(
    wait=wait_exponential(**WAIT_EXPONENTIAL_ARGS),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(urllib.error.URLError),
)
def fetch_pathway_genes(organism_id: str, pathway_id: str) -> str:
    response = REST.kegg_link(organism_id, f"path:{organism_id}{pathway_id}")

    return response.read()


def extract_gene_ids(text: str) -> list[str]:
    return sorted(set(row.split()[-1].strip() for row in text.splitlines()))





def fetch_gene_records(gene_ids: list[str]) -> Generator[Gene.Record, Any, None]:
    for batch_ids in itertools.batched(gene_ids, KEGG_REST_GET_BATCH_LIMIT):
        yield from Gene.parse(_fetch_batch(list(batch_ids)))


def main():
    organism_id = input("Give an organism ID:\t")
    pathway_id = input("Give a pathway ID:\t")

    # text = fetch_pathway_genes(organism_id, pathway_id)
    # gene_ids = extract_gene_ids(text)
    # print(gene_ids)
    # gene_records = fetch_gene_records(gene_ids)

    # for record in gene_records:
    #     print(record.dblinks)

    # print(text)

    xml_handle = fetch_pathway_kgml(organism_id, pathway_id)
    data = parse_kgml(xml_handle)
    reaction_records = fetch_generic_records(data.reaction_ids)

    for record in reaction_records:
        reaction_data = parse_reaction_record(record)

        for compound_record in fetch_compound_records(reaction_data["substrates"]):
            print(compound_record.entry)
            print(compound_record.name)
            break
        break

    # sys.stdout.write('\n'.join(reaction_records[:10]))

    return 0


if __name__ == "__main__":
    main()
