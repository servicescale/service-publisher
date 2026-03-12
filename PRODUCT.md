# Demand-Driven Content Publishing Engine

You are a coding agent tasked with building a demand-driven content publishing engine.
Your role is to implement the system described below without redesigning its core concepts.

This prompt defines the complete system scope, domain model, relationships, and functional capabilities.
It intentionally avoids prescribing frameworks, database schemas, or file structures.

Your responsibility is to implement the system faithfully.

---

SYSTEM PURPOSE

Build an engine capable of launching and operating niche content sites that automatically:

- detect demand
- identify content gaps
- generate targeted content
- publish content automatically
- attract search traffic
- direct users to monetised products (e.g. affiliate links)
- analyse performance signals
- improve strategy continuously

The system should enable many niche sites to run using the same core engine.

---

CORE OPERATING LOOP

The system continuously runs the following loop for each site:

Demand Detection
-> Gap Analysis
-> Cluster Planning
-> Atom Creation
-> Content Generation
-> Publishing
-> Signal Collection
-> Insight Generation
-> Strategy Refinement

Nothing should break or bypass this loop.

Every capability in the system must map to one or more stages in this loop.

The loop must be able to run repeatedly without corrupting state or duplicating work unintentionally.

---

CORE DOMAIN MODEL

The system vocabulary must remain consistent.

Site
Cluster
Atom
Output
Signal
Insight

These terms form the ubiquitous language of the system.

No replacement planning abstraction should be introduced that weakens or replaces Atom as the core planning unit.

---

SITE

A Site represents a niche publishing business.

Examples might include:

- a LEGO product guide site
- a kids lunch ideas site
- a camping gear review site

A site defines:

- niche focus
- target audience
- brand tone
- monetisation strategy
- publishing channels

A site owns:

- clusters
- atoms
- outputs
- signals
- insights

Clusters never cross sites.

Sites operate independently.

Each site should be able to run with its own isolated data storage.

No content, signals, or insights from one site should leak into another site unless explicitly implemented as a separate cross-site analysis feature. Cross-site analysis is not part of the core system definition.

---

CLUSTER

A Cluster is a strategic topic area inside a site.

Clusters organise the subject areas a site covers and represent families of related search intent.

Example clusters for a LEGO site might include:

- best LEGO sets
- LEGO storage ideas
- LEGO display ideas
- LEGO gift guides
- retired LEGO sets

Clusters help establish topical authority.

Clusters group related atoms.

Clusters belong to exactly one site.

Clusters should be expandable over time as new demand and insights are discovered.

---

ATOM

An Atom represents a single content opportunity.

Atoms are the core planning unit of the system.

An atom typically represents a keyword topic or specific search intent.

Examples:

- best lego sets for adults
- best lego sets under $100
- nut free lunchbox ideas
- high protein school lunches

Atoms belong to a single cluster.

Atoms drive the creation of outputs.

Atoms should contain enough context to generate useful content.

Atoms form the execution backlog for content creation and should be prioritised based on demand, strategic relevance, and insight feedback.

Atoms should be traceable to the demand, gaps, or insights that caused them to exist.

---

OUTPUT

Outputs are the concrete pieces of content published to channels.

Outputs are derived from atoms.

Examples include:

- articles
- buying guides
- product comparison pages
- curated recommendation lists
- social media posts
- Pinterest pins
- email snippets

Multiple outputs can be generated from a single atom.

Outputs are the content assets that attract traffic and generate engagement.

Outputs should retain a clear relationship to both the source atom and the publishing channel.

---

SIGNAL

Signals represent measurable performance data.

Signals attach to outputs.

Signals may represent metrics such as:

- impressions
- clicks
- search ranking visibility
- engagement
- affiliate link clicks
- affiliate revenue

Signals are used to evaluate the effectiveness of content.

Signals should accumulate over time for outputs and should also be aggregatable upward to atoms, clusters, and sites.

Signals must be timestamped or otherwise temporally attributable so the system can evaluate change over time.

---

INSIGHT

Insights are conclusions derived from signals.

Insights inform future planning.

Examples might include:

- expand a high-performing cluster
- create additional atoms within a successful topic
- deprioritise underperforming topics

Insights influence the next cycle of the system loop.

Insights should be explainable and traceable to the signals or signal patterns that generated them.

---

DOMAIN RELATIONSHIPS

Site
-> contains Clusters

Cluster
-> contains Atoms

Atom
-> produces Outputs

Output
-> generates Signals

Signals
-> inform Insights

