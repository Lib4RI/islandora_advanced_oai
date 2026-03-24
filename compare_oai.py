#!/usr/bin/env python3
"""
OAI-PMH Endpoint Comparison Tool
================================
This script is designed to compare metadata records from two distinct OAI-PMH endpoints:
1. `oai2`  (The legacy Islandora endpoint)
2. `oai2a` (The modernized endpoint backed directly by Solr for ListRecords performance)

Key objectives for Code Review:
- Normalizes identifier disparities (e.g., 'oai:dora:eawag_19000' vs 'eawag:19000').
- Bypasses traditional page-by-page comparison due to different sorting mechanisms
  (oai2 sorts by fgs_lastModifiedDate desc, oai2a sorts by PID asc). Instead, it
  harvests a full batch (or subset) and compares the resulting dictionaries locally.
- Specifically ignores certain `dc:rights` values introduced in the new endpoint 
  (OpenAIRE/DRIVER compliance vocabulary) to prevent false-positive differences.
"""

import urllib.request
import urllib.error
import http.client
import xml.etree.ElementTree as ET
import sys
import time
import ssl
import random
import json
import os

# --- CONFIGURATION ---
BASE_DOMAIN = "https://www.dora-dev.lib4ri.ch"
INSTITUTES = ['eawag', 'empa', 'wsl', 'psi']
METADATA_PREFIX = "oai_dc"  # Primary format for regression testing

# Limiting Strategy:
# To speed up the process while maintaining a representative sample across the whole
# repository, we skip records (SKIP_FACTOR) and limit the total retained (MAX_RECORDS).
MAX_RECORDS = 300          # Max records to keep per endpoint
SKIP_FACTOR = 10           # Harvest every 10th record
OUTPUT_FILE = "comparison_results.txt"

# Standard OAI-PMH XML Namespaces used for XPath parsing
NS = {
    'oai': 'http://www.openarchives.org/OAI/2.0/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
}

# SSL Context: Bypassing certificate validation for the development/testing environment
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def normalize_pid(identifier):
    """
    Normalizes various identifier formats into a common base PID (e.g., 'eawag:19000').
    Since oai2 uses 'oai:dora:eawag_19000' and internal PIDs use 'eawag:19000', 
    this ensures we can match records across endpoints.
    """
    s = identifier.strip()
    if s.startswith('oai:'):
        parts = s.split(':')
        if len(parts) >= 3:
            raw = ':'.join(parts[2:]) # e.g. eawag_19000
            idx = raw.rfind('_')
            # Transform the last underscore back to a colon to reconstruct the Fedora PID
            if idx > 0:
                return raw[:idx] + ':' + raw[idx+1:]
            return raw
    if ':' in s and not s.startswith('oai:'):
        return s
    return s


def fetch_xml_with_retry(url, max_retries=5):
    """
    Fetches XML from a URL with exponential backoff for network resilience.
    """
    base_delay = 2
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'OAI-Compare/1.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=300) as resp:
                return ET.fromstring(resp.read())
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"    [Retry {attempt+1}/{max_retries}] Network error: {e}. Retrying in {delay:.1f}s...")
            time.sleep(delay)
    return None


def get_cache_path(cache_key):
    """Generated a hidden cache path for checkpointing."""
    return f".harvest_cache_{cache_key}.json"


