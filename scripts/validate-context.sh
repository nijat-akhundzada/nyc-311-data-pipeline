#!/usr/bin/env bash
set -euo pipefail

required=(
  "AGENTS.md"
  "context/project-overview.md"
  "context/architecture.md"
  "context/code-standards.md"
  "context/ai-workflow-rules.md"
  "context/progress-tracker.md"
  "context/specs/00-build-plan.md"
)

failed=0
for file in "${required[@]}"; do
  if [[ ! -s "$file" ]]; then
    echo "Missing or empty: $file"
    failed=1
  fi
done

placeholder_report=$(mktemp)
trap 'rm -f "$placeholder_report"' EXIT

if rg -n '\[[A-Za-z][^]]*\]' "${required[@]}" >"$placeholder_report"; then
  echo "Unresolved placeholders found:"
  cat "$placeholder_report"
  failed=1
fi

if [[ "$failed" -ne 0 ]]; then
  echo "Context validation failed."
  exit 1
fi

echo "Context validation passed."
