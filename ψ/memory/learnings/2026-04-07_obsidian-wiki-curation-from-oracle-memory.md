---
title: Obsidian Wiki Curation from Oracle Memory
tags: [obsidian, wiki, oracle-memory, knowledge-management, df-obsidian]
created: 2026-04-07
source: retrospective: artemis-oracle
project: github.com/bjgdr/artemis-oracle
---
# Obsidian Wiki Curation from Oracle Memory

## The Mapping Pattern
The ψ/ brain structure maps cleanly to an Obsidian wiki:
- Resonance files → overview.md
- Retrospectives → wiki/sources/ (with session context)
- Learnings → wiki/concepts/ (reusable patterns)
- Shared memory → cross-entity references
- Family/siblings → wiki/entities/

## Workflow
1. Read all source material (resonance, retros, learnings)
2. Spawn 3 agents in parallel for speed (sources batch 1, sources batch 2, entities+concepts)
3. Each agent writes files directly to the vault path
4. Lint pass checks cross-refs and identifies missing pages

## Key Technical Notes
- Windows vault via WSL2: `/mnt/c/MyDoc/OPVAULT/FIEZ/`
- index.md works as primary navigation at ~100 sources without needing RAG
- Obsidian `[[wikilinks]]` for cross-referencing
- YAML frontmatter for Dataview plugin queries
- kebab-case for all filenames

## Scale Observations
- 10 sources curated → 39 total pages (entities and concepts expand from sources)
- Each source touches 5-10 related pages (cross-pollination)
- Log.md uses parseable prefixes: `## [YYYY-MM-DD] operation | Title`
