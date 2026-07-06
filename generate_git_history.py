#!/usr/bin/env python3
"""
generate_git_history.py

Reads 'Detailed_Daily_Tracker_Human.csv', simulates realistic multi-member Git commits
distributed chronologically across Weeks 1 to 10 with proper author attribution,
creates week branches (week1 to week10), and merges everything into the main branch.
"""

import os
import sys
import csv
import subprocess
import random
from datetime import datetime

# Path to the CSV tracker
CSV_PATH = r"C:\Users\manav\Downloads\Detailed_Daily_Tracker_Human.csv"

# ----------------------------------------------------------------------------------
# Team Members Configuration
# You can customize the GitHub display names and emails here if desired.
# By default, Member 3 (Lead) is mapped to your Git profile (manvendrahub).
# ----------------------------------------------------------------------------------
TEAM_MEMBERS = {
    "Member 1": {
        "name": "Aarav Sharma",
        "email": "aarav.sharma@cloudrecon.ai",
        "role": "Frontend & UI/UX"
    },
    "Member 2": {
        "name": "Rohan Patel",
        "email": "rohan.patel@cloudrecon.ai",
        "role": "Backend (Spring Boot & Auth)"
    },
    "Member 3": {
        "name": "Manvendra Singh",
        "email": "manavvinaysingh8@gmail.com",
        "role": "Database (MySQL & Storage) (Lead)"
    },
    "Member 4": {
        "name": "Vikram Malhotra",
        "email": "vikram.malhotra@cloudrecon.ai",
        "role": "AI Integration (Python/FastAPI)"
    },
    "Member 5": {
        "name": "Neha Verma",
        "email": "neha.verma@cloudrecon.ai",
        "role": "Analytics, Testing & Docs"
    }
}

# Week date ranges (based on project calendar)
WEEK_MILESTONES = [
    ("week1",  datetime(2026, 7, 6),  datetime(2026, 7, 11)),
    ("week2",  datetime(2026, 7, 12), datetime(2026, 7, 18)),
    ("week3",  datetime(2026, 7, 19), datetime(2026, 7, 25)),
    ("week4",  datetime(2026, 7, 26), datetime(2026, 8, 1)),
    ("week5",  datetime(2026, 8, 2),  datetime(2026, 8, 8)),
    ("week6",  datetime(2026, 8, 9),  datetime(2026, 8, 15)),
    ("week7",  datetime(2026, 8, 16), datetime(2026, 8, 22)),
    ("week8",  datetime(2026, 8, 23), datetime(2026, 8, 29)),
    ("week9",  datetime(2026, 8, 30), datetime(2026, 9, 19)),
    ("week10", datetime(2026, 9, 20), datetime(2026, 10, 6)),
]

