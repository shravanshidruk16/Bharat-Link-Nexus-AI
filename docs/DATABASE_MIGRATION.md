# BharatLink Nexus AI — Database Migration Guide (Supabase PostgreSQL to Cloud Firestore)

## 1. Overview
This document outlines the verified migration workflow from the production Supabase PostgreSQL cluster dump to Google Cloud Firestore (`bharatlink-nexus-ai`).

The migration preserves all **1,405 authentic records** across products, artisan seller profiles, buyer history, and taxonomy without data loss, truncation, or duplicate creation.

---

## 2. Source Backup File Inspection

* **Backup File**: `data/db_cluster-11-10-2026@02-10-44.backup` (6.75 MB)
* **Format**: Standard PostgreSQL plain-text cluster SQL dump (`pg_dumpall` stream).
* **Parser**: High-performance, pure-Python streaming `COPY ... FROM stdin` parser implemented in [`scripts/migrate_supabase_to_firestore.py`](file:///d:/BharatLink%20Nexus%20AI%20-%20Copy/scripts/migrate_supabase_to_firestore.py).
* **Dependency Requirement**: Zero external PostgreSQL binaries (`pg_restore` or `psql`) required.

---

## 3. Schema Transformation Mapping & Verified Record Counts

| PostgreSQL Source Table | Firestore Target Collection | Validated Record Count | Transformation & Integrity Rules |
| :--- | :--- | :--- | :--- |
| `public.profiles` | `users` | **53 records** | Maps `id` to document ID; sets verified `role`, email, and timestamps. |
| `public.seller_profiles` | `seller_profiles` | **47 records** | Preserves artisan business metadata, phone, WhatsApp number, and GI certification. |
| `public.seller_products` | `products` | **516 records** | Coerces numeric price, available stock, dimensions, weight, authenticity status, and image URLs. |
| `public.procurement_requests` | `procurement_requests` | **135 records** | Retains raw buyer requests, budget, quantity, and deadline parameters. |
| `public.procurement_results` | `orders` | **133 records** | Preserves fulfillment orders, shipping costs, delivery times, and carbon footprint. |
| `public.saved_recommendations` | `saved_recommendations` | **521 records** | Preserves user-curated procurement plans and bookmarks. |
| **Total Documents** | | **1,405 records** | 100% extracted and validated. |

---

## 4. Auxiliary Manifests (Identity & Storage)

* **Firebase Authentication (`data/firebase_auth_migration_manifest.json`)**:
  * Extracted from `auth.users` (5 accounts).
  * Contains emails, UUIDs, creation timestamps, and password hashes prepared for `firebase_admin.auth.import_users()`.
* **Storage Assets (`data/storage_migration_manifest.json`)**:
  * Extracted from `storage.objects` (5 objects).
  * Maps Supabase bucket file paths for migration to Google Cloud Storage (Firebase Storage).

---

## 5. Migration Execution

### Step 1: Dry-Run Mode (Validation & Safety Verification)
```bash
python scripts/migrate_supabase_to_firestore.py --dry-run
```
* Emits full reconciliation statistics without making any remote network calls or database writes.

### Step 2: Apply Migration to Live Cloud Firestore
```bash
python scripts/migrate_supabase_to_firestore.py --apply
```
* **Bounded Batches**: Writes in batches of 250 operations (within Firestore's 500-operation transaction ceiling).
* **Checkpoints**: Automatically tracks committed IDs in `data/migration_checkpoint.json`. If network is interrupted, re-running `--apply` resumes from the exact last uncommitted record.
* **Idempotence**: Uses `batch.set(doc_ref, doc, merge=True)` so running multiple times causes zero duplicate records or collisions.

---

## 6. Verification Checklist
1. Verify `products` collection contains 516 documents in Google Cloud Console / Firestore Studio.
2. Verify `seller_profiles` collection contains 47 documents.
3. Verify `/health/ready` probe returns `status: "ready"` and `firestore_connected: true`.
