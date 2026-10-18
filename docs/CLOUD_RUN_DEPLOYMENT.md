# BharatLink Nexus AI — Google Cloud Run Deployment Guide

## 1. Overview & Cloud Run Suitability

BharatLink Nexus AI is optimized for **Google Cloud Run**, Google Cloud's fully managed serverless compute platform.

### Key Deployment Characteristics:
- **Unified Single-Container Architecture**: FastAPI serves both the REST API, Server-Side Rendered (SSR) Jinja2 templates, and optimized static assets (`/static`), removing the need for a separate Node.js server.
- **Dynamic Port Binding**: Conforms to Cloud Run's requirement by binding to `0.0.0.0` and listening on the container `$PORT` environment variable (default 8080).
- **Stateless & Resilient**: Relies entirely on Cloud Firestore and Vertex AI / Gemini API. The container requires no local persistent disk or local `.env` files.
- **Health Probes**: Implements `/health` (liveness) and `/health/ready` (readiness) probes for Cloud Run health checking.

---

## 2. Dockerfile & Container Architecture

The production `Dockerfile` is built with Python 3.10-slim:
- Minimal attack surface and fast startup time (< 3 seconds).
- Installs only production dependencies from `requirements.txt`.
- Non-root application user for container security.
- Production ASGI server configuration (`uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2`).

```dockerfile
FROM python:3.10-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 2
```

---

## 3. GitHub Repository to Cloud Run Deployment Workflow

Follow these steps in the Google Cloud Console to deploy directly from your GitHub repository:

1. **Push your code to your GitHub repository**:
   ```bash
   git init
   git add .
   git commit -m "feat: BharatLink Nexus AI Google AI Builder Cup Edition"
   git remote add origin https://github.com/<your-username>/bharatlink-nexus-ai.git
   git push -u origin main
   ```

2. **Open Google Cloud Console**:
   - Navigate to **Cloud Run** (`https://console.cloud.google.com/run`).
   - Click **Create Service**.

3. **Select "Continuously deploy from a repository"**:
   - Click **Set up with Cloud Build**.
   - Select provider: **GitHub**.
   - Select your repository: `<your-username>/bharatlink-nexus-ai`.
   - Branch: `^main$`.
   - Build Type: **Dockerfile** (Path: `/Dockerfile`).

4. **Configure Service Settings**:
   - Service name: `bharatlink-nexus-ai`.
   - Region: `us-central1` (or your preferred region).
   - CPU allocation: **CPU is only allocated during request processing**.
   - Autoscaling: Minimum 0 instances, Maximum 5 instances.
   - Authentication: **Allow unauthenticated invocations** (for public web access).
   - In **Container, Networking, Security**:
     - Container port: `8080`.
     - Memory: `1 GiB` or `2 GiB`.
     - CPU: `1 vCPU`.

5. **Supply Environment Variables & Secrets**:
   Under **Variables & Secrets**, add:
   - `GEMINI_API_KEY`: Referenced from Google Secret Manager or entered as an environment variable.
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `AI_PROVIDER`: `gemini`
   - `FIREBASE_PROJECT_ID`: Your Google Cloud / Firebase Project ID.
   - `ENVIRONMENT`: `production`

6. **Deploy**:
   Click **Create**. Cloud Build will build the container image, push it to Artifact Registry, and Cloud Run will deploy the service. You will receive a secure HTTPS URL (e.g. `https://bharatlink-nexus-ai-xyz-uc.a.run.app`).
