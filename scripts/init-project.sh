#!/usr/bin/env bash
set -euo pipefail

project_name="${1:-}"
if [[ -z "$project_name" ]]; then
  echo "Usage: ./scripts/init-project.sh \"Project Name\""
  exit 1
fi

files=(
  AGENTS.md
  context/project-overview.md
  context/architecture.md
  context/code-standards.md
  context/ai-workflow-rules.md
  context/progress-tracker.md
  context/ui-context.md
  context/specs/00-build-plan.md
)

escaped_name=${project_name//&/\\&}
for file in "${files[@]}"; do
  sed -i.bak "s/\[Project Name\]/$escaped_name/g" "$file"
  rm "$file.bak"
done

echo "Initialized context for: $project_name"
echo "Next: complete the context files, then run ./scripts/validate-context.sh"
