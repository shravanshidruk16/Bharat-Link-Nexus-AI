import re
import os

backup_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "db_cluster-11-10-2026@02-10-44.backup")
if not os.path.exists(backup_path):
    print("Backup file not found at:", backup_path)
    exit(1)

file_size_mb = os.path.getsize(backup_path) / (1024 * 1024)
print(f"Inspecting backup file: {backup_path} ({file_size_mb:.2f} MB)")

with open(backup_path, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# Scan for COPY statements
copy_pattern = re.compile(r'COPY\s+([a-zA-Z_0-9\.\"]+)\s*\(([^)]+)\)\s*FROM\s+stdin;', re.IGNORECASE)
matches = copy_pattern.findall(text)

print(f"\nFound {len(matches)} COPY statements:")
public_tables = []
auth_tables = []
storage_tables = []
other_tables = []

for table_name, cols_raw in matches:
    clean_table = table_name.strip().replace('"', '')
    col_names = [c.strip().replace('"', '') for c in cols_raw.split(',')]
    
    # Count rows in this COPY block
    # A COPY block ends with a line containing only "\."
    pattern_block = rf'COPY\s+{re.escape(table_name)}[^\n]*\n([\s\S]*?)\n\\\.'
    block_match = re.search(pattern_block, text)
    row_count = 0
    if block_match:
        lines = [l for l in block_match.group(1).split('\n') if l.strip()]
        row_count = len(lines)

    info = f"  - {clean_table}: {row_count} rows, {len(col_names)} columns"
    if clean_table.startswith("public."):
        public_tables.append(info)
    elif clean_table.startswith("auth."):
        auth_tables.append(info)
    elif clean_table.startswith("storage."):
        storage_tables.append(info)
    else:
        other_tables.append(info)

print("\n--- PUBLIC APPLICATION TABLES ---")
for t in public_tables:
    print(t)

print("\n--- AUTH TABLES (For Firebase Auth) ---")
for t in auth_tables:
    print(t)

print("\n--- STORAGE TABLES (For Cloud Storage) ---")
for t in storage_tables:
    print(t)
