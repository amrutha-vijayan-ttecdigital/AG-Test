# Official GCP Icons

When a diagram's components are Google Cloud products, put the official product icon inside each GCP component box. This makes the diagram instantly readable to anyone who works with GCP — the BigQuery hexagon or Cloud Run wheel is recognized faster than any text label. Non-GCP components (clients, third-party systems, on-prem) get no icon; the contrast itself carries information.

The bundled set (`assets/gcp-icons/`) is Google's **2025 official icon system**: 19 unique core-product icons plus 26 category icons. Google deliberately no longer publishes per-product icons for most services — a product without a unique icon gets its **category** icon. That is official guidance, not a workaround, so don't hunt for a "real" Pub/Sub icon online; use `cat-integration-services`.

## How to embed (important — this is where diagrams die)

Two failure modes make hand-embedding icons a trap. First, the official icon SVGs define internal CSS classes (`.st0`, `.st1`, …), so inlining two icons' markup into one diagram makes the classes collide and colors render wrong. Second — and worse — the base64 data URIs are 2–6 KB of opaque text; writing or copying strings that long by hand reliably truncates or splices them, which breaks the XML and the **entire diagram renders as nothing**.

So never write icon markup or base64 yourself, at any point, including when fixing an existing file. Where an icon belongs, write a short placeholder comment:

```
<!-- gcp-icon: vertex-ai 987 214 36 -->     ← name, x, y, size(optional, default 36)
```

Then expand all placeholders in one shot — the script also validates every data URI and the XML, and refuses to write a broken file:

```bash
python scripts/gcp_icon.py --list                 # available icon names
python scripts/gcp_icon.py --inject diagram.svg   # placeholders → <image> elements
python scripts/gcp_icon.py --check diagram.svg    # validate without writing
```

Run `--inject` before every render; it's idempotent. If a render ever fails with an XML parse error near an `<image>`, don't repair the base64 in place — replace the whole `<image>` element with a fresh placeholder and re-run `--inject`.

## Placement inside a component box

- Icon size 36px (32px in nested boxes), placed at the top-left of the box content area: `x = box.x + 20`, `y = box.y + 16`.
- Shift the text block right so it clears the icon: name and descriptor lines start at `x = box.x + 68` (instead of the usual 22px inset). Budget line widths against the reduced text area.
- Keep the zone-colored accent bar; icon sits right of it.
- Vertically, the component name baseline aligns roughly with the icon's center: name baseline ≈ `box.y + 32` still works for a 36px icon at `y + 16` on a standard-height box.
- Zones don't get icons — they're groupings, not products. Exception: a small 28px icon next to a zone label is acceptable when the zone *is* a product (e.g. a "GKE CLUSTER" zone).

## Core product icons (unique, prefer these)

| Icon name | Product |
|---|---|
| `ai-hypercomputer` | AI Hypercomputer |
| `alloydb` | AlloyDB |
| `anthos` | Anthos |
| `apigee` | Apigee |
| `bigquery` | BigQuery |
| `cloud-run` | Cloud Run |
| `cloud-sql` | Cloud SQL |
| `cloud-spanner` | Cloud Spanner |
| `cloud-storage` | Cloud Storage (GCS) |
| `compute-engine` | Compute Engine (GCE) |
| `distributed-cloud` | Google Distributed Cloud |
| `gke` | Google Kubernetes Engine |
| `hyperdisk` | Hyperdisk / persistent disk |
| `looker` | Looker |
| `mandiant` | Mandiant |
| `security-command-center` | Security Command Center |
| `security-operations` | Security Operations (Chronicle SecOps) |
| `threat-intelligence` | Threat Intelligence |
| `vertex-ai` | Vertex AI (incl. Gemini API on Vertex, Agent Builder, pipelines) |

## Category icons (fallback for everything else)

`cat-agents`, `cat-ai-machine-learning`, `cat-business-intelligence`, `cat-collaboration`, `cat-compute`, `cat-containers`, `cat-data-analytics`, `cat-databases`, `cat-developer-tools`, `cat-devops`, `cat-hybrid-multicloud`, `cat-integration-services`, `cat-management-tools`, `cat-maps-geospatial`, `cat-marketplace`, `cat-media-services`, `cat-migration`, `cat-mixed-reality`, `cat-networking`, `cat-observability`, `cat-operations`, `cat-security-identity`, `cat-serverless-computing`, `cat-storage`, `cat-web-mobile`, `cat-web3`

Common products → category icon:

| Product(s) | Icon |
|---|---|
| Pub/Sub, Eventarc, Cloud Tasks, Cloud Scheduler, Workflows, Application Integration | `cat-integration-services` |
| Dataflow, Dataproc, Composer, Data Fusion, Datastream, Analytics Hub | `cat-data-analytics` |
| Cloud Functions / Cloud Run functions, App Engine | `cat-serverless-computing` |
| Firestore, Bigtable, Memorystore, Datastore | `cat-databases` |
| VPC, Load Balancing, Cloud CDN, Cloud DNS, Cloud NAT, Interconnect, Cloud Armor (edge/WAF) | `cat-networking` |
| IAM, Secret Manager, Cloud KMS, Certificate Authority Service, Identity Platform | `cat-security-identity` |
| Cloud Logging, Cloud Monitoring, Cloud Trace, Error Reporting | `cat-observability` |
| Cloud Build, Artifact Registry, Cloud Deploy | `cat-devops` |
| Cloud Workstations, Cloud Shell, Cloud Code, Cloud SDK | `cat-developer-tools` |
| Filestore, Backup and DR, Storage Transfer Service | `cat-storage` |
| Batch, sole-tenant nodes, TPUs/GPUs (as compute) | `cat-compute` |
| Gemini models / AI APIs not on Vertex (Speech, Vision, Translation) | `cat-ai-machine-learning` |
| Agentspace, agent runtimes | `cat-agents` |
| Cloud console, Resource Manager, Deployment Manager | `cat-management-tools` |

If a product fits none of these, pick the category a GCP practitioner would file it under; when torn between two, prefer the one matching the product's role *in this diagram* (e.g. Cloud Armor protecting an LB → `cat-networking`).

Note: Firebase products have their own brand and are not in this set — leave those boxes icon-free rather than mislabeling them.

## Style interaction

Icons complement the house style; they don't replace it. Keep the palette, zone colors, accent bars, arrow styles, and typography from `style-spec.md` exactly as-is. The icons' own Google brand colors (blue/red/yellow/green) sit comfortably on the white component boxes — never recolor, stretch, crop, or add effects to an icon (Google's brand guidelines and good taste both forbid it).
