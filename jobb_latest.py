import asyncio
import json
import sys
import os
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memory as mem

QUERIES = [
    {"keywords": "Senior Site Reliability Engineer",    "location": "Austin, TX"},
    {"keywords": "Staff Site Reliability Engineer",     "location": "Austin, TX"},
    {"keywords": "Senior Platform Engineer",            "location": "Austin, TX"},
    {"keywords": "Staff Platform Engineer",             "location": "Austin, TX"},
    {"keywords": "Senior DevOps Engineer",              "location": "Austin, TX"},
    {"keywords": "Senior Solutions Architect",          "location": "Austin, TX"},
    {"keywords": "Senior Customer Engineer",            "location": "Austin, TX"},
    {"keywords": "Senior Pre-Sales Engineer",           "location": "Austin, TX"},
    {"keywords": "Senior Customer Success Engineer",    "location": "Austin, TX"},
    {"keywords": "Senior Solutions Engineer",           "location": "Austin, TX"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Dallas, TX"},
    {"keywords": "Senior DevOps Engineer",              "location": "Dallas, TX"},
    {"keywords": "Senior Solutions Architect",          "location": "Dallas, TX"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Houston, TX"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "New York, NY"},
    {"keywords": "Staff Site Reliability Engineer",     "location": "New York, NY"},
    {"keywords": "Senior Solutions Architect",          "location": "New York, NY"},
    {"keywords": "Senior Customer Engineer",            "location": "New York, NY"},
    {"keywords": "Senior Pre-Sales Engineer",           "location": "New York, NY"},
    {"keywords": "Senior Customer Success Engineer",    "location": "New York, NY"},
    {"keywords": "Senior Solutions Engineer",           "location": "New York, NY"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "San Francisco, CA"},
    {"keywords": "Senior Solutions Architect",          "location": "San Francisco, CA"},
    {"keywords": "Senior Customer Engineer",            "location": "San Francisco, CA"},
    {"keywords": "Senior Pre-Sales Engineer",           "location": "San Francisco, CA"},
    {"keywords": "Senior Customer Success Engineer",    "location": "San Francisco, CA"},
    {"keywords": "Senior Solutions Engineer",           "location": "San Francisco, CA"},
    {"keywords": "Staff Site Reliability Engineer",     "location": "San Francisco, CA"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Seattle, WA"},
    {"keywords": "Senior Platform Engineer",            "location": "Seattle, WA"},
    {"keywords": "Senior Solutions Architect",          "location": "Seattle, WA"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Boston, MA"},
    {"keywords": "Senior Solutions Architect",          "location": "Boston, MA"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Chicago, IL"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Washington, DC"},
    {"keywords": "Senior Solutions Architect",          "location": "Washington, DC"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Denver, CO"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Atlanta, GA"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Stamford, CT"},
    {"keywords": "Staff SRE",                           "location": "Stamford, CT"},
]

CONCURRENCY        = 8
MAX_JOBS_PER_QUERY = 15

BLOCKED_LOCATIONS = [
    "india","bangalore","bengaluru","mumbai","pune","hyderabad","chennai","delhi","kolkata","gurgaon","noida",
    "canada","toronto","vancouver","uk","united kingdom","london","germany","berlin","france","paris",
    "poland","brazil","mexico","philippines","malaysia","indonesia","nigeria","south africa",
    "netherlands","ireland","spain","italy","sweden","denmark","norway","finland",
    "pakistan","sri lanka","bangladesh","dubai","singapore","australia","luxembourg",
]

US_ALLOWED = [
    "austin","dallas","houston","san antonio","fort worth",
    "san francisco","san jose","mountain view","palo alto","menlo park","sunnyvale","santa clara",
    "los angeles","irvine","san diego","seattle","bellevue","redmond",
    "new york","brooklyn","manhattan","jersey city","boston","cambridge",
    "chicago","washington","arlington","mclean","reston","bethesda",
    "connecticut","stamford","hartford","greenwich","denver","boulder",
    "atlanta","miami","raleigh","charlotte","minneapolis","phoenix",
    "salt lake city","portland","pittsburgh","philadelphia","nashville",
    "round rock","cedar park","buda","pflugerville","san marcos",
    "remote","united states","usa","anywhere","nationwide",
    ", tx",", ny",", ca",", wa",", ma",", il",", dc",", co",", ga",", fl",", nc",", ct",", va",", md",
]

# ── Hard block: explicitly wrong roles ───────────────────────────────────────
HARD_BLOCK = [
    # Wrong level
    "intern","internship","co-op","coop","junior","entry level","graduate","new grad",
    "engineer i,","engineer i ","engineer ii","engineer 1","engineer 2","tier 1","level 1",
    # Wrong role entirely
    "technical support","tech support","support engineer",
    "helpdesk","help desk","service desk","it support",
    "noc engineer","network operations center",
    "field engineer","field technician",
    "ios developer","android developer","mobile developer",
    "data scientist","machine learning engineer","ml engineer",
    "qa engineer","quality assurance","test engineer","sdet",
    "asic","fpga","embedded engineer","firmware engineer",
    "product manager","project manager","program manager","scrum master",
    "account executive","account manager",
    "recruiter","talent acquisition",
    "database administrator",
    "financial analyst","business analyst",
    "simulation engineer","hardware modeling",
    "forward deployed",
    "cloud security engineer","network security","cybersecurity",
    "networking engineer","network engineer","cloud networking",
    "data engineer","data platform engineer",
    # Plain SWE without cloud qualifier (checked separately below)
    "staff software engineer","principal software engineer",
    "frontend engineer","front-end engineer","full-stack engineer","full stack engineer",
    "ml infrastructure","ml platform engineer",
    # Management
    "sr manager","senior manager","director,","vp of","vice president",
    # Domain blockers
    "aerospace","defense contractor","semiconductor design",
    "salesforce developer","netsuite","sap consultant",
    "field solutions architect","ai solutions architect",
    "relocate to singapore","relocate to india",
    # Staffing body shops
    "tata consultancy","infosys","wipro","cognizant","hcl tech","capgemini",
    "via dice","via indeed",
]

# ── Must match one target role ────────────────────────────────────────────────
ROLE_MATCH = [
    "site reliability engineer","sre",
    "platform engineer","devops engineer",
    "infrastructure engineer","cloud engineer",
    "solutions architect",
    "customer engineer","customer success engineer",
    "pre-sales engineer","presales engineer","solutions engineer",
    "staff engineer","principal engineer",
]

# ── Seniority required for ALL roles ─────────────────────────────────────────
# SRE/SRE-adjacent titles are exempt because "Site Reliability Engineer" already
# implies a higher bar — juniors are almost never titled SRE at real companies
SENIORITY_REQUIRED = ["senior","staff","principal","lead","sr.","sr ","sr/"]
SENIORITY_EXEMPT   = [
    "site reliability engineer","sre",
    "solutions architect",
    "customer engineer","customer success engineer",
    "pre-sales engineer","presales engineer",
]

def is_allowed_location(loc):
    loc = loc.lower()
    for b in BLOCKED_LOCATIONS:
        if b in loc: return False
    for a in US_ALLOWED:
        if a in loc: return True
    return False

def passes_title(title):
    t = title.lower()

    # Hard block first
    for kw in HARD_BLOCK:
        if kw in t: return False

    # Plain "senior software engineer" only passes if cloud/devops qualifier present
    if "software engineer" in t:
        cloud_qualified = any(kw in t for kw in [
            "aws","gcp","azure","cloud","devops","sre","reliability",
            "infrastructure","kubernetes","k8s","platform infra",
        ])
        if not cloud_qualified: return False

    # Must match a target role
    if not any(kw in t for kw in ROLE_MATCH): return False

    # Seniority check — exempt roles skip this
    if any(kw in t for kw in SENIORITY_EXEMPT): return True
    return any(kw in t for kw in SENIORITY_REQUIRED)

def apply_priority(loc):
    l = loc.lower()
    if "austin" in l: return 0
    if any(x in l for x in ["dallas","houston","san antonio"]): return 1
    if any(x in l for x in [", tx","texas","round rock","cedar park","buda"]): return 2
    if any(x in l for x in ["remote","united states","usa","anywhere","nationwide"]): return 3
    if any(x in l for x in ["new york","brooklyn","manhattan"]): return 4
    if any(x in l for x in ["san francisco","mountain view","palo alto","sunnyvale","santa clara"]): return 5
    if any(x in l for x in ["seattle","bellevue","redmond"]): return 6
    if any(x in l for x in ["boston","cambridge"]): return 7
    if "chicago" in l: return 8
    if any(x in l for x in ["washington","mclean","arlington"]): return 9
    if any(x in l for x in ["stamford","greenwich","connecticut"]): return 10
    if any(x in l for x in ["los angeles","irvine","san diego"]): return 11
    return 12

async def scrape(context, keywords, location, semaphore):
    async with semaphore:
        jobs = []
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={keywords.replace(' ','%20')}"
            f"&location={location.replace(' ','%20')}"
            f"&f_TPR=r1209600&sortBy=DD"
        )
        page = await context.new_page()
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            await page.keyboard.press("End")
            await page.wait_for_timeout(800)

            soup  = BeautifulSoup(await page.content(), "html.parser")
            cards = soup.find_all("div", class_=lambda c: c and "job-search-card" in (
                c if isinstance(c, str) else " ".join(c)
            ))

            for card in cards[:MAX_JOBS_PER_QUERY]:
                try:
                    t  = card.find("h3")
                    co = card.find("h4")
                    lo = card.find(class_=lambda c: c and "job-search-card__location" in (
                        c if isinstance(c, str) else " ".join(c)
                    ))
                    lk = card.find("a", href=lambda h: h and "/jobs/view/" in str(h))
                    dt = card.find("time")

                    title   = t.get_text(strip=True)   if t  else "Unknown"
                    company = co.get_text(strip=True)  if co else "Unknown"
                    loc     = lo.get_text(strip=True)  if lo else location
                    link    = lk["href"].split("?")[0] if lk else ""
                    posted  = dt.get("datetime","")    if dt else ""

                    if title == "Unknown" or company == "Unknown": continue
                    if not passes_title(title): continue
                    if not is_allowed_location(loc): continue
                    if not link: continue

                    jobs.append({
                        "title":          title,
                        "company":        company,
                        "location":       loc,
                        "link":           link,
                        "posted":         posted,
                        "source":         "linkedin",
                        "keywords":       keywords,
                        "scraped_at":     datetime.now().isoformat(),
                        "status":         "new",
                        "apply_priority": apply_priority(loc)
                    })
                except: continue

        except Exception as e:
            print(f"   ❌ {keywords}/{location}: {e}")
        finally:
            await page.close()

        if jobs: print(f"   ✅ [{location}] {keywords}: {len(jobs)}")
        return jobs

async def run():
    start = datetime.now()
    print(f"\n🚀 JOBBY — {len(QUERIES)} LinkedIn searches")
    print(f"   {CONCURRENCY} parallel | US only | Senior/Staff only | 14-day window\n")

    semaphore = asyncio.Semaphore(CONCURRENCY)
    all_jobs  = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ))
        results = await asyncio.gather(*[
            scrape(ctx, q["keywords"], q["location"], semaphore)
            for q in QUERIES
        ])
        for jobs in results: all_jobs.extend(jobs)
        await browser.close()

    seen, unique = set(), []
    for job in all_jobs:
        if job["link"] not in seen:
            seen.add(job["link"]); unique.append(job)

    unique.sort(key=lambda j: apply_priority(j["location"]))

    with open("jobs.json", "w") as f: json.dump(unique, f, indent=2)
    mem.save_search_run(unique, queries_run=len(QUERIES))

    elapsed = (datetime.now() - start).seconds

    groups = [
        ("🏠 AUSTIN TX — Apply First",  [j for j in unique if "austin" in j["location"].lower()]),
        ("🤠 Texas (other)",             [j for j in unique if any(x in j["location"].lower() for x in ["dallas","houston","san antonio","round rock","cedar park","buda"]) and "austin" not in j["location"].lower()]),
        ("🌐 Remote US — Apply Second",  [j for j in unique if any(x in j["location"].lower() for x in ["remote","united states","usa","anywhere","nationwide"])]),
        ("🗽 New York",                   [j for j in unique if "new york" in j["location"].lower()]),
        ("🌉 Bay Area",                   [j for j in unique if any(x in j["location"].lower() for x in ["san francisco","mountain view","palo alto","sunnyvale","santa clara"])]),
        ("🌲 Seattle",                    [j for j in unique if any(x in j["location"].lower() for x in ["seattle","bellevue","redmond"])]),
        ("🦞 Boston",                     [j for j in unique if "boston" in j["location"].lower()]),
        ("🍕 Chicago",                    [j for j in unique if "chicago" in j["location"].lower()]),
        ("🏛️  DC / Virginia",            [j for j in unique if any(x in j["location"].lower() for x in ["washington","mclean","arlington"])]),
        ("🌴 Other US",                   [j for j in unique if apply_priority(j["location"]) >= 10]),
    ]

    print(f"\n{'='*60}")
    print(f"🏁 DONE in {elapsed}s — {len(unique)} jobs found")
    print(f"{'='*60}")

    for label, jobs in groups:
        if not jobs: continue
        print(f"\n{label} ({len(jobs)})")
        for j in jobs:
            print(f"   {j['title']} at {j['company']} — {j['location']}")

    print(f"\n📄 Saved to jobs.json + memory")
    print(f"💡 python3 memory.py stats")
    print(f"💡 python3 memory.py last")
    print(f"💡 python3 memory.py shortlist")

if __name__ == "__main__":
    asyncio.run(run())
