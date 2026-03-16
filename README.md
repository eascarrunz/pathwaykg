# Pathway knowledge graphs

This tool creates [RDF](https://en.wikipedia.org/wiki/Resource_Description_Framework) knowledge graphs for metabolic pathways in the KEGG database.

## Usage

Clone the repo and run with [uv](https://docs.astral.sh/uv/), which handles the virtual environment and dependencies automatically:

```bash
git clone <repo>
cd pathway-kg-maker
uv run python -m kg.build -o <organism_id> -p <pathway_id>
```

Alternatively, install with pip and use the `kgbuild` command:

```bash
pip install .
kgbuild -o <organism_id> -p <pathway_id>
```

You need to provide IDs from the KEGG database corresponding to an [organism](https://www.genome.jp/kegg/tables/br08606.html) and a [pathway](https://www.genome.jp/kegg/pathway.html).

For example, human glycolysis:

```bash
uv run python -m kg.build -o hsa -p 00010
```

Load from a local KEGG flat file instead:

```bash
uv run python -m kg.build -o hsa --file genes.txt
```

Output is written to stdout and can be redirected to a file:

```bash
uv run python -m kg.build -o hsa -p 00010 > hsa_00010.ttl
```
