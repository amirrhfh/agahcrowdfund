"""
IFB Crowdfunding Scraper
- On first run: scrapes ALL projects (2000+) — run this once on your machine
- On subsequent runs (GitHub Actions): only fetches NEW projects, stops early
- Output: data.json (no database, no server needed)
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import os
import sys
from datetime import datetime, timezone

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')

BASE_URL = 'https://www.ifb.ir/Finstars/AllCrowdFundingProject.aspx'
DESC_URL = 'https://www.ifb.ir/Finstars/AllCrowdFundingProject.aspx/showDesc'
GRID_ID  = 'ctl00$ContentPlaceHolder1$grdCrowdFundingData'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
    'Accept-Language': 'fa,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
POST_HEADERS = {
    **HEADERS,
    'Content-Type': 'application/x-www-form-urlencoded',
    'Referer': BASE_URL,
}
DESC_HEADERS = {
    'User-Agent': HEADERS['User-Agent'],
    'Content-Type': 'application/json; charset=utf-8',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Origin': 'https://www.ifb.ir',
    'Referer': BASE_URL,
}


def log(msg):
    """Print safely on all platforms (Windows/Linux/Mac)."""
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode('ascii'), flush=True)


def load_existing_data():
    """Load existing data.json. Returns (projects_list, known_ids_set)."""
    if not os.path.exists(DATA_FILE):
        return [], set()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    projects = raw.get('projects', [])
    known_ids = {str(p['project_id']) for p in projects if p.get('project_id')}
    return projects, known_ids


def save_data(projects):
    """Save projects list to data.json with UTC timestamp."""
    now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    output = {
        'last_updated': now_utc,
        'projects': projects
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, separators=(',', ':'))
    log(f"Saved {len(projects)} projects to data.json")


def get_form_fields(soup):
    fields = {}
    for inp in soup.find_all('input', type='hidden'):
        name = inp.get('name')
        if name:
            fields[name] = inp.get('value', '')
    return fields


def parse_table(soup):
    rows = []
    table = soup.find('table', {'class': 'mGrid'})
    if not table:
        return rows
    for tr in table.find_all('tr')[1:]:
        tds = tr.find_all('td')
        if len(tds) < 8:
            continue
        project_id = None
        desc_link = tr.find('a', onclick=True)
        if desc_link:
            onclick = desc_link.get('onclick', '')
            if "showDesc('" in onclick:
                project_id = onclick.split("showDesc('")[1].split("'")[0]
        try:
            rows.append({
                'project_id': project_id,
                'name':        tds[1].get_text(strip=True),
                'company':     tds[2].get_text(strip=True),
                'national_id': tds[3].get_text(strip=True),
                'domain':      tds[4].get_text(strip=True),
                'status':      tds[5].get_text(strip=True),
                'start_date':  tds[6].get_text(strip=True),
                'end_date':    tds[7].get_text(strip=True),
            })
        except Exception as e:
            log(f"  Row parse error: {e}")
    return rows


def get_description(session, project_id):
    try:
        payload = json.dumps({'ID': str(project_id)})
        resp = session.post(DESC_URL, data=payload, headers=DESC_HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.json().get('d', '').strip()
    except Exception as e:
        log(f"  Description fetch error for {project_id}: {e}")
    return ''


def scrape_pages(session, known_ids, full_mode=False):
    """
    Scrape pages from ifb.ir.
    full_mode=True  → scrape all pages (first run)
    full_mode=False → stop as soon as we see 2 consecutive pages with no new IDs
    """
    new_rows = []
    MAX_PAGES = 300
    MAX_RETRIES = 4
    consecutive_known = 0
    STOP_AFTER_KNOWN = 2  # stop after 2 pages of all-known IDs

    log("  Page 1...")
    resp = session.get(BASE_URL, timeout=30)
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')
    rows = parse_table(soup)

    for row in rows:
        pid = row.get('project_id')
        if pid and pid not in known_ids:
            new_rows.append(row)

    log(f"    {len(rows)} rows, {len(new_rows)} new")
    form_fields = get_form_fields(soup)
    page_num = 2

    while page_num <= MAX_PAGES:
        log(f"  Page {page_num}...", )
        post_data = {
            **form_fields,
            '__EVENTTARGET':   GRID_ID,
            '__EVENTARGUMENT': f'Page${page_num}',
            '__ASYNCPOST':     'false'
        }

        resp = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = session.post(BASE_URL, data=post_data,
                                    headers=POST_HEADERS, timeout=30)
                resp.encoding = 'utf-8'
                break
            except Exception as e:
                wait = 5 * (attempt + 1)
                log(f"  Retry {attempt+1}/{MAX_RETRIES}: {e} — waiting {wait}s")
                time.sleep(wait)

        if resp is None:
            log(f"  Page {page_num} failed after {MAX_RETRIES} retries — skipping")
            page_num += 1
            time.sleep(3)
            continue

        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = parse_table(soup)

        new_on_page = 0
        for row in rows:
            pid = row.get('project_id')
            if pid and pid not in known_ids:
                new_rows.append(row)
                new_on_page += 1

        log(f"    {len(rows)} rows, {new_on_page} new (total new: {len(new_rows)})")

        if not full_mode:
            if new_on_page == 0:
                consecutive_known += 1
                if consecutive_known >= STOP_AFTER_KNOWN:
                    log("  All recent projects already known — stopping early")
                    break
            else:
                consecutive_known = 0

        form_fields = get_form_fields(soup)
        page_num += 1
        time.sleep(1)

    return new_rows


def fetch_descriptions(session, rows):
    """Fetch descriptions for rows that don't have one yet."""
    missing = [r for r in rows if not r.get('description')]
    if not missing:
        log("All projects already have descriptions.")
        return

    log(f"Fetching descriptions for {len(missing)} projects...")

    # Prime session cookies
    try:
        session.get(BASE_URL, timeout=30)
    except Exception as e:
        log(f"  Cookie prime error: {e}")

    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    saved = 0

    for i, row in enumerate(missing):
        pid = row.get('project_id')
        if not pid:
            continue
        log(f"  [{i+1}/{len(missing)}] Project {pid}...")
        desc = ''
        for attempt in range(3):
            desc = get_description(session, pid)
            if desc:
                break
            if attempt < 2:
                time.sleep(3)
        row['description'] = desc
        row['last_updated'] = now
        if desc:
            saved += 1
            log(f"    {len(desc)} chars")
        else:
            log(f"    Empty description")
        time.sleep(1.5)

    log(f"Descriptions saved: {saved}/{len(missing)}")