def save_checkpoint(cache_key, records, token, counter):
    """Saves harvesting progress to a JSON file."""
    path = get_cache_path(cache_key)
    data = {
        'max_records': MAX_RECORDS,
        'skip_factor': SKIP_FACTOR,
        'metadata_prefix': METADATA_PREFIX,
        'token': token,
        'counter': counter,
        'records': records
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_checkpoint(cache_key):
    """Loads harvesting progress if valid settings match."""
    path = get_cache_path(cache_key)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Ensure cache is for the same settings
            if (data.get('max_records') == MAX_RECORDS and 
                data.get('skip_factor') == SKIP_FACTOR and 
                data.get('metadata_prefix') == METADATA_PREFIX):
                return data
        except Exception:
            return None
    return None


def harvest_records(base_url, cache_key, max_records=1000, skip_factor=1):
    """
    Harvests records with resumable checkpointing and retries.
    """
    # Try to resume from checkpoint
    checkpoint = load_checkpoint(cache_key)
    if checkpoint:
        records = checkpoint['records']
        counter = checkpoint['counter']
        token = checkpoint['token']
        if token:
            url = f"{base_url}?verb=ListRecords&resumptionToken={token}"
            print(f"    Resuming from token... ({len(records)} already kept)", flush=True)
        else:
            print(f"    Checkpoint shows harvest already complete.", flush=True)
            return records
    else:
        records = {}
        counter = 0
        url = f"{base_url}?verb=ListRecords&metadataPrefix={METADATA_PREFIX}"

    while url:
        # Optimization: Only save checkpoint every 10 pages to reduce I/O overhead
        page_count = (counter // 50) # Approx pages
        if page_count % 10 == 0:
            save_checkpoint(cache_key, records, url.split('resumptionToken=')[-1] if 'resumptionToken=' in url else None, counter)

        print(f"    Harvesting... ({len(records)} kept, {counter} seen)", flush=True)
        try:
            root = fetch_xml_with_retry(url)
            if root is None: break
        except Exception as e:
            print(f"    CRITICAL ERROR: {e}")
            break

        # Check for OAI-PMH level errors
        error = root.find('.//oai:error', NS)
        if error is not None:
            print(f"    OAI Error: {error.get('code')} - {error.text}")
            break

        # Parse records
        for record in root.findall('.//oai:record', NS):
            counter += 1
            if skip_factor > 1 and (counter % skip_factor) != 0:
                continue

            header = record.find('oai:header', NS)
            if header is None: continue
            
            raw_id = header.find('oai:identifier', NS)
            if raw_id is None or not raw_id.text: continue

            pid = normalize_pid(raw_id.text)
            sets = [s.text.strip() for s in header.findall('oai:setSpec', NS) if s.text]

            dc_fields = {}
            dc = record.find('.//oai_dc:dc', NS)
            if dc is not None:
                for child in dc:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    val = (child.text or '').strip()
                    if val:
                        if tag not in dc_fields: dc_fields[tag] = []
                        dc_fields[tag].append(val)

            records[pid] = {'raw_id': raw_id.text.strip(), 'sets': sorted(sets), 'fields': dc_fields}

        if max_records and len(records) >= max_records:
            save_checkpoint(cache_key, records, None, counter) # Mark as done (no token)
            break

        # Handle Pagination
        token_elem = root.find('.//oai:resumptionToken', NS)
        token = token_elem.text.strip() if token_elem is not None and token_elem.text else None
        
        # Save progress before moving to next page
        save_checkpoint(cache_key, records, token, counter)

        if token:
            url = f"{base_url}?verb=ListRecords&resumptionToken={token}"
            time.sleep(0.1) # Faster rate
        else:
            url = None

    return records


def filter_ignored_values(values):
    """
    Removes the DRIVER/OpenAIRE access rights vocabulary (`info:eu-repo/*`) and 'Text'
    from the list of values before comparison.
    """
    return [v for v in values if not str(v).startswith('info:eu-repo/') and v != 'Text']


def compare(old_recs, new_recs):
    """
    Compares two mapped dictionaries of harvested records.
    Returns categorized results (missing records, differences) and field-level variance stats.
    """
    all_pids = sorted(set(list(old_recs.keys()) + list(new_recs.keys())))

    results = {
        'only_old': [],
        'only_new': [],
        'identical': [],
        'different': [],
    }
    field_diff_counts = {}

    for pid in all_pids:
        # 1. Identify records present in one endpoint but not the other
        if pid not in new_recs:
            results['only_old'].append(pid)
            continue
        if pid not in old_recs:
            results['only_new'].append(pid)
            continue

        old = old_recs[pid]
        new = new_recs[pid]
        diffs = []

        # 2. Compare OAI Sets (Collections)
        if old['sets'] != new['sets']:
            diffs.append(('setSpec', old['sets'], new['sets']))
            field_diff_counts['setSpec'] = field_diff_counts.get('setSpec', 0) + 1

        # 3. Compare generic Dublin Core fields
        all_keys = sorted(set(list(old['fields'].keys()) + list(new['fields'].keys())))
        for key in all_keys:
            old_vals = sorted(old['fields'].get(key, []))
            new_vals = sorted(new['fields'].get(key, []))

            # Apply exceptions (e.g. EU-Repo rights and type vocabulary)
            if key in ('rights', 'type'):
                old_vals = sorted(filter_ignored_values(old_vals))
                new_vals = sorted(filter_ignored_values(new_vals))

            # If arrays mismatches, record the specific difference
            if old_vals != new_vals:
                diffs.append((f'dc:{key}', old_vals, new_vals))
                field_diff_counts[f'dc:{key}'] = field_diff_counts.get(f'dc:{key}', 0) + 1

        if diffs:
            results['different'].append((pid, diffs))
        else:
            results['identical'].append(pid)

    return results, field_diff_counts


def run_comparison(f, institute):
    """
    Orchestrator for a single institute's comparison workflow.
    Executes harvests, triggers comparison, and formats output.
    """
    old_url = f"{BASE_DOMAIN}/{institute}/oai2"
    new_url = f"{BASE_DOMAIN}/{institute}/oai2a"

    f.write("\n" + "#" * 70 + "\n")
    f.write(f"# INSTITUTE: {institute.upper()}\n")
    f.write(f"# OLD: {old_url}\n")
    f.write(f"# NEW: {new_url}\n")
    f.write("#" * 70 + "\n")

    print(f"\n{'='*50}")
    print(f"  Institute: {institute.upper()}")
    print(f"{'='*50}")

    print(f"  [1/3] Harvesting from OLD ({institute}/oai2)...")
    old_recs = harvest_records(old_url, f"{institute}_old", MAX_RECORDS, SKIP_FACTOR)
    print(f"    => {len(old_recs)} records")

    print(f"  [2/3] Harvesting from NEW ({institute}/oai2a)...")
    new_recs = harvest_records(new_url, f"{institute}_new", MAX_RECORDS, SKIP_FACTOR)
    print(f"    => {len(new_recs)} records")

    print(f"  [3/3] Comparing...")
    results, field_diff_counts = compare(old_recs, new_recs)

    # Output Summary Metrics
    f.write(f"\nSUMMARY ({institute.upper()}):\n")
    f.write(f"  OLD records:     {len(old_recs)}\n")
    f.write(f"  NEW records:     {len(new_recs)}\n")
    f.write(f"  Identical:       {len(results['identical'])}\n")
    f.write(f"  Different:       {len(results['different'])}\n")
    f.write(f"  Only in OLD:     {len(results['only_old'])}\n")
    f.write(f"  Only in NEW:     {len(results['only_new'])}\n")

    print(f"  Identical: {len(results['identical'])}, Different: {len(results['different'])}, "
          f"Only OLD: {len(results['only_old'])}, Only NEW: {len(results['only_new'])}")

    if results['only_old']:
        f.write(f"\n  PIDs only in OLD ({len(results['only_old'])}): {results['only_old'][:20]}\n")
    if results['only_new']:
        f.write(f"\n  PIDs only in NEW ({len(results['only_new'])}): {results['only_new'][:20]}\n")

    if field_diff_counts:
        f.write(f"\nFIELD DIFFERENCES ({institute.upper()}):\n")
        for field, count in sorted(field_diff_counts.items(), key=lambda x: -x[1]):
            pct = count / max(len(results['different']), 1) * 100
            bar = "#" * min(int(pct / 2), 35)
            f.write(f"  {field:25s}  {count:5d} records  ({pct:5.1f}%)  {bar}\n")

    # Output Detailed Diffs
    if results['different']:
        f.write(f"\nDETAILED DIFFERENCES ({institute.upper()}) - ALL {len(results['different'])} records:\n")
        f.write("-" * 70 + "\n")
        for pid, diffs in results['different']:
            f.write(f"\n  PID: {pid}\n")
            for field, old_vals, new_vals in diffs:
                old_str = '; '.join(old_vals)[:200]
                new_str = '; '.join(new_vals)[:200]
                if not old_vals:
                    f.write(f"    {field}: MISSING in OLD, NEW has: {new_str}\n")
                elif not new_vals:
                    f.write(f"    {field}: OLD has: {old_str}, MISSING in NEW\n")
                else:
                    f.write(f"    {field}:\n")
                    f.write(f"      OLD: {old_str}\n")
                    f.write(f"      NEW: {new_str}\n")

    # Clean up cache files if we reached here successfully
    for key in [f"{institute}_old", f"{institute}_new"]:
        path = get_cache_path(key)
        if os.path.exists(path):
            os.remove(path)

    return results, field_diff_counts


def main():
    print("=" * 70)
    print("OAI-PMH Endpoint Comparison (All Institutes)")
    print(f"Institutes: {', '.join(INSTITUTES)}")
    print(f"Every {SKIP_FACTOR}th record, max {MAX_RECORDS} per endpoint")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Note: dc:rights and dc:type info:eu-repo/* and 'Text' values are excluded from comparison")
    print("=" * 70)

    grand_totals = {'identical': 0, 'different': 0, 'only_old': 0, 'only_new': 0}
    grand_field_diffs = {}

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("OAI-PMH Endpoint Comparison Report\n")
        f.write(f"Institutes: {', '.join(INSTITUTES)}\n")
        f.write(f"Every {SKIP_FACTOR}th record, max {MAX_RECORDS} per endpoint\n")
        f.write(f"Format: {METADATA_PREFIX}\n")
        f.write(f"Note: dc:rights and dc:type info:eu-repo/* and 'Text' values excluded\n")
        f.write("=" * 70 + "\n")

        # Iterate all institutional repos
        for institute in INSTITUTES:
            results, field_diffs = run_comparison(f, institute)
            grand_totals['identical'] += len(results['identical'])
            grand_totals['different'] += len(results['different'])
            grand_totals['only_old'] += len(results['only_old'])
            grand_totals['only_new'] += len(results['only_new'])
            for field, count in field_diffs.items():
                grand_field_diffs[field] = grand_field_diffs.get(field, 0) + count

        # Grand summary across all institutions
        f.write("\n\n" + "=" * 70 + "\n")
        f.write("GRAND TOTAL (ALL INSTITUTES)\n")
        f.write("=" * 70 + "\n")
        f.write(f"  Identical:       {grand_totals['identical']}\n")
        f.write(f"  Different:       {grand_totals['different']}\n")
        f.write(f"  Only in OLD:     {grand_totals['only_old']}\n")
        f.write(f"  Only in NEW:     {grand_totals['only_new']}\n")

        if grand_field_diffs:
            f.write(f"\nGRAND FIELD DIFFERENCES:\n")
            for field, count in sorted(grand_field_diffs.items(), key=lambda x: -x[1]):
                f.write(f"  {field:25s}  {count:5d} records\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("Comparison complete.\n")

    print(f"\n{'='*70}")
    print("GRAND TOTAL:")
    print(f"  Identical: {grand_totals['identical']}, Different: {grand_totals['different']}")
    print(f"  Only OLD: {grand_totals['only_old']}, Only NEW: {grand_totals['only_new']}")
    print(f"\nFull results written to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
