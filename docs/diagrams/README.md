# Architecture diagram sources

## Shared-runtime preview with Python Diagrams

The system and request flow views use [mingrammer/diagrams](https://github.com/mingrammer/diagrams), with explanatory component cards and colored paths. Read [Architecture, explained](../architecture-diagrams.md) for the walkthrough.

| Source | Rendered SVG | Rendered PNG |
|---|---|---|
| `architecture.py` (system view) | [System](../assets/architecture-system.svg) | [System](../assets/architecture-system.png) |
| `architecture.py` (request flows) | [Flows](../assets/architecture-flows.svg) | [Flows](../assets/architecture-flows.png) |

Install Graphviz (`brew install graphviz` on macOS), then render from the repository root:

```sh
python3 -m venv /tmp/mms-diagrams
/tmp/mms-diagrams/bin/python -m pip install -r docs/diagrams/requirements.txt
/tmp/mms-diagrams/bin/python docs/diagrams/architecture.py
```

These are documentation dependencies only; the memory-engine runtime does not depend on Diagrams or Graphviz. The script resolves output paths relative to itself, so it also works from another directory. Use `--output-dir PATH` for alternate renders.

For environments without native Graphviz, emit standard DOT sources:

```sh
/tmp/mms-diagrams/bin/python docs/diagrams/architecture.py --dot-only --output-dir /tmp/mms-architecture-dot
```

Render the resulting `.gv` files with a compatible Graphviz renderer. The checked-in views were rendered through the bundled `@viz-js/viz` Graphviz WebAssembly build and rasterized to 2,400-pixel-wide PNGs. Native Graphviz may produce small spacing differences. Nodes are text cards with no external image assets, so SVGs are self-contained. Review both images after changes for clipped text, crossings, contrast and architectural accuracy.
