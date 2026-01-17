# How to Deploy JobScraper on DigitalOcean App Platform

DigitalOcean App Platform is much simpler than AWS. It will natively support the Docker setup we have prepared.

## Step-by-Step Instructions

1.  **Go to DigitalOcean App Platform**: [https://cloud.digitalocean.com/apps](https://cloud.digitalocean.com/apps)
2.  Click **Create App**.
3.  **Choose Source**:
    *   Select **GitHub**.
    *   Authorize if needed, then select your repository (`Submission`).
    *   Branch: `main`.
    *   **Source Directory**: Click "Edit" (pencil icon) and select `/JobScraper`. **(Crucial Step)**
    *   Click **Next**.
4.  **Resources**:
    *   It should detect **Docker** automatically because of the Dockerfile.
    *   HTTP Port: Ensure it says **3000** (Click Edit if it says 8080).
    *   Plan: "Basic" ($5/mo) is fine for testing.
    *   Click **Next**.
5.  **Environment Variables**:
    *   Click **Edit** next to Environment Variables.
    *   Add `YELLOWCAKE_API_KEY` = `your_key_here`
    *   Add `GROQ_API_KEY` = `your_key_here`
    *   Click **Save**, then **Next**.
6.  **Info**:
    *   Change the App Name if you want.
    *   Click **Create Resources**.

## Troubleshooting
- If the build fails, check the "Build Logs".
- If the URL gives a 404, make sure to add `/docs` to the end of the URL (e.g., `https://sea-lion-app-123.ondigitalocean.app/docs`).
