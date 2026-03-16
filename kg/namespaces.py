from rdflib import Namespace, OWL, RDF, RDFS

_ORGANISM_BASE_URL = "https://example.org/kg/organism/"


def create_organism_namespace(org_id: str) -> Namespace:
    return Namespace(f"{_ORGANISM_BASE_URL}{org_id}/")


KEGG = Namespace("https://www.kegg.jp/entry/")
UNIPROT = Namespace("https://identifiers.org/uniprot:")
KG = Namespace("https://example.org/kg/ontology/")
EC = Namespace("https://identifiers.org/ec-code:")
