Deploy rápido a Render

Sigue estos pasos para desplegar el backend en Render (puede usarse también en Heroku con Procfile):

1) Pre-requisitos
- Código en un repo GitHub (o GitLab)
- Cuenta en Render (https://render.com)

2) Archivos incluidos
- `requirements.txt` contiene dependencias (se añadió `gunicorn`)
- `Procfile` define el comando de inicio:
  ```
  web: gunicorn -k uvicorn.workers.UvicornWorker wsgi:app --bind 0.0.0.0:$PORT
  ```

3) Pasos para desplegar
- Push del repo a GitHub:
  ```bash
  git add requirements.txt Procfile README_RENDER.md
  git commit -m "Prepare backend for Render: gunicorn + Procfile"
  git push origin main
  ```
- En Render: New -> Web Service -> Connect GitHub repo
- Build Command: (Render usa `pip install -r requirements.txt` por defecto)
- Start Command: deja el campo vacío si tienes `Procfile`, o usa explícito:
  ```bash
  gunicorn -k uvicorn.workers.UvicornWorker wsgi:app --bind 0.0.0.0:$PORT
  ```
- En Environment → añade variable(s) de entorno:
  - `ALLOWED_ORIGINS` = `https://<tu-frontend>.vercel.app` (o lista separada por comas)
  - Opcional: otras variables como `DATABASE_URL` si usas DB remota

4) Configurar frontend en Vercel
- En Vercel Project -> Settings -> Environment Variables añade:
  - `VITE_API_URL` = `https://<tu-backend>.onrender.com`
- Redeploy del frontend

5) Comprobaciones finales
- API docs: `https://<tu-backend>.onrender.com/docs`
- Frontend: `https://<tu-frontend>.vercel.app`
- Revisa consola del navegador para errores CORS (si aparecen, añade origen a `ALLOWED_ORIGINS`)

Si quieres, puedo encargarte del deploy desde aquí, pero necesitaré acceso a tu cuenta GitHub y a Render (o un token de deploy). Alternativamente, haz el push y dame la URL del repo: yo puedo generar el archivo `render.yaml` y los pasos exactos para que Render lo conecte automáticamente.
