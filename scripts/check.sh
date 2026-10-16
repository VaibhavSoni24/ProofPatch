#!/usr/bin/env bash
set -e

echo "Running ProofPatch test and quality checks..."

source .venv/bin/activate
pytest backend/tests -v

cd frontend
npm test -- --run
npm run build
cd ..

echo "All ProofPatch checks passed successfully!"
