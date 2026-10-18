# BharatLink Nexus AI — Firebase Setup & Local Emulator Guide

## 1. Firebase Architecture Overview
BharatLink Nexus AI utilizes **Firebase Authentication** and **Cloud Firestore** as its primary operational data store:
- **Firebase Authentication**: Provides secure, standards-compliant user identity for buyers, artisan sellers, and administrators.
- **Cloud Firestore**: High-performance NoSQL document database providing real-time synchronization, ACID transactions for inventory stock, and scalable indexing.
- **Firebase Admin SDK**: Server-side administrative SDK integrated directly into the FastAPI backend for token verification and transactional database operations.

---

## 2. Environment Variables Configuration

To connect the application to Firebase, set the following environment variables:

```bash
# Production / Cloud Mode
FIREBASE_PROJECT_ID=your-google-cloud-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json # Optional on Cloud Run (uses ADC)

# Local Development / Emulator Mode
FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
FIRESTORE_EMULATOR_HOST=localhost:8080
```

When deployed to **Google Cloud Run**, `firebase-admin` automatically discovers credentials using Google Cloud's **Application Default Credentials (ADC)** through the Cloud Run service identity. No JSON service account file is required in the container.

---

## 3. Running Firebase Emulator Locally

For offline testing and local development, the Firebase Emulator Suite allows you to emulate Authentication and Firestore without incurring cloud costs:

1. **Install Firebase CLI** (requires Node.js):
   ```bash
   npm install -g firebase-tools
   ```

2. **Initialize Firebase in the project directory**:
   ```bash
   firebase init emulators
   ```

3. **Start the Emulators**:
   ```bash
   firebase emulators:start --only auth,firestore
   ```

4. **Run the Application with Emulators**:
   Set `FIRESTORE_EMULATOR_HOST="127.0.0.1:8080"` and `FIREBASE_AUTH_EMULATOR_HOST="127.0.0.1:9099"`. The backend repository layer automatically detects these variables and routes queries to the local emulator instances.

---

## 4. In-Memory / File Fallback Mode
If the Firebase Emulator Suite is not installed on your machine, BharatLink Nexus AI includes a **built-in fail-safe in-memory/file repository engine** (`services/repository.py`). This allows developers to run tests, execute multi-agent procurement runs, test inventory updates, and explore Seller Central without needing cloud access or local emulators installed.

When real Firebase credentials or emulator hosts are detected, the platform seamlessly switches to live Firestore.
