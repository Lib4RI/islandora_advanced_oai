# OAI2A System Architecture

This higher-level diagram simplifies how the newly optimized `oai2a` endpoint interacts with Drupal, Solr, and Fedora to serve metadata efficiently.

## Core Flow (Fast vs. Fallback)

The core optimization relies on short-circuiting expensive Fedora API calls whenever possible, serving batches of metadata directly from Solr search indexes ("The Fast Path").

```mermaid
graph TD
    User([OAI Harvester]) -->|HTTP Request| Router[Drupal: oai2a.module]
    
    %% Setup & Validation
    Router --> Valid{Token & Institute Valid?}
    Valid -->|No| Err[Return OAI Error]
    
    %% Cache Check
    Valid -->|Yes| Cache{Is Request Cached?}
    Cache -->|Yes| Return([Return Cached XML])
    
    %% Route by Verb
    Cache -->|No| Verb{Which OAI Verb?}
    
    %% THE FAST PATH (Solr)
    Verb -->|ListRecords / ListIdentifiers| FastPath[Fast Path: Direct Solr Query]
    FastPath --> Solr[(Solr Search Index)]
    Solr -.-> Mapper[Map Solr fields to OAI-DC XML]
    
    %% THE FALLBACK PATH (Fedora)
    Verb -->|GetRecord| SlowPath[Fallback Path: Load Object via Islandora API]
    SlowPath --> Fedora[(Fedora Data Repo)]
    Fedora -.-> Parser[Parse MODS & RELS-EXT Datastreams]
    
    %% Merge and output
    Mapper --> Builder[Combine into OAI-PMH XML Document]
    Parser --> Builder
    
    %% Finalize
    Builder --> Save[Save to Drupal Cache]
    Save --> Return
    
    %% Visual Styling
    classDef primary fill:#e3f2fd,stroke:#1565c0,stroke-width:2px;
    classDef secondary fill:#ffebee,stroke:#c62828,stroke-width:2px;
    classDef logic fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef database fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef endnode fill:#e0e0e0,stroke:#616161,stroke-width:2px;
    
    class FastPath,Mapper primary;
    class SlowPath,Parser secondary;
    class Valid,Cache,Verb logic;
    class Solr,Fedora database;
    class User,Return endnode;
```

## Why is it faster?
In the legacy (`oai2`) architecture, fetching 1,000 records required **1,000 separate calls to Fedora**. 
In the modern (`oai2a`) architecture, fetching 1,000 records requires just **1 call to Solr**, mapping the response payload instantly in memory.
