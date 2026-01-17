# How to Deploy JobScraper

This application is a **Python Backend** that uses **Playwright** (requires Chrome/Browsers).
It **CANNOT** be deployed on **AWS Amplify Hosting** (which is for static websites like React/Vue).
Using Amplify Hosting will result in a **404 Error**.

## ✅ The Solution: AWS App Runner

AWS App Runner is the correct service for this. It connects to this repo just like Amplify but runs the Docker container.

### Step-by-Step Instructions

1.  **Go to AWS App Runner Console**: [https://console.aws.amazon.com/apprunner](https://console.aws.amazon.com/apprunner)
2.  Click **Create Service**.
3.  **Source & Deployment**:
    *   **Repository Type**: Source code repository.
    *   **Provider**: GitHub.
    *   **Repository**: Select this repository (`Submission`).
    *   **Branch**: `main`.
    *   **Deployment Trigger**: Automatic.
4.  **Build Settings**:
    *   **Configuration**: Select **"Configure all settings here"**.
    *   **Source Directory**: `/JobScraper` (or browse to select the JobScraper folder).
    *   **Runtime**: **Docker** (Do NOT select Python).
    *   **Dockerfile location**: `Dockerfile` (It should default to this).
    *   **Build command**: (Leave empty).
    *   **Start command**: (Leave empty).
    *   **Port**: `3000`.
5.  **Service Configuration**:
    *   **Service Name**: `jobscraper-api`.
    *   **Environment Variables** (Add these):
        *   `YELLOWCAKE_API_KEY`: `your_key_here`
        *   `GROQ_API_KEY`: `your_key_here`
6.  **Review & Create**.

### Why this is necessary
This application scrapes websites using a real browser (Chromium). This requires a complex system environment that standard web hosting (Amplify) does not provide. Docker packages that entire environment for you.
