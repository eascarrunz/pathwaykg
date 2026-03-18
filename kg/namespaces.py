from rdflib import Namespace, OWL, RDF, RDFS

_KG_BASE_URL = "https://github.com/eascarrunz/pathwaykg/"

_ORGANISM_BASE_URL = _KG_BASE_URL + "organism/"


def create_organism_namespace(org_id: str) -> Namespace:
    return Namespace(f"{_ORGANISM_BASE_URL}{org_id}/")


KEGG = Namespace("https://www.kegg.jp/entry/")
UNIPROT = Namespace("https://identifiers.org/uniprot:")
KG = Namespace(_KG_BASE_URL + "ontology/")
EC = Namespace("http://purl.uniprot.org/enzyme/")
RHEA = Namespace("https://rdf.rhea-db.org/")
