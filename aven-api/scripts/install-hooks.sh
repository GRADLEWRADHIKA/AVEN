#!/bin/sh
# Installs a git pre-commit hook that blocks commits containing patient-data-looking files or secrets.
set -e
cd "$(git rev-parse --show-toplevel)"
cat > .git/hooks/pre-commit <<'EOF'
#!/bin/sh
python3 scripts/check_no_phi.py --staged
EOF
chmod +x .git/hooks/pre-commit
echo "Installed pre-commit hook."
