# Islandora Advanced OAI-PMH Provider

A custom OAI-PMH interface for Islandora 7 (Drupal 7) repositories, designed to meet modern harvesting requirements like OpenAIRE v4.0 and Unpaywall.

## Features

*   **High Performance:** Uses direct Solr queries to bypass Drupal's internal overhead for `ListRecords` and `ListIdentifiers`.
*   **Hybrid Metadata Fetching:**
    *   Fetches descriptive metadata from Solr for speed.
    *   Fetches rights and file information from Fedora (RELS-INT/RELS-EXT) for precision.
*   **OpenAIRE v4.0 Compliance:**
    *   Supports `metadataPrefix=oai_openaire`.
    *   Maps funding information, DOIs, and resource types to the OpenAIRE schema.
    *   Handles "Access Rights" (Open Access, Embargoed, Restricted) based on file availability.
*   **Unpaywall Optimization:**
    *   Exposes direct links to PDF datastreams.
    *   Distinguishes between "Published Version" (VoR), "Accepted Manuscript" (AM), etc.
    *   Correctly handles embargo dates.
*   **MODS Support:**
    *   Supports `metadataPrefix=mods` to return the raw MODS XML datastream.
*   **Selective Harvesting:**
    *   Supports `from` and `until` date filtering (UTC).
    *   Supports `set` filtering based on collection membership.
*   **Security:**
    *   HMAC-signed `resumptionTokens` to prevent tampering.
    *   XXE protection.
    *   Admin impersonation for safe object loading.

## Installation

1.  Clone this module into your Drupal `sites/all/modules` directory.
2.  Enable the module via `drush en islandora_advanced_oai` or the admin interface.
3.  Configure the Solr connection in `islandora_advanced_oai.module` (constants at the top of the file):
    *   `ISLANDORA_ADVANCED_OAI_SOLR_URL`
    *   `ISLANDORA_ADVANCED_OAI_SOLR_CORE`

## Usage

The OAI-PMH endpoint is available at:
`http://your-site.com/advanced-oai`

### Supported Verbs

*   `Identify`: Returns repository information, including the OAI identifier scheme.
*   `ListMetadataFormats`: Lists supported formats. Supports the optional `identifier` argument to check formats for a specific item.
*   `ListRecords`: Lists records with metadata. Supports `from`, `until`, and `set` parameters.
*   `ListIdentifiers`: Lists record headers only. Supports `from`, `until`, and `set` parameters.
*   `GetRecord`: Retrieves a single record by identifier.
*   `ListSets`: Lists all collections in the repository as OAI sets.

### Supported Metadata Formats

*   **oai_dc**: Standard Dublin Core.
*   **oai_openaire**: OpenAIRE v4.0 compliant XML.
*   **mods**: Raw MODS XML from the object's datastream.

## Configuration

### Solr Mapping
The module uses a hardcoded mapping array in `_islandora_advanced_oai_handle_list_records` to map Solr fields to metadata elements. You may need to adjust these keys to match your GSearch `schema.xml`.

```php
$solr_map = array(
    'title'       => 'fgs_label_s',
    'creator'     => 'dc.creator',
    // ...
);
```

### Access Rights Logic
The module determines access rights by inspecting the `RELS-INT` datastream of the object. It looks for specific predicates (e.g., `lib4ridora-multi-embargo-availability`) to determine if a PDF is "public", "embargoed", or "restricted".

## Requirements

*   Islandora 7.x
*   PHP 5.3+
*   Solr 4+