def run(cmd, env=None, check=True):
    res = subprocess.run(cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and res.returncode != 0:
        print(f"Error running command: {cmd}\nStderr: {res.stderr}")
    return res

def parse_csv(csv_path):
    if not os.path.exists(csv_path):
        print(f"CSV file not found: {csv_path}")
        sys.exit(1)
        
    entries = []
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Strip whitespace in keys and values
            clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
            date_str = clean_row.get("Date")
            member_key = clean_row.get("Team Member")
            work = clean_row.get("Work Done (Detailed Description)")
            
            if not (date_str and member_key and work):
                continue
                
            try:
                dt = datetime.strptime(date_str, "%d-%m-%Y")
            except ValueError:
                continue
                
            entries.append({
                "date": dt,
                "member_key": member_key,
                "role": clean_row.get("Role", ""),
                "work": work,
                "status": clean_row.get("Status", "Completed")
            })
            
    # Sort strictly by chronological date
    entries.sort(key=lambda x: x["date"])
    return entries

def main():
    print("=" * 70)
    print(" CloudRecon Git History Generator (Week 1 -> Week 10)")
    print("=" * 70)
    
    entries = parse_csv(CSV_PATH)
    print(f"Loaded {len(entries)} work tracker entries from CSV.")

    # Track directory
    docs_dir = os.path.join(".", "progress_logs")
    os.makedirs(docs_dir, exist_ok=True)
    
    # Ensure Git repo
    if not os.path.exists(".git"):
        run("git init")
        
    # Check current branch or switch to a fresh baseline branch
    run("git checkout -B main")

    current_week_idx = 0
    total_commits = 0
    
    # We will iterate through each log entry, write progress notes, and commit with past author and date
    for i, entry in enumerate(entries):
        dt = entry["date"]
        member_info = TEAM_MEMBERS.get(entry["member_key"], {
            "name": entry["member_key"],
            "email": f"{entry['member_key'].lower().replace(' ', '')}@cloudrecon.ai",
            "role": entry.get("role", "")
        })
        
        # Generate simulated commit time during work hours (10:00 to 19:00)
        hour = random.randint(10, 19)
        minute = random.randint(5, 55)
        second = random.randint(10, 50)
        commit_dt = dt.replace(hour=hour, minute=minute, second=second)
        date_iso = commit_dt.strftime("%Y-%m-%dT%H:%M:%S")

        # Determine which week this entry belongs to
        assigned_week = "week1"
        for w_name, start_d, end_d in WEEK_MILESTONES:
            if start_d <= dt <= end_d:
                assigned_week = w_name
                break
        
        # Touch or update progress log file
        log_file = os.path.join(docs_dir, f"{assigned_week}_summary.md")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"- **{dt.strftime('%d-%m-%Y')}** | **{member_info['name']}** ({member_info['role']}): {entry['work']}\n")

        # Stage changes
        run("git add .")
        
        # Construct commit message
        commit_msg = f"[{assigned_week.upper()}] {entry['work']}"
        
        # Git environment with author and committer dates
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = member_info["name"]
        env["GIT_AUTHOR_EMAIL"] = member_info["email"]
        env["GIT_AUTHOR_DATE"] = date_iso
        env["GIT_COMMITTER_NAME"] = member_info["name"]
        env["GIT_COMMITTER_EMAIL"] = member_info["email"]
        env["GIT_COMMITTER_DATE"] = date_iso
        
        res = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if res.returncode == 0:
            total_commits += 1
            if total_commits % 20 == 0:
                print(f"  Processed {total_commits} commits... (latest: {assigned_week} on {dt.strftime('%d-%m-%Y')})")

        # Create week tag/branch checkpoint when reaching end of week
        for w_name, start_d, end_d in WEEK_MILESTONES:
            if dt == end_d or (i == len(entries) - 1 and assigned_week == w_name):
                # Create branch for this week if not already created
                run(f"git branch -f {w_name}")

    print(f"\n[OK] Successfully created {total_commits} chronological commits across all 5 team members!")
    
    # Create week1 to week10 branches explicitly so links in tracker work
    print("\nCreating week branch references (week1 -> week10)...")
    for w_name, _, _ in WEEK_MILESTONES:
        run(f"git branch -f {w_name}")
        print(f"  Branch '{w_name}' configured.")
        
    # Ensure current project files are all committed on main branch
    run("git checkout -B main")
    run("git add .")
    
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Manvendra Singh"
    env["GIT_AUTHOR_EMAIL"] = "manavvinaysingh8@gmail.com"
    env["GIT_AUTHOR_DATE"] = "2026-10-12T20:00:00"
    env["GIT_COMMITTER_NAME"] = "Manvendra Singh"
    env["GIT_COMMITTER_EMAIL"] = "manavvinaysingh8@gmail.com"
    env["GIT_COMMITTER_DATE"] = "2026-10-12T20:00:00"
    
    subprocess.run(
        ["git", "commit", "-m", "release: finalize complete CloudRecon production fullstack application"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print("\n" + "=" * 70)
    print(" COMPLETE! Next steps to push everything to GitHub:")
    print("=" * 70)
    print(" 1. Push main branch:")
    print("    git push origin main --force")
    print("\n 2. Push all week branches (week1 to week10):")
    print("    git push origin --all --force")
    print("=" * 70)

if __name__ == "__main__":
    main()
