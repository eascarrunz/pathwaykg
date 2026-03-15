#!/usr/bin/env python3

"""Functions for fetching data to build pathway knowledge graphs"""

import io
import urllib
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)
from typing import Generator, Any
import itertools
from Bio.KEGG import Gene, REST

KEGG_REST_GET_BATCH_LIMIT = 10

WAIT_EXPONENTIAL_ARGS = {
    "multiplier": 1,
    "min": 2,
    "max": 10
}


@retry(
    wait=wait_exponential(**WAIT_EXPONENTIAL_ARGS),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(urllib.error.HTTPError),
)
def fetch_pathway_genes(organism_id: str, pathway_id: str) -> str:
    response = REST.kegg_link(organism_id, f"path:{organism_id}{pathway_id}")

    return response.read()


def extract_gene_ids(text: str) -> list[str]:
    return sorted(set(row.split()[-1].strip() for row in text.splitlines()))


@retry(
    wait=wait_exponential(**WAIT_EXPONENTIAL_ARGS),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(urllib.error.HTTPError),
)
def _fetch_batch(batch_ids: list[str]) -> io.TextIOWrapper:
    return REST.kegg_get(batch_ids)


def fetch_gene_records(gene_ids: list[str]) -> Generator[Gene.Record, Any, None]:
    for batch_ids in itertools.batched(gene_ids, KEGG_REST_GET_BATCH_LIMIT):
        yield from Gene.parse(_fetch_batch(list(batch_ids)))


def main():
    organism_id = input("Give an organism ID:\t")
    pathway_id = input("Give a pathway ID:\t")

    text = fetch_pathway_genes(organism_id, pathway_id)
    gene_ids = extract_gene_ids(text)
    print(gene_ids)
    gene_records = fetch_gene_records(gene_ids)

    for record in gene_records:
        print(record)

    print(text)

    return 0


if __name__ == "__main__":
    main()