Insights
-> influence future Atoms and Clusters

These relationships must remain consistent across the system.

The system must preserve lineage from demand inputs through to insights so decisions can be audited.

---

FUNCTIONAL CAPABILITIES

The system must support the following functional areas.

---

DEMAND DETECTION

The system must be able to identify audience demand.

Demand signals may come from sources such as:

- keyword datasets
- search trends
- competitor analysis
- topical research

Demand detection produces opportunity signals that indicate where content could attract traffic.

Demand detection should preserve the source and confidence of any discovered opportunity where possible.

---

GAP ANALYSIS

The system must analyse where demand exists but content coverage is weak or incomplete.

Gap analysis identifies areas where new content could perform well.

Outputs from gap analysis should feed cluster planning.

Gap analysis should operate at least at the site and cluster level, and should be able to identify missing atoms within promising clusters.

---

CLUSTER PLANNING

Based on detected demand and gaps, the system should organise topics into clusters.

Clusters represent strategic coverage areas for a site.

Clusters should expand over time as new opportunities are discovered.

Cluster planning must remain site-scoped.

---

ATOM GENERATION

Within each cluster, the system should generate atoms.

Atoms represent individual content opportunities.

Atoms should be prioritised based on demand and strategic importance.

Atoms form the backlog for content creation.

Atom generation should avoid producing semantically duplicate atoms unless duplication is explicitly intentional and justified by strategy.

---

CONTENT GENERATION

The system must generate content outputs from atoms.

Content should aim to:

- satisfy search intent
- provide useful information
- guide users toward relevant products

Outputs may include:

- long-form articles
- product comparisons
- recommendation lists
- curated guides

The goal of content generation is to attract traffic and support monetisation.

Content generation should preserve enough metadata to explain which atom, cluster, site, and monetisation strategy shaped the output.

---

PUBLISHING

The system must be capable of publishing outputs to configured channels.

Possible channels include:

- website CMS
- social platforms
- Pinterest
- newsletters

Publishing should allow outputs to become discoverable by audiences.

Publishing should be idempotent where practical so retries do not create accidental duplicate outputs.

---

MONETISATION

Content should guide readers toward relevant products or services.

Typical monetisation methods include:

- affiliate product links
- product comparison tables
- buying guides
- curated product lists

The system should make it possible for content to convert audience interest into revenue.

Monetisation mechanisms must remain subordinate to user usefulness and search-intent satisfaction.

---

SIGNAL COLLECTION

After publishing, the system must capture performance signals.

Signals allow the system to evaluate how content performs.

Signals should accumulate over time for outputs, atoms, and clusters.

Signal collection should support repeated ingestion over time and must not assume a single snapshot is sufficient.

---

INSIGHT GENERATION

The system must analyse signals to produce insights.

Insights may identify:

- clusters that deserve expansion
- atoms that should be replicated or extended
- topics that perform poorly

Insights should guide future strategy.

Insight generation should be able to compare relative performance across outputs, atoms, and clusters within a site.

---

STRATEGY REFINEMENT

Insights feed back into planning.

Clusters may grow or shrink.

New atoms may be created.

Content priorities may change.

This closes the system loop.

Strategy refinement must result in updated planning state, not just passive reporting.

---

MULTI-SITE OPERATION

The engine must support multiple independent sites.

Each site may target a different niche.

Examples:

- LEGO products
- lunch ideas
- outdoor gear
- coffee equipment

Sites share the same engine but operate independently.

Clusters remain site-scoped.

The engine should be able to run the loop for one site without requiring other sites to run at the same time.

---

ARCHITECTURAL CONSTRAINTS

The system must follow these principles:

- the planning unit is the Atom
- articles are outputs, not planning objects
- clusters are site-scoped
- sites operate independently
- signals and insights must feed back into planning
- the system loop must remain intact

The engine should remain flexible enough to support many niche sites.

The implementation must make state transitions explicit enough that the progress of each atom and output through the loop can be understood and audited.

---

IMPLEMENTATION OBJECTIVE

Implement a system capable of:

1. running the publishing loop continuously
2. discovering new content opportunities
3. generating useful content
4. publishing content automatically
5. learning from performance signals
6. expanding successful topic coverage

The end result should be a scalable engine capable of operating multiple niche content sites that attract traffic and generate product-driven revenue.

---

DELIVERY INTENT

This document is the canonical product roadmap and system vision for the repository.

Future implementation work should align to this system definition unless explicitly superseded by the user.

End of system definition.
