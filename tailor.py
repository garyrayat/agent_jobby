#!/usr/bin/env python3
"""
tailor.py — Resume Tailor Agent
Usage:
  python3 tailor.py                 # interactive picker from jobs.json
  python3 tailor.py --index 3       # job #3 from jobs.json
  python3 tailor.py --link <url>    # any LinkedIn URL
"""

import asyncio, argparse, json, os, sys, subprocess, re, textwrap
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic
from playwright.async_api import async_playwright

AGENT_DIR   = Path(__file__).parent
JOBS_FILE   = AGENT_DIR / "jobs.json"
OUTPUT_BASE = AGENT_DIR / "applications"
NODE_DOCX   = str(AGENT_DIR / "node_modules/docx")
OUTPUT_BASE.mkdir(exist_ok=True)

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

GARRY_RESUME = """
GARRY SINGH
Senior Site Reliability Engineer · Platform and Cloud Infrastructure
Austin, TX · networkgarry@gmail.com · 469-756-1805 · linkedin.com/in/garry-singh-82ba8822

PROFESSIONAL SUMMARY
Senior SRE and platform engineer with 12 years across GCP, AWS, and distributed on-prem Linux
environments, uniquely positioned at the intersection of deep network engineering and cloud-native SRE.
Deep expertise in SLO-driven reliability engineering, Kubernetes platform operations, Terraform
infrastructure automation, CI/CD pipeline governance, and enterprise observability at scale. Proven track
record designing multi-region failover architectures, enforcing error budget driven deployment gates, and
driving platform strategy across cross-functional engineering teams. Strong networking foundation spanning
VPC and load balancer design, Kubernetes pod networking, and Layer 4/7 routing gives a diagnostic edge
across the full infrastructure stack that most SRE candidates lack.

EXPERIENCE

Senior Site Reliability Engineer | Nov 2023 - Present
The Home Depot · Austin, TX

- SLO Architecture and Deployment Gating: Designed and enforced SLI/SLO framework across ~50 services, integrating error budget burn-rate checks as Spinnaker webhook gates, reducing SLO breach frequency by ~35% and eliminating 10-15 false pages per on-call shift. Framework adopted across 6 product teams and 40+ engineers.
- Terraform Platform Automation: Authored reusable Terraform modules for GCP covering GKE cluster provisioning, VPC design, IAM bindings, Cloud Armor, and Load Balancer config across ~20 projects, reducing provisioning time by ~65%. Enforced OPA policy-as-code blocking 100% of non-compliant deployments.
- Multi-Region Failover Architecture: Designed weighted multi-region failover using Global LB traffic policies, regional health checks, and automated DNS failover, achieving full recovery within under 8 minutes. Authored ADRs, platform runbooks, and reliability guides. Led quarterly DR drills.
- Capacity Planning and Autoscaling: Migrated autoscaling from CPU triggers to request-rate metrics via Global LB, reducing p95 latency by ~33% and instance costs by ~20%. Zero rollout incidents across 3 major GKE version upgrades.
- Automation and Toil Reduction: Built event-driven remediation pipelines (Cloud Functions, Pub/Sub, Python) eliminating ~4 hrs/week of manual on-call toil. Designed dead-letter queues, fan-out patterns, and consumer lag alerting across messaging infrastructure.
- Observability and Incident Response: Standardized Grafana SLI dashboards and OpenTelemetry distributed tracing, improving MTTR by ~40%. Primary on-call for ~50 production services; led 15+ incident postmortems, reducing repeat incidents by ~30%.
- DevOps Enablement and Governance: Enforced least-privilege IAM across ~20 GCP projects, reducing over-permissioned accounts by ~50%. Presented reliability roadmaps to senior engineering leadership.

Independent Consultant — DevOps and Infrastructure Engineer | Aug 2019 - Sep 2023
NCR (Banking) · Cogeco (Telecom) · Telus (Telecom) · Toronto, ON / Atlanta, GA

- SLO and Reliability Engineering: Owned SLI/SLO definitions and on-call for GCP/AWS (GKE/EKS) workloads. Tuned alerts in Prometheus, Grafana, Cloud Monitoring, PagerDuty, reducing MTTD by ~45% and alert volume >50%.
- Terraform IaC at Scale: Built Terraform module libraries for GCP and AWS across 12+ infrastructure components, cutting provisioning time by ~70% and eliminating config drift behind ~40% of rollback events.
- Observability and APM: Redesigned Dynatrace alerting across Java Spring Boot microservices, reducing false-positive rate by ~65% and MTTRC by ~30 minutes.
- Messaging and Event-Driven Platforms: Operated RabbitMQ and AWS SQS/SNS across 8+ production services, reducing message loss incidents by ~45%.
- CI/CD and Linux Operations: Built Jenkins and Cloud Build pipelines with automated gates and rollback strategies, reducing pipeline failure rates by ~35%. Managed Linux fleets sustaining 3x traffic spikes.

Senior Network Engineer | Jan 2017 - Aug 2019
Rogers Communications · Toronto, ON
- Designed carrier-grade SIP/MPLS/WAN architectures achieving 99.95% uptime. Automated OSPF/QoS via Python RESTCONF across 20+ routers, cutting config time by ~50%.
- Deployed proactive monitoring (Zabbix, Nagios, Grafana) on SONET/DWDM infrastructure, reducing fault detection time by ~35%.

Systems Engineer | Apr 2014 - Dec 2016
LANtelligence / Caffcomm Systems · San Diego, CA
- Configured OSPF/BGP/EIGRP routing and Juniper/Cisco switching for 15+ enterprise clients. Executed 6+ data center migrations with zero unplanned downtime.

TECHNICAL SKILLS
SRE/Reliability  | SLI/SLO · Error Budgets · Spinnaker · PRRs · ADRs · Multi-region Failover · DR · Capacity planning
Cloud/Kubernetes | GCP · AWS · GKE · EKS · AKS · Kubernetes · Docker · Autoscaling · Helm · Linux
IaC/Automation   | Terraform · Ansible · OPA · Chef · Puppet · Python · Bash · Cloud Functions · RESTCONF
Observability    | Prometheus · Grafana · Dynatrace · OpenTelemetry · CloudWatch · PagerDuty · Zabbix · Nagios
CI/CD            | GitHub Actions · Jenkins · Cloud Build · Spinnaker · SonarQube · OPA policy-as-code
Messaging        | RabbitMQ · Pub/Sub · SQS/SNS · Kafka · Dead-letter queues · Fan-out patterns
Networking       | BGP · OSPF · MPLS · VPC · GLB/ALB/NLB · Cloud Armor · IPsec · SD-WAN · Route 53
Dev/Data         | Python · Bash · Java Spring Boot · SQL · PostgreSQL · Redis · Cassandra · BigQuery
Security         | IAM · RBAC · TLS · WAF · Least-Privilege · Wiz · Audit governance

CERTIFICATIONS
- GCP Professional Cloud DevOps Engineer · Google · 2025 · ID: PR000263
- Google Cloud Associate Engineer (ACE) · Google · 2024 · ID: 70951495
- AWS Certified Solutions Architect - Professional · Amazon · Expected Q3 2026
- Cisco Certified Network Professional (CCNP) · Cisco · ID: CSCO12651811
- Cisco Certified Network Associate (CCNA) · Cisco · 2020 · ID: CSCO11847293
- Microsoft Certified Solutions Associate (MCSA) · Microsoft · 2017 · ID: E849-5648

EDUCATION
Master of Engineering - Electrical and Computer Engineering · 2014 · University of Western Ontario · London, ON
Bachelor of Technology - Electronics and Telecom Engineering · 2012 · Punjab University · India
"""

