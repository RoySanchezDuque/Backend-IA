#!/usr/bin/env bash
set -e

# Branch with deployment-ready changes
git checkout -b render/deploy-ready

git add requirements.txt Procfile README_RENDER.md render.yaml
git commit -m "chore(deploy): prepare render deployment (gunicorn, Procfile, render.yaml)"

echo "Branch 'render/deploy-ready' created and committed."

echo "Next steps:" 
echo "1) Push branch to GitHub: git push origin render/deploy-ready"
echo "2) In Render dashboard: New -> Web Service -> Connect GitHub repo -> Import from repo"
echo "   When Render prompts, choose 'Import Existing Render.yaml' to create the service from render.yaml"

echo "3) In Render service settings add environment variable ALLOWED_ORIGINS with your Vercel domain(s)."

echo "4) In Vercel dashboard add VITE_API_URL pointing to the Render service URL and redeploy the frontend."
