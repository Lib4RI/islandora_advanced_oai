# OAI2A - Advanced OAI-PMH Provider

A custom, high-performance OAI-PMH interface for Islandora 7 (Drupal 7) repositories, optimized for OpenAIRE v4.0 and Unpaywall compliance.

*   **Multi-Institute Support:** Provides separate, filtered entry points for **Eawag**, **Empa**, **WSL**, and **PSI**.
*   **High Performance:** Uses direct, raw Solr queries to bypass Drupal's internal overhead for large-scale harvesting (`ListRecords`, `ListIdentifiers`).
*   **Hybrid Metadata Fetching:**
    *   Fetches descriptive metadata from Solr for maximum speed.
    *   Fetches rights, licenses, and file versions from Fedora (`RELS-INT`/`RELS-EXT`) for precision.
*   **OpenAIRE v4.0 & QDC Compliance:**
    *   Full support for OpenAIRE metadata schema (`metadataPrefix=oai_openaire`).
    *   **New:** Support for Qualified Dublin Core (`metadataPrefix=oai_qdc`) using `dcterms`.
    *   Automatic mapping of funding info, DOIs, and Resource Types.
*   **Unpaywall & Open Access Optimization:**
    *   Exposes direct PDF datastream links.
    *   Detects and maps content versions (VoR, AM, etc.) and embargo dates.
*   **Security & Reliability:**
    *   **Institute-Bound Tokens:** HMAC-signed `resumptionTokens` are cryptographically tied to their specific institute endpoint.
    *   **XXE Protection:** Hardened against XML External Entity attacks.
    *   **Admin Impersonation:** Securely loads Fedora objects bypassing frontend access filters.
    *   **XML Escaping:** Strict escaping (`htmlspecialchars`) for all dynamically injected values in SimpleXML to prevent 500 Internal Server errors from unescaped characters.

## Installation

1.  Clone this module into your Drupal `sites/all/modules` directory.
2.  Enable the module: `drush en oai2a`
3.  Configure the Solr connection in `oai2a.module` (constants at the top):
    *   `oai2a_SOLR_URL`
    *   `oai2a_SOLR_CORE`
4.  **Rebuild Menu:** Trigger a Drupal menu rebuild (e.g., `drush cc menu`) to activate the institute paths.

## Usage

OAI2A provides four separate institute entry points:

- **Eawag:** `https://your-site.com/eawag/oai2a`
- **Empa:** `https://your-site.com/empa/oai2a`
- **WSL:** `https://your-site.com/wsl/oai2a`
- **PSI:** `https://your-site.com/psi/oai2a`

*Note: The legacy path `/oai2a` is also supported. While the `/institute/oai2a` paths filter records to a specific institute namespace, navigating to the generic `/oai2a` endpoint will return all records across the entire repository by default.*

### Supported Verbs

*   `Identify`: Returns repository information, including the specific institute name.
*   `ListMetadataFormats`: Lists supported formats (oai_dc, oai_openaire, oai_qdc, mods).
*   `ListRecords` / `ListIdentifiers`: Lists records filtered by the endpoint's institute namespace. Supports `from`, `until`, and `set` parameters.
*   `GetRecord`: Retrieves a single record (validated against the endpoint's institute).
*   `ListSets`: Lists collections belonging to the specific institute.

## Verification & Auditing (with Docker)

The easiest way to run the dashboard and auditing tools is via Docker:

1.  **Start Dashboard:** `docker-compose up -d`
2.  **Open Dashboard:** Navigate to `http://localhost:8080/oai_dashboard.html`.
3.  **Run Comparison Audit:** (Inside or outside the container) `python compare_oai.py` will update the shared `comparison_results.txt` file which the dashboard watches.

### Manual Setup (Without Docker)

1.  **Start Proxy Server:** `python serve_dashboard.py` (serves and proxies OAI requests).
2.  **Open Dashboard:** Navigate to `http://localhost:8080/oai_dashboard.html`.
3.  **Run Comparison Audit:** `python compare_oai.py` harvests every 20th record from legacy and modernized endpoints to generate a detailed diff report.

## Requirements

*   Islandora 7.x (Drupal 7)
*   PHP 5.6+ / 7.x
*   Solr 4.x or later