async def fetch_job_description(url):
    print("   🌐 Fetching job description...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx  = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = await ctx.new_page()
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            text = ""
            for sel in [".description__text", ".show-more-less-html__markup", "[class*='description']"]:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        text = await el.inner_text()
                        if len(text) > 200: break
                except: continue
            if not text:
                text = await page.evaluate("() => document.body.innerText")
            await browser.close()
            return text[:6000]
    except Exception as e:
        print(f"   ⚠️  Could not fetch JD: {e}")
        return ""

def tailor_with_claude(job, jd):
    print("   🤖 Asking Claude to tailor resume...")
    prompt = f"""You are a professional resume writer tailoring Garry Singh's resume for a specific job.

JOB DETAILS:
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
URL: {job['link']}

JOB DESCRIPTION:
{jd if jd else "Not available — infer from job title and company."}

GARRY'S BASE RESUME:
{GARRY_RESUME}

INSTRUCTIONS:

TAILORED RESUME rules:
- Rewrite the Professional Summary (4-5 sentences) to mirror the job's exact language and priorities
- Keep the same section structure and ALL jobs/dates — do not remove anything
- Reorder bullets within each job to lead with the most relevant ones for this role
- Bold key phrases that directly match JD keywords (wrap in **double asterisks**)
- Keep ALL metrics — never remove or soften numbers
- Do NOT fabricate skills or invent experience
- For TECHNICAL SKILLS: reorder the rows so the most JD-relevant categories appear first, keep pipe | format
- If the JD mentions specific tools Garry lacks, add [MISSING: X] note at end of skills

COVER LETTER rules:
- 3 paragraphs, no fluff
- Para 1: Specific reason this role at this company (not generic)
- Para 2: 2-3 concrete proof points with metrics that directly answer the JD
- Para 3: Forward-looking close, mention Austin/Central timezone fit if remote role

Return EXACTLY in this format, no other text outside the tags:

===RESUME_START===
GARRY SINGH
Senior Site Reliability Engineer · Platform and Cloud Infrastructure
Austin, TX · networkgarry@gmail.com · 469-756-1805 · linkedin.com/in/garry-singh-82ba8822

[rest of tailored resume — use - for bullets, CAPS for section headers, Category | skills for skills rows]
===RESUME_END===

===COVER_LETTER_START===
Dear Hiring Manager,

[3 paragraphs]

Sincerely,
Garry Singh
networkgarry@gmail.com | 469-756-1805
===COVER_LETTER_END===

===FIT_SCORE===
Score: X/10
Reasoning: [2-3 sentences]
Gaps: [comma-separated or None]
===FIT_SCORE_END==="""

    resp = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4500,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text

def parse_response(text):
    def extract(s, e):
        i, j = text.find(s), text.find(e)
        return text[i+len(s):j].strip() if i != -1 and j != -1 else ""
    return {
        "resume":       extract("===RESUME_START===",       "===RESUME_END==="),
        "cover_letter": extract("===COVER_LETTER_START===", "===COVER_LETTER_END==="),
        "fit_score":    extract("===FIT_SCORE===",          "===FIT_SCORE_END==="),
    }

def build_resume_docx(resume_text, output_path):
    lines_json = json.dumps(resume_text.split('\n'))
    js = f"""
const {{ Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, BorderStyle, WidthType, ShadingType }} = require('{NODE_DOCX}');
const fs = require('fs');

const BLUE='1F3864', ACCENT='2E75B6', BLACK='000000', GRAY='595959';
const CONTENT_W=10440;

const lines = {lines_json};

function parseInlineBold(text, sz, color) {{
    return text.split(/(\*\*[^*]+\*\*)/).map(p =>
        p.startsWith('**') && p.endsWith('**')
            ? new TextRun({{ text: p.slice(2,-2), bold:true, size:sz, font:'Calibri', color }})
            : new TextRun({{ text: p, size:sz, font:'Calibri', color }})
    );
}}

function isSkillLine(t) {{ return t.includes(' | ') && !t.startsWith('-') && !t.includes('|  '); }}

function skillRow(line) {{
    const idx = line.indexOf(' | ');
    const cat = line.slice(0, idx).trim();
    const skills = line.slice(idx+3).trim();
    return new TableRow({{ children: [
        new TableCell({{
            width: {{ size:2100, type:WidthType.DXA }},
            borders: {{ top:{{style:'none'}},bottom:{{style:'none'}},left:{{style:'none'}},right:{{style:'none'}} }},
            shading: {{ fill:'EBF0F8', type:ShadingType.CLEAR }},
            margins: {{ top:60,bottom:60,left:100,right:100 }},
            children: [new Paragraph({{ children:[new TextRun({{ text:cat, bold:true, size:17, font:'Calibri', color:BLUE }})] }})]
        }}),
        new TableCell({{
            width: {{ size:CONTENT_W-2100, type:WidthType.DXA }},
            borders: {{ top:{{style:'none'}},bottom:{{style:'none'}},left:{{style:'none'}},right:{{style:'none'}} }},
            margins: {{ top:60,bottom:60,left:100,right:100 }},
            children: [new Paragraph({{ children:[new TextRun({{ text:skills, size:17, font:'Calibri', color:GRAY }})] }})]
        }}),
    ]}});
}}

const children=[];
let skillLines=[], inSkills=false, nameWritten=false;

for (const raw of lines) {{
    const t = raw.trim();
    if (!t) {{
        if (inSkills && skillLines.length) {{
            children.push(new Table({{ width:{{size:CONTENT_W,type:WidthType.DXA}}, columnWidths:[2100,CONTENT_W-2100], rows:skillLines.map(skillRow) }}));
            skillLines=[]; inSkills=false;
        }}
        children.push(new Paragraph({{ spacing:{{after:40}} }}));
        continue;
    }}
    if (!nameWritten) {{
        children.push(new Paragraph({{ alignment:AlignmentType.CENTER, spacing:{{after:20}}, children:[new TextRun({{text:t,bold:true,size:36,font:'Calibri',color:BLUE}})] }}));
        nameWritten=true; continue;
    }}
    if (t.includes('@') || t.includes('linkedin') || t.match(/\\d{{3}}-\\d{{3}}/)) {{
        children.push(new Paragraph({{ alignment:AlignmentType.CENTER, spacing:{{after:100}}, children:[new TextRun({{text:t,size:18,font:'Calibri',color:GRAY}})] }}));
        continue;
    }}
    const isHeader = t===t.toUpperCase() && t.replace(/[^A-Z]/g,'').length>3 && !t.startsWith('-') && t.length<70;
    if (isHeader) {{
        if (t==='TECHNICAL SKILLS') inSkills=true;
        children.push(new Paragraph({{ spacing:{{before:200,after:80}}, border:{{bottom:{{style:BorderStyle.SINGLE,size:8,color:ACCENT,space:1}}}}, children:[new TextRun({{text:t,bold:true,size:20,font:'Calibri',color:BLUE}})] }}));
        continue;
    }}
    if (inSkills && isSkillLine(t)) {{ skillLines.push(t); continue; }}
    if (t.startsWith('-') || t.startsWith('•')) {{
        children.push(new Paragraph({{ indent:{{left:300,hanging:200}}, spacing:{{after:60}}, children:[new TextRun({{text:'•  ',size:18,font:'Calibri'}}), ...parseInlineBold(t.replace(/^[-•]\\s*/,''),18,BLACK)] }}));
        continue;
    }}
    if (t.includes(' | ') && !inSkills) {{
        const [role,...rest]=t.split(' | ');
        children.push(new Paragraph({{ spacing:{{before:120,after:40}}, children:[new TextRun({{text:role.trim(),bold:true,size:20,font:'Calibri',color:BLACK}}), new TextRun({{text:'  |  '+rest.join(' | ').trim(),size:18,font:'Calibri',color:GRAY}})] }}));
        continue;
    }}
    if (t.includes(' · ') && !t.includes('@') && !t.includes('linkedin')) {{
        children.push(new Paragraph({{ spacing:{{after:80}}, children:[new TextRun({{text:t,size:18,font:'Calibri',color:GRAY,italics:true}})] }}));
        continue;
    }}
    children.push(new Paragraph({{ spacing:{{after:60}}, children:parseInlineBold(t,18,BLACK) }}));
}}
if (skillLines.length) children.push(new Table({{ width:{{size:CONTENT_W,type:WidthType.DXA}}, columnWidths:[2100,CONTENT_W-2100], rows:skillLines.map(skillRow) }}));

const doc = new Document({{ sections:[{{ properties:{{ page:{{ size:{{width:12240,height:15840}}, margin:{{top:720,right:864,bottom:720,left:864}} }} }}, children }}] }});
Packer.toBuffer(doc).then(buf=>{{fs.writeFileSync('{output_path}',buf);console.log('done');}}).catch(e=>{{console.error(e.message);process.exit(1);}});
"""
    tmp="/tmp/build_resume.js"
    with open(tmp,"w") as f: f.write(js)
    r=subprocess.run(["node",tmp],capture_output=True,text=True)
    if r.returncode!=0: print(f"   ❌ Resume DOCX: {r.stderr[:300]}"); return False
    print(f"   ✅ Resume DOCX: {output_path}"); return True

def build_coverletter_docx(cl_text, job, output_path):
    lines_json = json.dumps(cl_text.split('\n'))
    date_str = datetime.now().strftime("%B %d, %Y")
    title_escaped = job['title'].replace("'","\\'")
    company_escaped = job['company'].replace("'","\\'")
    js = f"""
const {{ Document, Packer, Paragraph, TextRun, BorderStyle }} = require('{NODE_DOCX}');
const fs = require('fs');
const BLUE='1F3864', GRAY='595959', BLACK='000000';
const lines = {lines_json};
const children = [
    new Paragraph({{ spacing:{{after:40}}, children:[new TextRun({{text:'GARRY SINGH',bold:true,size:28,font:'Calibri',color:BLUE}})] }}),
    new Paragraph({{ spacing:{{after:40}}, children:[new TextRun({{text:'Austin, TX  ·  networkgarry@gmail.com  ·  469-756-1805',size:18,font:'Calibri',color:GRAY}})] }}),
    new Paragraph({{ spacing:{{after:160}}, border:{{bottom:{{style:BorderStyle.SINGLE,size:8,color:'2E75B6',space:1}}}}, children:[new TextRun({{text:'',size:18}})] }}),
    new Paragraph({{ spacing:{{after:160}}, children:[new TextRun({{text:'{date_str}',size:18,font:'Calibri'}})] }}),
    new Paragraph({{ spacing:{{after:40}}, children:[new TextRun({{text:'Re: {title_escaped} — {company_escaped}',bold:true,size:18,font:'Calibri'}})] }}),
    new Paragraph({{ spacing:{{after:160}}, children:[new TextRun({{text:'',size:18}})] }}),
];
for (const raw of lines) {{
    const t=raw.trim();
    if (!t) {{ children.push(new Paragraph({{spacing:{{after:140}}}})); continue; }}
    const isBold = t.startsWith('Dear') || t.startsWith('Sincerely') || t==='Garry Singh';
    children.push(new Paragraph({{ spacing:{{after:120}}, children:[new TextRun({{text:t,bold:isBold,size:18,font:'Calibri'}})] }}));
}}
const doc=new Document({{sections:[{{properties:{{page:{{size:{{width:12240,height:15840}},margin:{{top:1008,right:1152,bottom:1008,left:1152}}}}}},children}}]}});
Packer.toBuffer(doc).then(buf=>{{fs.writeFileSync('{output_path}',buf);console.log('done');}}).catch(e=>{{console.error(e.message);process.exit(1);}});
"""
    tmp="/tmp/build_cl.js"
    with open(tmp,"w") as f: f.write(js)
    r=subprocess.run(["node",tmp],capture_output=True,text=True)
    if r.returncode!=0: print(f"   ❌ Cover letter DOCX: {r.stderr[:300]}"); return False
    print(f"   ✅ Cover letter DOCX: {output_path}"); return True

def convert_to_pdf(docx_path, output_dir):
    try:
        r=subprocess.run(["libreoffice","--headless","--convert-to","pdf","--outdir",str(output_dir),str(docx_path)],capture_output=True,text=True,timeout=45)
        if r.returncode==0: print(f"   ✅ PDF: {output_dir}/{Path(docx_path).stem}.pdf")
        else: print(f"   ⚠️  PDF failed: {r.stderr[:100]}")
    except FileNotFoundError: print("   ⚠️  PDF skipped — run: brew install --cask libreoffice")
    except Exception as e: print(f"   ⚠️  PDF error: {e}")

def pick_interactive():
    if not JOBS_FILE.exists(): print("❌ No jobs.json. Run jobb_latest.py first."); sys.exit(1)
    with open(JOBS_FILE) as f: jobs=json.load(f)
    print(f"\n{'─'*72}")
    for i,j in enumerate(jobs):
        status=j.get("status","new")
        label=f"{j['title']} at {j['company']} — {j['location']}"
        print(f"  [{i:>2}] [{status:10}]  {label[:58]}")
    print(f"{'─'*72}")
    idx=input("\nPick a number (q to quit): ").strip()
    if idx.lower()=='q': sys.exit(0)
    return jobs[int(idx)], jobs, int(idx)

async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--index",type=int)
    parser.add_argument("--link",type=str)
    args=parser.parse_args()

    jobs_list=[]; job_idx=None
    if args.link:
        job={"title":"Role","company":"Company","location":"Unknown","link":args.link,"status":"new"}
    elif args.index is not None:
        with open(JOBS_FILE) as f: jobs_list=json.load(f)
        job=jobs_list[args.index]; job_idx=args.index
    else:
        job,jobs_list,job_idx=pick_interactive()

    slug=re.sub(r'[^a-z0-9]+','-',f"{job['company']}-{job['title']}".lower())[:60]
    out=OUTPUT_BASE/slug
    out.mkdir(parents=True,exist_ok=True)

    print(f"\n🎯 Tailoring: {job['title']} at {job['company']}")
    print(f"   📁 {out}\n")

    jd=await fetch_job_description(job["link"])
    raw=tailor_with_claude(job,jd)
    parsed=parse_response(raw)

    if not parsed["resume"]:
        print("❌ Bad Claude response. Saving raw output.")
        with open(out/"raw_output.txt","w") as f: f.write(raw)
        sys.exit(1)

    print(f"\n{'─'*60}\n📊 FIT ASSESSMENT\n{'─'*60}")
    print(parsed["fit_score"])
    print(f"{'─'*60}\n")

    co=re.sub(r'[^a-z0-9]+','-',job['company'].lower())[:25]
    r_docx=out/f"Garry_Singh_{co}_resume.docx"
    c_docx=out/f"Garry_Singh_{co}_coverletter.docx"

    build_resume_docx(parsed["resume"], str(r_docx))
    build_coverletter_docx(parsed["cover_letter"], job, str(c_docx))
    convert_to_pdf(r_docx, out)
    convert_to_pdf(c_docx, out)

    with open(out/"metadata.json","w") as f:
        json.dump({"job":job,"fit_score":parsed["fit_score"],"cover_letter":parsed["cover_letter"],"tailored_at":datetime.now().isoformat()},f,indent=2)

    print()
    if input("Mark as 'tailored' in jobs.json? (y/n): ").strip().lower()=='y' and jobs_list and job_idx is not None:
        jobs_list[job_idx]["status"]="tailored"
        jobs_list[job_idx]["output_dir"]=str(out)
        jobs_list[job_idx]["tailored_at"]=datetime.now().isoformat()
        with open(JOBS_FILE,"w") as f: json.dump(jobs_list,f,indent=2)
        print("✅ Status updated.")
    else:
        print("↩️  Status unchanged.")

    print(f"\n✅ Done!\n   open {out}")

if __name__=="__main__":
    asyncio.run(main())
