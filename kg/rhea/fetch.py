#!/usr/bin/env python3

"""Fetch EC data from the Rhea database"""

import argparse
import kg.namespaces as ns
from typing import Iterable
from rdflib import URIRef
from urllib.request import urlopen, Request
from urllib.parse import urlencode
import json

RHEA_SPARQL_ENDPOINT = "https://sparql.rhea-db.org/sparql"


def fetch_ec_reactions(
    ec_uris: Iterable[URIRef], endpoint: str = RHEA_SPARQL_ENDPOINT
) -> list[dict]:
    query_string = f"""
PREFIX ec: <http://purl.uniprot.org/enzyme/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rh: <http://rdf.rhea-db.org/>
# Query 9
# Select all Rhea reactions mapped to EC numbers (enzyme classification)
#
# This query corresponds to the Rhea website query:
# https://www.rhea-db.org/rhea?query=ec:*
#
SELECT ?ec ?ecNumber ?rhea ?accession ?equation ?compound ?compoundLabel ?isSubstrate ?chebi
WHERE {{
  VALUES ?ec {{ {" ".join(f"<{ec}>" for ec in ec_uris)} }}
  ?rhea rh:status rh:Approved .
  ?rhea rdfs:subClassOf rh:Reaction .
  ?rhea rh:accession ?accession .
  ?rhea rh:ec ?ec .
  ?rhea rh:side ?side .
  ?side rh:contains ?participant .
  ?participant rh:compound ?compound .
  ?compound rh:name ?compoundLabel .
  ?compound rh:chebi ?chebi .
  BIND(STRENDS(str(?side), "_L") AS ?isSubstrate)
  BIND(strafter(str(?ec),str(ec:)) as ?ecNumber)
  ?rhea rh:equation ?equation .
}}
"""
    data = urlencode({"query": query_string}).encode()
    req = Request(
        endpoint, data=data, headers={"Accept": "application/sparql-results+json"}
    )
    response = json.load(urlopen(req))
    return response["results"]["bindings"]


def main() -> int:
    arg_parser = argparse.ArgumentParser(
        "Rhea Fetcher",
        description="Build an knogledge graph of directional Rhea reactions based on EC URIs.",
    )
    arg_parser.add_argument("--ec", nargs="+", type=str, help="EC URIs")
    args = arg_parser.parse_args()

    ecs = [ns.EC[ec] for ec in args.ec]

    result = fetch_ec_reactions(ecs)

    for row in result:
        print(row)

    return 0


if __name__ == "__main__":
    main()
