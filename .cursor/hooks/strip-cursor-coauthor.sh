#!/bin/bash
# Fail closed on git commit/push that would publish Cursor co-author attribution.
input=$(cat)
command=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("command",""))' 2>/dev/null || true)
if printf '%s' "$command" | grep -Eqi 'git[[:space:]]+commit|git[[:space:]]+push'; then
  if printf '%s' "$command" | grep -Eqi 'cursoragent@cursor\.com|Co-authored-by:[[:space:]]*Cursor'; then
    echo '{
      "permission": "deny",
      "user_message": "Blocked: commit message still contains Cursor co-author. The .githooks/prepare-commit-msg hook should strip it — rewrite the message without Co-authored-by: Cursor.",
      "agent_message": "Remove Co-authored-by: Cursor / cursoragent@cursor.com from the commit message, then retry."
    }'
    exit 0
  fi
fi
echo '{ "permission": "allow" }'
exit 0
