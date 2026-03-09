import json
import os
import sys
from datetime import datetime
from pathlib import Path

MEMORY_DIR  = Path.home() / ".jobby"
MEMORY_FILE = MEMORY_DIR / "memory.json"

DEFAULT = {
    "profile": {
        "name": "Garry Singh",
        "title": "Senior Site Reliability Engineer",
        "location": "Austin, TX",
        "email": "networkgarry@gmail.com",
        "skills": ["GCP","AWS","Kubernetes","Terraform","Python","SRE","Observability","Messaging"],
        "target_roles": ["SRE","Staff SRE","Platform Engineer","DevOps Engineer","Solutions Architect","Customer Engineer","Pre-Sales Engineer"],
        "target_salary_min": 175000,
        "notes": ""
    },
    "searches": [],
    "jobs": {},
    "shortlist": [],
    "applied": [],
    "rejected": [],
    "last_run": None,
    "stats": {"total_searches": 0, "total_jobs_found": 0, "total_applied": 0}
}

def load():
    MEMORY_DIR.mkdir(exist_ok=True)
    if not MEMORY_FILE.exists():
        save(DEFAULT)
        return json.loads(json.dumps(DEFAULT))
    with open(MEMORY_FILE) as f:
        return json.load(f)

def save(data):
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def reset():
    save(json.loads(json.dumps(DEFAULT)))
    print("🧹 Memory wiped")

def save_search_run(jobs, queries_run=0):
    m = load()
    run = {
        "timestamp":   datetime.now().isoformat(),
        "queries_run": queries_run,
        "jobs_found":  len(jobs),
        "job_links":   [j["link"] for j in jobs]
    }
    m["searches"].append(run)
    m["last_run"] = run["timestamp"]
    m["stats"]["total_searches"]   += 1
    m["stats"]["total_jobs_found"] += len(jobs)
    for job in jobs:
        link = job["link"]
        if link not in m["jobs"]:
            m["jobs"][link] = job
        else:
            m["jobs"][link]["scraped_at"] = job["scraped_at"]
    save(m)
    print(f"💾 Memory: saved {len(jobs)} jobs ({len(m['jobs'])} total stored)")

def get_last_run_jobs():
    m = load()
    if not m["searches"]: return []
    return [m["jobs"][l] for l in m["searches"][-1]["job_links"] if l in m["jobs"]]

def get_all_jobs(status=None):
    m = load()
    jobs = list(m["jobs"].values())
    return [j for j in jobs if j.get("status") == status] if status else jobs

def update_job_status(link, status):
    m = load()
    if link not in m["jobs"]:
        print(f"❌ Not found: {link}"); return
    m["jobs"][link]["status"] = status
    m["jobs"][link]["status_updated"] = datetime.now().isoformat()
    if status == "shortlisted" and link not in m["shortlist"]:
        m["shortlist"].append(link)
    elif status == "applied":
        if link not in m["applied"]: m["applied"].append(link)
        m["stats"]["total_applied"] += 1
    elif status == "rejected" and link not in m["rejected"]:
        m["rejected"].append(link)
    save(m)
    j = m["jobs"][link]
    print(f"✅ [{status.upper()}] {j['title']} at {j['company']}")

def shortlist_job(link): update_job_status(link, "shortlisted")
def apply_to_job(link):  update_job_status(link, "applied")
def reject_job(link):    update_job_status(link, "rejected")
def update_profile(updates):
    m = load(); m["profile"].update(updates); save(m)
    print(f"✅ Profile updated: {list(updates.keys())}")
def get_profile(): return load()["profile"]

def build_agent_context():
    m       = load()
    p       = m["profile"]
    stats   = m["stats"]
    last    = get_last_run_jobs()
    short   = [m["jobs"][l] for l in m["shortlist"] if l in m["jobs"]]
    applied = [m["jobs"][l] for l in m["applied"]   if l in m["jobs"]]
    return f"""
CANDIDATE PROFILE:
  Name:           {p['name']}
  Title:          {p['title']}
  Location:       {p['location']}
  Target Roles:   {', '.join(p['target_roles'])}
  Key Skills:     {', '.join(p['skills'])}
  Target Salary:  ${p['target_salary_min']:,}+

JOB SEARCH MEMORY:
  Total searches:    {stats['total_searches']}
  Total jobs found:  {stats['total_jobs_found']}
  Jobs applied:      {stats['total_applied']}
  Last run:          {m['last_run'][:19] if m['last_run'] else 'Never'}

LAST SEARCH ({len(last)} jobs):
{chr(10).join(f"  - {j['title']} at {j['company']} ({j['location']})" for j in last[:20]) or '  None yet'}

SHORTLISTED ({len(short)}):
{chr(10).join(f"  - {j['title']} at {j['company']}" for j in short) or '  None yet'}

APPLIED ({len(applied)}):
{chr(10).join(f"  - {j['title']} at {j['company']}" for j in applied) or '  None yet'}
""".strip()

def print_stats():
    m = load()
    jobs = m["jobs"]
    by_status = {}
    for j in jobs.values():
        s = j.get("status","new")
        by_status[s] = by_status.get(s,0) + 1
    print(f"\n{'='*50}")
    print(f"📊 JOBBY MEMORY STATS")
    print(f"{'='*50}")
    print(f"Total searches run:    {m['stats']['total_searches']}")
    print(f"Total jobs ever found: {m['stats']['total_jobs_found']}")
    print(f"Unique jobs stored:    {len(jobs)}")
    print(f"Applied to:            {m['stats']['total_applied']}")
    print(f"Last run:              {m['last_run'][:19] if m['last_run'] else 'Never'}")
    print(f"\nBy status:")
    for s,c in sorted(by_status.items()): print(f"  {s:15} {c}")
    print(f"{'='*50}\n")

def print_shortlist():
    m = load()
    jobs = [m["jobs"][l] for l in m["shortlist"] if l in m["jobs"]]
    if not jobs: print("No shortlisted jobs."); return
    print(f"\n⭐ SHORTLIST ({len(jobs)})\n{'='*50}")
    for j in jobs:
        print(f"\n  {j['title']} at {j['company']}")
        print(f"  📍 {j['location']}")
        print(f"  🔗 {j['link']}")

def print_last_run():
    jobs = get_last_run_jobs()
    if not jobs: print("No previous run."); return
    print(f"\n🕐 LAST RUN — {len(jobs)} jobs\n{'='*50}")
    for j in jobs:
        print(f"  [{j['location']}] {j['title']} at {j['company']}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if   cmd == "stats":     print_stats()
    elif cmd == "shortlist": print_shortlist()
    elif cmd == "last":      print_last_run()
    elif cmd == "context":   print(build_agent_context())
    elif cmd == "all":
        for j in get_all_jobs():
            print(f"  [{j.get('status','new'):12}] {j['title']} at {j['company']} — {j['location']}")
    elif cmd == "reset":
        if input("Reset ALL memory? Type YES: ") == "YES": reset()
    else:
        print("Commands: stats | last | shortlist | all | context | reset")
