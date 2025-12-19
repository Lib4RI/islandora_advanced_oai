Islandora Advanced OAI-PMH Provider

A custom OAI-PMH interface for Islandora 7 (Drupal 7) repositories, designed to meet modern harvesting requirements for OpenAIRE v4.0 and Unpaywall.

Features

This module provides an alternative OAI endpoint (parallel to the default Islandora OAI) with specific enhancements for institutional repositories:

OpenAIRE v4.0 Compliance:

Maps internal MODS metadata to the OpenAIRE schema.

Handles mandatory fields like resourceType, licenseCondition, and publicationYear.

Exports funding information (funder roles and project notes).

Unpaywall Optimization:

Direct PDF Linking: Explicitly exposes the URL to the full-text datastream in dc:identifier and oai:identifier.

Smart Versioning: Distinguishes between Submitted, Accepted, and Published versions based on RELS-INT metadata.

Embargo Handling: Calculates embargo end dates and sets access rights accordingly (open vs. embargoed vs. restricted).

Robust Backend:

SPARQL over Solr: Uses direct SPARQL queries against the Fedora Resource Index (RI) to fetch object lists. This avoids common issues with Solr indexing lag or permission filters.

Secure Admin Impersonation: Temporarily switches to User 1 permissions during read-only operations to ensure metadata is harvested correctly, even if XACML policies restrict anonymous access to the Fedora object.

Reliable Paging: Implements resumptionToken logic that works even if the triple store does not support COUNT aggregations correctly.

Requirements

Drupal 7

Islandora 7.x

Tuque (Islandora's PHP library for Fedora Commons)

Installation

Clone this repository into your modules directory:

cd /var/www/html/sites/all/modules
git clone [https://github.com/YOUR_ORG/islandora_advanced_oai.git](https://github.com/YOUR_ORG/islandora_advanced_oai.git)


Enable the module via Drush or the Admin Interface:

drush en islandora_advanced_oai


Clear the Drupal cache.

Usage

The OAI-PMH endpoint is available at:
https://your-repository.org/advanced-oai

Supported Verbs

Identify: Returns repository information and a connection check to the Fedora RI.

ListMetadataFormats: Supported prefixes are oai_dc and oai_openaire.

ListRecords: Iterates through all objects with a citation content model.

GetRecord: Fetches a single record by PID.

Examples

OpenAIRE Format: ?verb=ListRecords&metadataPrefix=oai_openaire

Dublin Core: ?verb=GetRecord&identifier=eawag:1234&metadataPrefix=oai_dc

How it works

Access Rights Logic

The module inspects the RELS-INT datastream of an object to find PDF datastreams. It evaluates:

Availability: Is the file marked as public?

Embargo: Is there an embargo date, and has it passed?

Version: If multiple public files exist, it prioritizes the Published Version over the Accepted Manuscript.

Security

XXE Protection: XML entity loaders are disabled during parsing to prevent injection attacks.

Error Masking: Detailed SPARQL/Fedora exceptions are logged to the Drupal Watchdog but hidden from the public XML output.

License

GPLv2 or later.
