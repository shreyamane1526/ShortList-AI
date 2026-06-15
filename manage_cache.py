"""
manage_cache.py  — Cache management tool

Works on Windows, Linux, and Mac.
Avoids shell quote issues by running Python directly.

Usage:
    python manage_cache.py list              # show all cached candidates
    python manage_cache.py clear            # delete ALL cached entries
    python manage_cache.py delete torvalds  # delete one specific candidate
    python manage_cache.py show torvalds    # print full cached profile
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from core.database import engine, init_db
from sqlmodel import Session, select, text
from core.database import CandidateCache

init_db()

def cmd_list():
    with Session(engine) as s:
        records = s.exec(select(CandidateCache)).all()
    if not records:
        print("Cache is empty.")
        return
    print(f"{'candidate_id':<40} {'collected_at':<28} {'expires_at'}")
    print("-" * 100)
    for r in records:
        print(f"{r.candidate_id:<40} {str(r.collected_at):<28} {r.ttl_expires_at}")
    print(f"\nTotal: {len(records)} cached profile(s)")

def cmd_clear():
    with Session(engine) as s:
        records = s.exec(select(CandidateCache)).all()
        count = len(records)
        for r in records:
            s.delete(r)
        s.commit()
    print(f"Deleted {count} cached profile(s).")

def cmd_delete(candidate_id: str):
    with Session(engine) as s:
        records = s.exec(
            select(CandidateCache).where(
                CandidateCache.candidate_id.startswith(candidate_id)
            )
        ).all()
        if not records:
            print(f"No cached profiles found matching '{candidate_id}'")
            return
        for r in records:
            print(f"  Deleting: {r.candidate_id}")
            s.delete(r)
        s.commit()
    print(f"Done. Deleted {len(records)} entry/entries.")

def cmd_show(candidate_id: str):
    with Session(engine) as s:
        records = s.exec(
            select(CandidateCache).where(
                CandidateCache.candidate_id.startswith(candidate_id)
            )
        ).all()
    if not records:
        print(f"No cached profiles found matching '{candidate_id}'")
        return
    for r in records:
        profile = json.loads(r.profile_json)
        print(f"\n=== {r.candidate_id} ===")
        print(f"Collected : {r.collected_at}")
        print(f"Expires   : {r.ttl_expires_at}")
        print(f"Sources   : {profile.get('sources_used')}")
        print(f"Skills    : {[s['name'] for s in profile.get('skills', [])]}")
        print(f"Trust     : {profile.get('integrity', {}).get('trust_score')}/100")
        signals = profile.get('signals', {})
        print(f"Commits   : {signals.get('commit_consistency')}")
        print(f"Complexity: {signals.get('project_complexity')}")
        print(f"Domains   : {signals.get('domain_breadth')}")
        print(f"LeetCode  : {signals.get('leetcode_solved')} solved")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "clear":
        cmd_clear()
    elif args[0] == "delete" and len(args) >= 2:
        cmd_delete(args[1])
    elif args[0] == "show" and len(args) >= 2:
        cmd_show(args[1])
    else:
        print(__doc__)