#!/usr/bin/env bash
# verify-alignment — Evaluate an output against the alignment spec using RLM.
#
# Usage:
#   verify-alignment --file output.md
#   verify-alignment --stdin < output.md
#   echo "some text" | verify-alignment --stdin
#
# The alignment spec is resolved from:
#   1. $ALIGNMENT_SPEC environment variable (if set)
#   2. The co-located artifacts/alignment_spec.md (relative to this script)
#
# Requires: rlm binary in PATH

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve alignment spec path
if [[ -n "${ALIGNMENT_SPEC:-}" ]]; then
    SPEC_PATH="$ALIGNMENT_SPEC"
elif [[ -f "$SCRIPT_DIR/artifacts/alignment_spec.md" ]]; then
    SPEC_PATH="$SCRIPT_DIR/artifacts/alignment_spec.md"
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

# Parse arguments
INPUT_FILE=""
USE_STDIN=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --file)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --file requires a path argument" >&2
                exit 1
            fi
            if [[ -n "$INPUT_FILE" ]]; then
                echo "Error: verify-alignment accepts only one --file input" >&2
                exit 1
            fi
            INPUT_FILE="$2"
            shift 2
            ;;
        --stdin)
            if [[ -n "$INPUT_FILE" ]]; then
                echo "Error: Use either --file or --stdin, not both" >&2
                exit 1
            fi
            USE_STDIN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            cat <<'EOF'
verify-alignment — Check output alignment against user values and process standards.

Usage:
  verify-alignment --file output.md
  verify-alignment --stdin < output.md

Options:
  --file PATH    File to evaluate
  --stdin        Read output to evaluate from stdin
  --verbose      Print progress to stderr
  --help         Show this help

Output:
  VERDICT: SHIP | TIGHTEN | REWORK
  DECISION MAP with per-decision alignment scores
  TIGHTEN INSTRUCTIONS or REWORK REASON as applicable

Environment:
  ALIGNMENT_SPEC    Override path to the alignment spec file
EOF
            exit 0
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# Validate we have something to evaluate
if [[ -z "$INPUT_FILE" ]] && [[ "$USE_STDIN" == "false" ]]; then
    echo "Error: Provide --file or --stdin to specify what to evaluate" >&2
    exit 1
fi

if [[ -n "$INPUT_FILE" ]] && [[ "$USE_STDIN" == "true" ]]; then
    echo "Error: Use either --file or --stdin, not both" >&2
    exit 1
fi

# Build the RLM command
RLM_CMD=(rlm)

# Add the user-provided file as the evaluation target context
if [[ -n "$INPUT_FILE" ]]; then
    RLM_CMD+=("--file" "$INPUT_FILE")
fi

# Add stdin flag if needed
if [[ "$USE_STDIN" == "true" ]]; then
    RLM_CMD+=("--stdin")
fi

# Add verbose flag if needed
if [[ "$VERBOSE" == "true" ]]; then
    RLM_CMD+=("--verbose")
fi

# The evaluation query: pass the rubric as prompt text, not as a second file-backed source.
SPEC_TEXT="$(<"$SPEC_PATH")"
QUERY=$(cat <<EOF
Use the following alignment verification spec as the rubric for this evaluation:

$SPEC_TEXT

Evaluate the provided output against that spec. Follow the evaluation procedure exactly and return the required structured result.
EOF
)

RLM_CMD+=("$QUERY")

# Execute
exec "${RLM_CMD[@]}"
