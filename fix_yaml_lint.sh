#!/bin/bash
# Fix trailing spaces
find . -type f \( -name "*.yml" -o -name "*.yaml" \) -not -path "./node_modules/*" -not -path "./.terraform/*" -exec sed -i 's/[[:space:]]*$//' {} +

# Ensure newline at EOF
find . -type f \( -name "*.yml" -o -name "*.yaml" \) -not -path "./node_modules/*" -not -path "./.terraform/*" -exec sh -c 'tail -c1 "{}" | read -r _ || echo >> "{}"' \;
