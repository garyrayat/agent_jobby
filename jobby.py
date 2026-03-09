import asyncio
import json
import sys
import os
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memory as mem

# ─────────────────────────────────────────────────────────────────────────────
# SEARCH QUERIES — LinkedIn only
# ─────────────────────────────────────────────────────────────────────────────
QUERIES = [
    # Austin TX — apply first
    {"keywords": "Senior Site Reliability Engineer",    "location": "Austin, TX"},
    {"keywords": "Staff Site Reliability Engineer",     "location": "Austin, TX"},
    {"keywords": "Senior Platform Engineer",            "location": "Austin, TX"},
    {"keywords": "Staff Platform Engineer",             "location": "Austin, TX"},
    {"keywords": "Senior DevOps Engineer",              "location": "Austin, TX"},
    {"keywords": "Senior Solutions Architect",          "location": "Austin, TX"},
    {"keywords": "Staff Solutions Architect",           "location": "Austin, TX"},
    {"keywords": "Senior Customer Engineer",            "location": "Austin, TX"},
    {"keywords": "Senior Pre-Sales Engineer",           "location": "Austin, TX"},
    # Texas
    {"keywords": "Senior Site Reliability Engineer",    "location": "Dallas, TX"},
    {"keywords": "Senior Solutions Architect",          "location": "Dallas, TX"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Houston, TX"},
    # Remote US — apply second
    {"keywords": "Staff SRE",                           "location": "Remote"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Remote"},
    {"keywords": "Senior Platform Engineer",            "location": "Remote"},
    {"keywords": "Staff Platform Engineer",             "location": "Remote"},
    {"keywords": "Senior Solutions Architect Cloud",    "location": "Remote"},
    {"keywords": "Senior Customer Engineer",            "location": "Remote"},
    {"keywords": "Senior Pre-Sales Engineer",           "location": "Remote"},
    {"keywords": "Senior DevOps Engineer",              "location": "Remote"},
    # Major US hubs
    {"keywords": "Senior Site Reliability Engineer",    "location": "New York, NY"},
    {"keywords": "Staff SRE",                           "location": "New York, NY"},
    {"keywords": "Senior Pre-Sales Solutions Engineer", "location": "New York, NY"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "San Francisco, CA"},
    {"keywords": "Senior Solutions Architect GCP",      "location": "San Francisco, CA"},
    {"keywords": "Senior Customer Engineer Cloud",      "location": "San Francisco, CA"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Seattle, WA"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Boston, MA"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Chicago, IL"},
    {"keywords": "Senior Site Reliability Engineer",    "location": "Washington, DC"},
]

CONCURRENCY        = 6
MAX_JOBS_PER_QUERY = 15

# ─────────────────────────────────────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────────────────────────────────────
US_ALLOWED = [
    "austin","dallas","houston","san antonio","fort worth",
    "san francisco","san jose","mountain view","palo alto","menlo park",
    "sunnyvale","santa clara","cupertino","redwood city","los angeles",
    "irvine","san diego","seattle","bellevue","redmond","kirkland",
    "new york","brooklyn","manhattan","jersey city","hoboken",
    "boston","cambridge","chicago","washington","arlington","mclean",
    "reston","bethesda","connecticut","stamford","hartford","greenwich",
    "denver","boulder","atlanta","miami","raleigh","charlotte",
    "minneapolis","phoenix","scottsdale","salt lake city","portland",
    "pittsburgh","philadelphia","nashville",
    "remote","united states","usa","anywhere","nationwide",
    ", tx",", ny",", ca",", wa",", ma",", il",", dc",
    ", co",", ga",", fl",", nc",", ct",", va",", md",", or",
]

BLOCKED_LOCATIONS = [
    "india","bangalore","bengaluru","mumbai","pune","hyderabad",
    "chennai","delhi","kolkata","gurgaon","noida",
    "canada","toronto","vancouver","ontario","british columbia",
    "uk","united kingdom","london","manchester",
    "germany","berlin","munich","france","paris",
    "poland","cracow","warsaw","brazil","mexico",
    "philippines","manila","malaysia","kuala lumpur",
    "indonesia","jakarta","nigeria","south africa","cape town",
    "netherlands","amsterdam","ireland","dublin",
    "spain","madrid","italy","milan",
    "sweden","denmark","norway","finland",
    "pakistan","sri lanka","bangladesh",
    "dubai","singapore","australia","luxembourg",
]

BLOCKED_TITLES = [
    "intern","internship","co-op","coop","apprentice",
    "junior","entry level","graduate","new grad","associate ",
    "technical support","tech support","support engineer",
    "operations engineer","noc ","network operations center",
    "helpdesk","help desk","service desk","it support",
    "field engineer","field technician","field service",
    "customer support","customer service representative",
    "front end","frontend","ios","android","mobile developer",
    "data scientist","machine learning","ml engineer",
    "qa engineer","quality assurance","test engineer","sdet",
    "asic","fpga","embedded","firmware","hardware engineer",
    "product manager","project manager","scrum master",
    "account executive","account manager",
    "recruiter","talent acquisition","hr ","marketing",
    "business analyst","security analyst","soc analyst",
    "database administrator","dba",
    "systems administrator","sysadmin","it administrator",
    "full stack","fullstack","backend developer","frontend developer",
    "simulation engineer","modeling engineer",
    "forward deployed",
]

REQUIRED_TITLE_KEYWORDS = [
    "senior","staff","principal","lead","architect",
    "sre","devops","platform","reliability","infrastructure",
    "solutions","cloud engineer","customer engineer",
    "customer success engineer","pre-sales","presales",
]

def is_allowed_location(loc):
    loc = loc.lower()
    for b in BLOCKED_LOCATIONS:
        if b in loc: return False
    for a in US_ALLOWED:
        if a in loc: return True
    return False

def passes_title_filter(title):
    t = title.lower()
    for kw in BLOCKED_TITLES:
        if kw in t: return False
    return any(kw in t for kw in REQUIRED_TITLE_KEYWORDS)

def apply_priority(job):
    loc = job.get("location","").lower()
    if "austin" in loc: return 0
    if any(x in loc for x in ["dallas","houston","san antonio"]): return 1
    if any(x in loc for x in [", tx","texas"]): return 2
    if any(x in loc for x in ["remote","united states","usa","anywhere","nationwide"]): return 3
    if any(x in loc for x in ["new york","brooklyn","manhattan"]): return 4
    if any(x in loc for x in ["san francisco","mountain view","palo alto","sunnyvale","santa clara"]): return 5
    if any(x in loc for x in ["seattle","bellevue","redmond"]): return 6
    if any(x in loc for x in ["boston","cambridge"]): return 7
    if "chicago" in loc: return 8
    if any(x in loc for x in ["washington","mclean","arlington"]): return 9
    if any(x in loc for x in ["connecticut","stamford","greenwich"]): return 10
    if any(x in loc for x in ["los angeles","irvine","san diego"]): return 11
    return 12

# ─────────────────────────────────────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────────────────────────────────────
async def scrape(context, keywords, location, semaphore):
    async with semaphore:
        jobs = []
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={keywords.replace(' ','%20')}"
            f"&location={location.replace(' ','%20')}"
            f"&f_TPR=r86400&sortBy=DD"
        )
        page = await context.new_page()
        try:
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            await page.keyboard.press("End")
            await page.wait_for_timeout(800)

            soup  = BeautifulSoup(await page.content(), "html.parser")
            cards = soup.find_all("div", class_=lambda c: c and "job-search-card" in c)
            if not cards:
                cards = soup.find_all("li", class_=lambda c: c and "jobs-search-results__list-item" in c)

            for card in cards[:MAX_JOBS_PER_QUERY]:
                try:
                    t  = card.find("h3") or card.find(class_=lambda c: c and "job-title" in str(c))
                    co = card.find("h4") or card.find(class_=lambda c: c and "company-name" in str(c))
                    lo = card.find(class_=lambda c: c and "job-search-card__location" in str(c))
                    lk = card.find("a", href=lambda h: h and "/jobs/view/" in str(h))
                    dt = card.find("time")

                    title   = t.get_text(strip=True)   if t  else "Unknown"
                    company = co.get_text(strip=True)  if co else "Unknown"
                    loc     = lo.get_text(strip=True)  if lo else location
                    link    = lk["href"].split("?")[0] if lk else ""
                    posted  = dt.get("datetime","")    if dt else ""

                    if title == "Unknown" or company == "Unknown": continue
                    if not passes_title_filter(title): continue
                    if not is_allowed_location(loc): continue
                    if not link: continue

                    jobs.append({
                        "title":         title,
                        "company":       company,
                        "location":      loc,
                        "link":          link,
                        "posted":        posted,
                        "source":        "linkedin",
                        "keywords":      keywords,
                        "scraped_at":    datetime.now().isoformat(),
                        "status":        "new",
                        "apply_priority": apply_priority({"location": loc})
                    })
                except: continue

        except Exception as e:
            print(f"   ❌ {keywords}/{location}: {e}")
        finally:
            await page.close()

        if jobs: print(f"   ✅ [{location}] {keywords}: {len(jobs)}")
        return jobs

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
async def run():
    start = datetime.now()
    print(f"\n🚀 JOBBY — {len(QUERIES)} LinkedIn searches")
    print(f"   {CONCURRENCY} parallel | US only | Senior/Staff only\n")

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

    # Deduplicate
    seen, unique = set(), []
    for job in all_jobs:
        if job["link"] not in seen:
            seen.add(job["link"]); unique.append(job)

    # Sort: Austin > Remote US > rest
    unique.sort(key=apply_priority)

    # Save
    with open("jobs.json", "w") as f: json.dump(unique, f, indent=2)
    mem.save_search_run(unique, queries_run=len(QUERIES))

    elapsed = (datetime.now() - start).seconds

    groups = [
        ("🏠 AUSTIN TX — Apply First",   [j for j in unique if "austin" in j["location"].lower()]),
        ("🤠 Texas (other)",              [j for j in unique if any(x in j["location"].lower() for x in ["dallas","houston","san antonio"]) and "austin" not in j["location"].lower()]),
        ("🌐 Remote US — Apply Second",   [j for j in unique if any(x in j["location"].lower() for x in ["remote","united states","usa","anywhere"])]),
        ("🗽 New York",                    [j for j in unique if "new york" in j["location"].lower()]),
        ("🌉 Bay Area",                    [j for j in unique if any(x in j["location"].lower() for x in ["san francisco","mountain view","palo alto","sunnyvale","santa clara"])]),
        ("🌲 Seattle",                     [j for j in unique if "seattle" in j["location"].lower() or "bellevue" in j["location"].lower()]),
        ("🦞 Boston",                      [j for j in unique if "boston" in j["location"].lower()]),
        ("🍕 Chicago",                     [j for j in unique if "chicago" in j["location"].lower()]),
        ("🏛️  DC / Virginia",             [j for j in unique if any(x in j["location"].lower() for x in ["washington","mclean","arlington"])]),
        ("🌴 Other US",                    [j for j in unique if apply_priority(j) >= 10]),
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
