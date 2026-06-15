import json
import sqlite3

# Connect to the database
conn = sqlite3.connect('evidence_agent.db')
cursor = conn.cursor()

# Get all cached profiles
cursor.execute('SELECT candidate_id, profile_json, collected_at, ttl_expires_at FROM candidatecache')
records = cursor.fetchall()

print("=" * 100)
print(f"TOTAL CACHED PROFILES: {len(records)}")
print("=" * 100)

for i, (candidate_id, profile_json, collected_at, expires_at) in enumerate(records, 1):
    print(f"\n{'='*100}")
    print(f"PROFILE #{i}: {candidate_id}")
    print(f"{'='*100}")
    print(f"Collected: {collected_at}")
    print(f"Expires:   {expires_at}")
    print(f"\nDATA:")
    print("-" * 100)
    
    profile = json.loads(profile_json)
    print(json.dumps(profile, indent=2))

conn.close()