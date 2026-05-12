# Deploy Dash App on Render

## Why GitHub Pages shows no data
GitHub Pages is static hosting. Your app is Dash (Python server), so it must run on a Python host (Render).

## Files added
- render.yaml
- .env.example

## 1. Ensure data is available at runtime
Your app expects a folder containing:
- LaLiga/
- Copa del Rey/
- UEFA Champions League/

Use one of these options:
1. Commit these data folders into this repository root.
2. Mount a Render Disk and copy data there, then set DATA_ROOT to that mount path.

## 2. Push repository
From this folder:

```bash
cd "/Users/sudhirdahiya/Downloads/FINAL_MASTER_PROJECT(REALMADRID)/dashboard"
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

## 3. Create service in Render
1. Open Render Dashboard -> New -> Blueprint
2. Select this GitHub repository
3. Render will detect `render.yaml`
4. Deploy

## 4. Set environment variable (if needed)
In Render service settings -> Environment:
- DATA_ROOT = path containing competition folders

Default in `render.yaml` is:
- `/opt/render/project/src`

This works if your competition folders are committed at repository root.

## 5. Verify
After deploy, open Render URL and check:
- Competition dropdown has 3 options
- Seasons load
- Match dropdown has entries
- KPIs/charts populate

## Optional: keep GitHub Pages as landing page
Use GitHub Pages only as a static landing page with a button linking to your Render URL.