def run():
    log("=" * 50)
    log(f"IFB Scraper starting — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 50)

    existing_projects, known_ids = load_existing_data()
    full_mode = len(known_ids) == 0

    if full_mode:
        log("FULL MODE — no existing data found, scraping everything")
    else:
        log(f"INCREMENTAL MODE — {len(known_ids)} projects already known")

    session = requests.Session()
    session.headers.update(HEADERS)

    log("\nFetching pages...")
    new_rows = scrape_pages(session, known_ids, full_mode=full_mode)
    log(f"\nFound {len(new_rows)} new projects")

    if not new_rows:
        log("No new projects found. Updating timestamp and saving.")
        save_data(existing_projects)
        return

    # Stamp new projects with first_seen
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    for row in new_rows:
        row['first_seen'] = now
        row['last_updated'] = now
        row['is_new'] = 1
        row['description'] = row.get('description', '')

    # Fetch descriptions for new projects only
    log("\nFetching descriptions for new projects...")
    fetch_descriptions(session, new_rows)

    # Merge: new projects go to front
    all_projects = new_rows + existing_projects

    # Add project IDs of new ones to known set for dedup
    seen = set()
    deduped = []
    for p in all_projects:
        pid = str(p.get('project_id', ''))
        if pid and pid not in seen:
            seen.add(pid)
            deduped.append(p)

    save_data(deduped)

    log("\n" + "=" * 50)
    log(f"Done! {len(new_rows)} new projects added. Total: {len(deduped)}")
    log("=" * 50)


if __name__ == '__main__':
    run()
