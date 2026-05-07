#!/usr/bin/env bash
# verify-alignment — Evaluate an output against the alignment spec using RLM.
#
# Usage:
#   verify-alignment --file output.md
#   verify-alignment --stdin < output.md
#   echo "some text" | verify-alignment --stdin
#   verify-alignment --file src --url https://example.com/context "optional extra instruction"
#
# The alignment spec is resolved from:
#   1. $ALIGNMENT_SPEC environment variable (if set)
#   2. workspaces/alignment/artifacts/alignment_spec.md
#
# Requires: rlm binary in PATH

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments. Keep native rlm behavior: context flags may be combined and
# repeated, while this wrapper only fixes the judgment style and evaluation query.
RLM_ARGS=()
POSITIONAL_QUERY=()
HAS_CONTEXT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --file|--url|--text|--model|--sub-model|--provider)
            if [[ -z "${2:-}" ]]; then
                echo "Error: $1 requires an argument" >&2
                exit 1
            fi
            RLM_ARGS+=("$1" "$2")
            case "$1" in
                --file|--url|--text)
                    HAS_CONTEXT=true
                    ;;
            esac
            shift 2
            ;;
        --stdin)
            RLM_ARGS+=("--stdin")
            HAS_CONTEXT=true
            shift
            ;;
        --verbose)
            RLM_ARGS+=("--verbose")
            shift
            ;;
        --judgment-style)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --judgment-style requires an argument" >&2
                exit 1
            fi
            echo "Error: verify-alignment always uses --judgment-style compass" >&2
            exit 1
            ;;
        --help|-h)
            cat <<'EOF'
verify-alignment — Check output alignment against user values and process standards.

Usage:
  verify-alignment --file output.md
  verify-alignment --stdin < output.md
  verify-alignment --file src --url https://example.com/context
  verify-alignment --text "draft text"

Options:
  --file PATH       Load a file, directory, or glob as artifact/context
  --url URL         Load a URL as artifact/context
  --text TEXT       Add inline artifact/context text
  --stdin           Read artifact/context from stdin
  --model ID        Override the configured root model
  --sub-model ID    Override the configured sub-query model
  --provider NAME   Override the configured provider
  --verbose         Print progress events to stderr
  --help            Show this help

Notes:
  Context flags match native rlm behavior: --file, --url, and --text may be
  repeated, and --stdin may be combined with them. verify-alignment always runs
  rlm with --judgment-style compass.

Output:
  VERDICT: SHIP | TIGHTEN | REWORK
  DECISION MAP with per-decision alignment scores
  TIGHTEN INSTRUCTIONS or REWORK REASON as applicable

Environment:
  ALIGNMENT_SPEC    Override path to the alignment spec file
EOF
            exit 0
            ;;
        --)
            shift
            POSITIONAL_QUERY+=("$@")
            break
            ;;
        -*)
            echo "Error: Unknown argument: $1" >&2
            exit 1
            ;;
        *)
            POSITIONAL_QUERY+=("$1")
            shift
            ;;
    esac
done

# Validate we have something to evaluate
if [[ "$HAS_CONTEXT" == "false" ]]; then
    echo "Error: Provide --file, --url, --text, or --stdin to specify what to evaluate" >&2
    exit 1
fi

# Resolve alignment spec path
if [[ -n "${ALIGNMENT_SPEC:-}" ]]; then
    SPEC_PATH="$ALIGNMENT_SPEC"
elif [[ -f "$SCRIPT_DIR/../workspaces/alignment/artifacts/alignment_spec.md" ]]; then
    SPEC_PATH="$SCRIPT_DIR/../workspaces/alignment/artifacts/alignment_spec.md"
else
    echo "Error: Alignment spec not found." >&2
    echo "Run 'python -m core build-alignment-spec' first, or set ALIGNMENT_SPEC." >&2
    exit 1
fi

# Verify spec exists
if [[ ! -f "$SPEC_PATH" ]]; then
    echo "Error: Alignment spec not found at $SPEC_PATH" >&2
    exit 1
fi

# Verify rlm is available
if ! command -v rlm &>/dev/null; then
    echo "Error: rlm binary not found in PATH" >&2
    exit 1
fi

# Build the RLM command
RLM_CMD=(rlm --judgment-style compass)
RLM_CMD+=("${RLM_ARGS[@]}")

# The evaluation query: pass the rubric as prompt text, not as a second file-backed source.
SPEC_TEXT="$(<"$SPEC_PATH")"
QUERY=$(cat <<EOF
Use the following alignment verification spec as the rubric for this evaluation:

$SPEC_TEXT

First, build an explicit Compass knowledge map for the provided output.

Use the Compass directions this way:
- North: origin, framing, context, and what the artifact is trying to do
- West: adjacent patterns, supporting structure, and what in the artifact coheres with the spec
- East: contradictions, omissions, weak spots, and boundary conditions relative to the spec
- South: downstream implications, operator effect, and what this would lead to if shipped as-is

Make the implicit structure explicit. Store a complete Compass map before rendering the final answer.

Then evaluate the provided output against the alignment spec using that verified Compass map as the basis for judgment. Follow the evaluation procedure exactly and return the required structured result.
EOF
)

if [[ ${#POSITIONAL_QUERY[@]} -gt 0 ]]; then
    QUERY+=$'\n\nAdditional user instruction:\n'
    QUERY+="${POSITIONAL_QUERY[*]}"
fi

RLM_CMD+=("$QUERY")

# Execute
exec "${RLM_CMD[@]}"
