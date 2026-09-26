# Nix Packaging And Distribution

The flake exposes generated artifacts under `lib.artifacts` and a default
development shell. The shell contains Python 3.12 with the project client
libraries, `ai-data-extractor`, and QMD.

QMD comes from the `github:numtide/llm-agents.nix` input. The flake imports the
shared overlay and packages `pkgs.llm-agents.qmd` with Vulkan and CUDA disabled
for portable development shells.

The flake has no RLM input, schema flake input, `substrate-cli`, or
`verify-alignment` package.
