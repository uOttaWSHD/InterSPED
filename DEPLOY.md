# Deploying to DigitalOcean App Platform

This project is structured as a Monorepo with a Next.js Frontend and a FastAPI Backend. 

## 1. Environment Variables Strategy
Since you are using a comma-separated key rotation system, you must define these in the DigitalOcean Control Panel under **Settings > Environment Variables**.

### Required Variables:
- `ELEVENLABS_API_KEY`: `key1,key2,key3`
- `LLM_API_KEY`: `key1,key2,key3`
- `YELLOWCAKE_API_KEY`: `key1,key2`
- `NEXT_PUBLIC_API_URL`: The URL of your backend component (e.g., `https://api-xyz.ondigitalocean.app`)

## 2. App Spec Configuration
When creating the app, use the following directory mapping:

### Backend Component:
- **Source Directory**: `/Backend`
- **Build Command**: `pip install -r requirements.txt`
- **Run Command**: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`
- **HTTP Port**: `8000` (or `${PORT}`)

### Frontend Component:
- **Source Directory**: `/Frontend`
- **Build Command**: `npm run build`
- **Run Command**: `npm start`
- **HTTP Port**: `3000`

## 3. Handling Shared .env
On DigitalOcean, you **do not need a .env file**.
- **Local Development**: We use a symlink (`Frontend/.env.local` -> `../.env`).
- **Production**: DigitalOcean injects environment variables directly into the process. The code is already updated to read `os.environ` directly, so it will "just work" without the `.env` file present in the container.

## 4. Key Rotation
If a key is revoked or hits a rate limit:
1. Go to the DigitalOcean App Dashboard.
2. Edit the environment variable.
3. Remove the bad key from the comma-separated list.
4. DigitalOcean will automatically redeploy the app with the updated list.
5. The backend's new retry logic will automatically skip failed keys and cycle to the next valid one.
