#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(realpath "${script_dir}/../..")"
output_dir="${repo_root}/Operational-Layer/data"
extractor_target="${1:-all}"

case "${extractor_target}" in
  all|claude-code|codex|continue|cursor|gemini|opencode|trae|windsurf)
    ;;
  list|help)
    exec nix run "${repo_root}#ai-data-extraction" -- "${extractor_target}"
    ;;
  *)
    printf 'Usage: %s <extractor|all|list|help>\n' "$(basename "$0")" >&2
    printf 'Supported extractors: claude-code codex continue cursor gemini opencode trae windsurf\n' >&2
    exit 1
    ;;
esac

mkdir -p "${output_dir}"
temp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "${temp_dir}"
}
trap cleanup EXIT

printf 'Running extractor %s...\n' "${extractor_target}"
(
  cd "${temp_dir}"
  nix run "${repo_root}#ai-data-extraction" -- "${extractor_target}"
)

shopt -s nullglob
jsonl_files=("${temp_dir}"/extracted_data/*.jsonl)

if [ "${#jsonl_files[@]}" -eq 0 ]; then
  printf 'No JSONL files were produced by ai-data-extraction.\n' >&2
  exit 1
fi

cp "${jsonl_files[@]}" "${output_dir}/"
printf 'Copied %s file(s) into %s\n' "${#jsonl_files[@]}" "${output_dir}"
