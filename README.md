# Knowledge graphs of KEGG pathways

![hsa00232: Pathway of caffeine metabolism in humans](assets/hsa00232.png)

This project includes scripts for building [RDF](https://en.wikipedia.org/wiki/Resource_Description_Framework) knowledge graphs and visualizing pathways from the KEGG database. You can visualize one pathway graph at the time, or combine pathways from two different species to see their overlap.


## Installation

First, clone this repo and enter the directory. I recommend using the option `--depth=1` to only copy the current version of the files.

```bash
git clone --depth=1 https://github.com/eascarrunz/pathwaykg
cd pathwaykg
```

### Option 1: Run with uv (no install needed)

[uv](https://docs.astral.sh/uv/) can run the project directly without an explicit install step — it reads `pyproject.toml` and resolves dependencies automatically. Just prepend `uv run` to the commands. For example:

```bash
uv run kgbuild -p hsa00010 > hsa00010.ttl
```

### Option 2: Install with uv

To install the project into a virtual environment managed by uv:

```bash
uv sync
```

Then run commands through uv as in **option 1**:

```bash
uv run kgbuild -p hsa00010 > hsa00010.ttl
```

### Option 3: Install with pip

```bash
pip install .
```

Then run commands directly:

```bash
kgbuild -p hsa00010 > hsa00010.ttl
```

## Building knowledge graphs

To build a knowledge graph you only need to provide the option `-p` with a KEGG pathway entry corresponding to some organism. Entries are IDs made out of a three-letter organism code plus a 5 digit pathway code.

For instance, "hsa00010" is the entry for the **H**omo **sa**piens glycolysis/gluconeogenesis pathway. The knowledge graph is build with this command:

```bash
kgbuild -p hsa00010 > hsa00010.ttl
```

This fetches pathway topology (KGML), gene records, reaction equations, and compound metadata from the KEGG REST API, then assembles them into an RDF graph in Turtle ("ttl") format.

KEGG has webpages listing the [organism codes](https://www.genome.jp/kegg/tables/br08606.html) and [pathway codes](https://www.genome.jp/kegg/pathway.html) available. Not all organisms have all the possible pathways.

### Graph structure

The knowledge graph contains the following node types and relationships:

- **Gene** nodes with KEGG IDs, labels, UniProt cross-references, and KO/EC annotations
- **KO Term** nodes (KEGG Orthologs) linking genes to their functional roles
- **Reaction** nodes with directional equations, EC numbers, and substrate/product relationships
- **Compound** nodes with names and links to reactions

Genes are linked to reactions via `catalyzes` triples derived from KEGG's pathway topology (KGML), ensuring that only pathway-specific reactions are included.

Note that the substrates and products are simply defined by the script as the left-hand and right-hand compounds in the KEGG reaction equation.


## Visualization

Generate an interactive HTML visualization from a Turtle file:

```bash
visualize -i hsa00010.ttl -o hsa00010.html
```

The visualization shows a pathway-level network: KO (ortholog) nodes connected to reaction nodes, with compound nodes as substrates and products. Nodes are colored by type (KO, reaction, compound) and display metadata on hover.

### Pathway comparison

Provide two Turtle files to visualize their overlap. Shared nodes are colored differently from nodes unique to each organism:

```bash
visualize -i hsa00010.ttl sce00010.ttl -o hsa-sce-00010.html
```

This is useful for comparing how different organisms implement the same metabolic pathway, revealing which enzymatic steps are conserved and which are organism-specific.

