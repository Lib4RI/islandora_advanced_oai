Islandora Advanced OAI-PMH Provider
A high-performance, compliant, and robust OAI-PMH interface for Islandora 7 (Drupal 7) repositories.
This module was designed to overcome specific limitations of the standard Islandora OAI provider regarding performance, access rights calculation (Unpaywall/Open Access), and OpenAIRE v4.0 compliance.
Table of Contents
* Key Features
* Architecture
* Installation
* Configuration
* Usage
* Troubleshooting
* License
Key Features
1. Hybrid Data Fetching (Performance & Precision)
Standard OAI providers often struggle with the trade-off between speed (Solr) and data accuracy (Fedora). This module uses a hybrid approach:
* Metadata (Speed): Static fields like Title, Creator, Date, Publisher, and Descriptions are fetched directly from the Solr Index. This avoids parsing huge MODS XML files for thousands of records, resulting in significantly lower CPU usage.
* Access Rights (Precision): Complex logic regarding Open Access status, Embargoes, and Versioning (Submitted vs. Accepted vs. Published) is calculated in real-time by inspecting the Fedora Object (RELS-INT, RELS-EXT). This ensures Unpaywall always gets the correct link to the open full-text version.
2. Direct Solr HTTP Mode
To bypass potential internal filtering issues where Drupal's IslandoraSolrQueryProcessor might return 0 results due to strict XACML policies for anonymous users, this module implements a Direct HTTP Solr Client.
* It sends raw queries directly to the Solr core (e.g., http://localhost:8080/solr).
* It uses specific Filter Queries (fq) to target content models (e.g., ir:citationCModel).
3. Unpaywall & Open Access Optimization
* Smart Versioning: Automatically detects multiple PDF datastreams (PDF, PDF2...). It prioritizes the Published Version but falls back to the Accepted Manuscript if the former is restricted and the latter is open.
* Direct Links: Exposes the direct download URL of the specific open datastream in dc:identifier (Dublin Core) and datacite:identifier (OpenAIRE), allowing Unpaywall to index the full text.
* Embargo Handling: Calculates whether an embargo date has passed based on the server time and RELS-INT metadata.
4. OpenAIRE v4.0 Compliance
* Full support for OpenAIRE Guidelines v4.0.
* Maps internal vocabularies to COAR resource types (e.g., journal article, thesis, book part).
* Exports funding references and project information.
* Includes rightsList with specific URIs for access rights and licenses (CC BY, etc.).
5. Security & Robustness
* HMAC Signed Tokens: resumptionTokens are signed using the site's private key to prevent tampering or DoS attacks via offset manipulation.
* Admin Impersonation: The OAI endpoint temporarily switches to the super-user (User 1) context during read-only operations to ensure all metadata can be read from Fedora, regardless of anonymous user restrictions.
* XXE Protection: XML entity loaders are explicitly disabled to prevent injection attacks.
* Stale Cache Prevention: Error responses (e.g., "No records match") are never cached to facilitate easier debugging.
Installation
1. Clone this repository into your Drupal modules directory:
cd /var/www/html/sites/all/modules
git clone [https://github.com/YOUR_ORG/islandora_advanced_oai.git](https://github.com/YOUR_ORG/islandora_advanced_oai.git)

2. Enable the module:
drush en islandora_advanced_oai

Configuration
1. Solr Connection
Open the .module file and locate the configuration constant at the top. You must define the internal URL to your Solr core. This allows the module to bypass internal Drupal filters.
// e.g., inside islandora_advanced_oai.module
define('EAWAG_OAI17_SOLR_URL', 'http://localhost:8080/solr');
define('EAWAG_OAI17_SOLR_CORE', 'collection1');

2. Solr Field Mapping
In the function _handle_list_records, check the $solr_map array. Ensure the Solr fields match your GSearch configuration (e.g., MODS_abstract_ms vs dc.description).
$solr_map = array(
   'title'       => 'fgs_label_s',
   'creator'     => 'dc.creator', // or MODS_name_personal_namePart_ms
   'date'        => 'MODS_originInfo_dateIssued_s',
   // ...
);

Usage
The OAI endpoint is available at:
https://your-repository.org/eawag-oai17
Examples
   * Identify:
?verb=Identify
   * List Records (Dublin Core):
?verb=ListRecords&metadataPrefix=oai_dc
   * List Records (OpenAIRE):
?verb=ListRecords&metadataPrefix=oai_openaire
   * Get Record:
?verb=GetRecord&identifier=eawag:12345&metadataPrefix=oai_dc
Troubleshooting
"noRecordsMatch" Error
If you receive this error even though your repository has content:
      1. Check the EAWAG_OAI17_SOLR_URL setting. The server must be able to reach Solr via HTTP/cURL.
      2. Check the query filter in the code: RELS_EXT_hasModel_uri_ms:"info:fedora/ir:citationCModel". Does your repository use a different content model URI?
      3. Clear the Drupal cache (drush cc all) to ensure no old error responses are served.
Missing Metadata Fields
If fields like "Publisher" or "Description" are missing in ListRecords:
      * Verify the field names in your Solr index using the Solr Admin UI.
      * Update the $solr_map array in the module code to match your specific index schema.
License
GPLv2 or later.
