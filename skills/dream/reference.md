# Domain reference — grounding for PRD drafting

What `/dream` needs to know about the product domain, the positioning, and the
product-management craft before drafting. Read the section that matches the seed;
skim the rest. This file carries concept-level knowledge only — evidence for any
specific PRD claim still comes from Phase 1 research. It deliberately contains no
pricing, no customer names, and no competitive battlecard material.

## Technical reference — the AtScale semantic layer

**What it is.** AtScale is middleware between cloud data warehouses and everything
that consumes data — BI tools, spreadsheets, notebooks, applications, and AI agents.
Metrics and dimensions are defined once, in one model, and every consumer gets the
same governed answer.

**SML — the modeling language.** Semantic Modeling Language is an open (Apache 2.0),
Git-native YAML language. Its object types: Dataset, Measure, Dimension, Hierarchy,
Calculated Member, Relationship, Perspective (an audience-scoped subset of a model),
and Security Rule. Models can import from other modeling languages (dbt, LookML,
Power BI) and compose across repositories.

**Six query protocols, one model.** The same model is served simultaneously over:
- **DAX** — Power BI connects live via XMLA, no data import
- **MDX** — Excel PivotTables and Tableau, with user hierarchies preserved
- **SQL** — standard JDBC/ODBC
- **PGWire** — the Postgres wire protocol, for tools that speak Postgres
- **Python** — a DataFrame client for notebooks and data science
- **MCP** — the Model Context Protocol, for AI agents

**Query planning.** A cost-based planner resolves join paths from the model's
relationships, decides where each query runs (in-memory cache → pre-computed
aggregate tables → live SQL pushdown to the warehouse), and emits SQL in the
warehouse's own dialect. The consumer never sees any of this; they query the model.

**Autonomous aggregates.** The engine creates and maintains aggregate tables on its
own: demand-defined aggregates react to observed query patterns; prediction-defined
aggregates are built proactively from table statistics before a model is even
published; modelers can also hint or define aggregates by hand. This is how
dashboard-speed queries come off warehouse-scale data without manual tuning.

**Governance.** Row- and column-level security is enforced in the semantic layer for
every protocol, including agent queries over MCP, with a full audit trail. Queries
can run under the end user's own warehouse identity, so native warehouse security
still applies.

**The comparison landscape (concept level).** Other semantic layers are narrower on
one of two axes: modeling richness (SQL-only metric layers have flat dimensions — no
hierarchies, no calculated members) or reach (BI-vendor languages serve only their
own tool). The distinctive AtScale combination is OLAP-rich modeling plus
multi-protocol reach plus cross-platform federation (one model spanning multiple
warehouses at once).

## Positioning reference — the public narrative

**Four differentiators**, in the language the company uses publicly:
- **Universal** — one model, every consumer, human or agent
- **Open** — open spec (SML), open protocols, no lock-in to a cloud, BI vendor, or AI runtime
- **Composable** — drops into the existing stack; no re-platforming
- **Dimensional** — true multidimensional modeling: hierarchies, calculated members, time intelligence

**The AI-ready data narrative.** Data isn't AI-ready until it has a semantic layer.
An LLM writing SQL against a raw schema guesses at table meanings and invents joins;
given a semantic model, it selects from governed, named metrics instead. Published
benchmarks show a dramatic accuracy gap between the two. The argument has three
parts: a constrained output space (the agent can't invent columns), a governed
metric vocabulary (the agent uses the business's own definitions), and enforced
security with an audit trail (the agent is as governed as any human user).

**Where it sits in the AI stack.** Two layers at once: a *tool* layer (the MCP
server agents call for governed data access) and a *knowledge and context* layer
(the semantic definitions that ground what the agent says). Complementary to — not
competing with — vector databases (unstructured content), knowledge graphs
(relationships), and data catalogs (metadata about data).

**The adoption argument.** Semantic definitions fail when they exist but nobody uses
them. Surfacing one model natively in every tool — the spreadsheet, the dashboard,
the notebook, the agent — removes the translation step where trust dies.

## Product-management reference — frameworks for the craft

Use these when shaping a vision or judging whether a PRD-sized bet is the right bet.
One line each; look any of them up when a seed calls for depth.

**Strategy and prioritization**
- **Playing to Win** — five cascading choices: winning aspiration → where to play → how to win → capabilities → systems; every choice must reinforce the others.
- **Jobs-to-be-Done** — customers hire products to make progress on a job; find jobs that are important but poorly served.
- **Positioning (Obviously Awesome)** — start from real competitive alternatives (including "do nothing" and "use Excel"), then unique attributes → value themes → best-fit segments → market category.
- **RICE scoring** — (Reach × Impact × Confidence) / Effort; the Confidence term is the bias-killer; the score informs the decision, it doesn't make it.
- **Opportunity Solution Trees** — outcome → opportunities (customer needs) → solutions → experiments; test the riskiest assumption first.
- **North Star Metric** — one metric that reflects customer value, leads revenue, and the team can actually move; decompose into a handful of input metrics.
- **Kano model** — must-be, performance, and delight features are different games; yesterday's delight is tomorrow's must-be.

**AI-product patterns** (for any PRD with an LLM or agent in it)
- **Golden dataset first** — a versioned, ground-truthed eval set is the most important artifact; build it before the feature.
- **Execution accuracy** — the metric that matters for generated queries: does it run AND return the right answer?
- **The 95% problem** — 95% on a benchmark still means hundreds of visible errors a day at enterprise query volume; plan for the failures, not just the score.
- **Trust calibration** — the goal is user trust that matches actual reliability; over-trust is dangerous, under-trust wastes the feature.
- **Progressive autonomy** — copilot (suggests) → draft (human reviews) → delegate (human approves exceptions) → agent (human monitors); tier by how reversible the action is.
- **Three-layer evaluation** — offline golden-dataset gate in CI, online shadow/canary/A-B rollout, periodic human expert review.
- **Risk formula** — Impact × Probability × (1 − Reversibility); irreversible high-impact actions don't get automated.

**Scoping heuristics**
- Add AI only when input variability is high, an approximate answer is useful, the user can verify it, and failure is recoverable — otherwise write deterministic logic.
- The disambiguation cascade for ambiguous requests: semantic-model default → context → ask the user. Never silently guess.
- Count the AI tax honestly: evaluation infrastructure, debugging, trust UX, and monitoring all cost; if the tax exceeds the value, the deterministic alternative wins.
