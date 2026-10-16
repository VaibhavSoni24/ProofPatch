#!/usr/bin/env bash
set -e

echo "Setting up ProofPatch environment..."
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -e backend

cd frontend
npm install
cd ..

echo "Setup complete! Run ./scripts/check.sh to verify."
