# Phase 2: Autonomous Curator Architecture

## Vision

Build a meta-system that generates and executes collection curation solutions autonomously, rather than hand-coding scrapers for each data source.

## The Problem We're Solving

**Wrong Approach** (what I did initially):
- Write `elden_ring_curator.py` by hand
- Hard-code selectors and logic
- Manually categorize and import
- Repeat for each new data source

**Right Approach** (what we're building):
- User provides: goal + URL + collection context
- System analyzes source autonomously
- Generates necessary tools/workflows
- Executes and learns
- Reuses knowledge for similar sources

## Four-Phase Architecture

### Phase A: Initialization

**User Input** (minimal):
```python
curator = AutonomousCurator()
curator.initialize(
    goal="Import Elden Ring merchandise",
    source="https://store.bandainamcoent.eu/elden-ring-collection-figurines/",
    collection_id="c427fd49-97d1-427b-8126-cee2042fef63"
)
```

**System Actions**:
1. Generate unique curator ID (e.g., "elden-ring-curator")
2. Create memory footprint in Mem0
3. Set up artifact directory: `artifacts/{curator_id}/`
4. Store goal (importance 1.0 - protected, never forgotten)
5. Initialize DeepAgents context
6. Return ready curator instance

**Outputs**:
- Curator instance ready to discover
- Memory entry with goal and context
- Empty artifact directory

---

### Phase B: Discovery

**Trigger**: `curator.discover()` or automatic on first run

**System Actions**:
1. **Fetch Source**: Download HTML/API response from URL
2. **LLM Analysis**: Send to Gemini 2.5 Flash with prompt:
   ```
   Analyze this source and determine:
   - Is this a web page or API?
   - What data structure? (e-commerce, catalog, API endpoint)
   - What data fields are available?
   - What technology? (BigCommerce, Shopify, custom)
   - What extraction strategy? (CSS selectors, JSON parsing)
   ```
3. **Generate Discovery Report**: Structured JSON with findings
4. **Store in Memory**: Save report (importance 0.7 - strategic knowledge)

**Outputs**:
- Discovery report JSON
- Memory entry with source analysis
- Recommended approach

**Example Discovery Report**:
```json
{
  "source_type": "web_page",
  "technology": "bigcommerce",
  "structure": "product_listing",
  "data_available": {
    "products": true,
    "prices": true,
    "images": true,
    "categories": true
  },
  "extraction_strategy": "html_scraping",
  "selectors": {
    "product_card": "article.card",
    "name": "h2.card-title",
    "price": "a.card-figure__link[data-productprice]",
    "image": "img.card-image[data-srcset]"
  },
  "pagination": {
    "available": true,
    "pattern": "?page={n}"
  }
}
```

---

### Phase C: Workflow and Tool Creation

**Trigger**: After successful discovery

**System Actions**:
1. **Decision**: Curator uses DeepAgents to decide what to build:
   - Simple scraper script?
   - Complex LangGraph workflow?
   - API client?

2. **Code Generation**: Use LLM to generate Python code
   - Prompt includes discovery report
   - Generates complete, runnable code
   - Includes error handling, logging

3. **Artifact Storage**:
   - Save to `artifacts/{curator_id}/scraper.py`
   - Store in memory with metadata
   - Version tracking

4. **Validation**: Optionally test-run on sample data

**Outputs**:
- Generated Python script(s)
- LangGraph workflow definition (if needed)
- Invocation plan
- Memory entry linking goal → artifact

**Example Generated Artifact** (`artifacts/elden-ring-curator/scraper.py`):
```python
"""
Auto-generated scraper for Elden Ring merchandise
Generated: 2025-11-03
Source: https://store.bandainamcoent.eu/...
"""

import asyncio
from bs4 import BeautifulSoup
import httpx

async def scrape_products(url: str, max_pages: int = 1):
    """Scrape products from Bandai Namco store."""
    # ... LLM-generated code based on discovery report ...
    pass

if __name__ == "__main__":
    asyncio.run(scrape_products("...", max_pages=4))
```

---

### Phase D: Invocation

**Trigger**: `curator.run()` or scheduled

**System Actions**:
1. **Check Memory**: Look for existing artifacts
   ```python
   existing_workflow = curator.memory.search(
       f"workflow for {source_url}"
   )
   ```

2. **Decision**: Should we reuse, modify, or regenerate?
   - If website changed: regenerate
   - If new products expected: reuse
   - If errors occurred: modify

3. **Execute**: Run the generated artifact
   - Import generated module
   - Execute with monitoring
   - Capture results and errors

4. **Monitor**: Track progress in real-time
   - Log to console
   - Store interim results
   - Handle failures gracefully

5. **Learn**: Update memory with execution results
   ```python
   curator.memory.store({
       "type": "execution_result",
       "success": True,
       "products_imported": 20,
       "errors": [],
       "timestamp": "2025-11-03T17:00:00Z"
   }, importance=0.3)
   ```

**Outputs**:
- Imported products in database
- Updated memory with results
- Execution report
- Learned patterns for future runs

---

## Technology Mapping

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Meta-Agent** | DeepAgents | Autonomous decision-making across all phases |
| **Planning** | LangGraph | Complex multi-step workflows |
| **Analysis** | Gemini 2.5 Flash | Source analysis, code generation |
| **Memory** | Mem0 + Qdrant | Persistent knowledge and artifacts |
| **Artifact Storage** | Filesystem + Memory | Generated code and workflows |
| **Execution** | Python subprocess | Run generated scripts |
| **Database** | Supabase | Store imported collectibles |

## Memory Architecture

### Importance Levels

**1.0 - Protected** (never pruned):
- User goals and preferences
- Collection structure and relationships
- Explicit rules and constraints

**0.7 - Strategic** (high value):
- Discovery reports for sources
- Generated workflows and artifacts
- Successful extraction patterns
- API credentials and endpoints

**0.3 - Tactical** (can be pruned):
- Execution state and progress
- Individual product data during processing
- Temporary context and calculations

### Memory Queries

```python
# Find existing workflow for a source
curator.memory.search(
    "workflow for bandainamcoent.eu elden ring",
    limit=1
)

# Get all discovered patterns for BigCommerce sites
curator.memory.search(
    "bigcommerce scraping strategy",
    filters={"source_type": "web_page"}
)

# Retrieve execution history
curator.memory.search(
    f"execution results for {curator_id}",
    limit=10
)
```

## Code Structure

```
curators/
├── core/
│   ├── autonomous_curator.py      # Main meta-system
│   ├── discovery_agent.py         # Phase B: Source analysis
│   ├── workflow_generator.py      # Phase C: Code generation
│   └── execution_engine.py        # Phase D: Artifact execution
├── artifacts/
│   └── {curator_id}/
│       ├── scraper.py             # Generated scrapers
│       ├── workflow.json          # LangGraph workflows
│       └── metadata.json          # Artifact metadata
└── examples/
    └── elden_ring_example.py      # Usage example
```

## Example Usage

```python
from core.autonomous_curator import AutonomousCurator

# Initialize with minimal instruction
curator = AutonomousCurator()
await curator.initialize(
    goal="Import Elden Ring merchandise from Bandai Namco Store",
    source="https://store.bandainamcoent.eu/elden-ring-collection-figurines/",
    collection_id="c427fd49-97d1-427b-8126-cee2042fef63"
)

# First run: Discovers, generates, executes
result = await curator.run()
print(f"Imported {result['products_imported']} products")

# Second run: Reuses existing workflow
result = await curator.run()
print(f"Updated with {result['new_products']} new products")

# Manual phases (if needed)
await curator.discover()           # Just analyze
await curator.generate_workflow()  # Just create tools
await curator.execute()             # Just run existing workflow
```

## Comparison: Before vs After

### Before (Manual Approach)
```python
# curators/elden_ring_curator.py - 330 lines of hand-coded logic
class EldenRingCurator:
    def __init__(self, collection_id):
        # Hard-coded selectors
        self.base_url = "https://store.bandainamcoent.eu"

    def parse_product_listing(self, html):
        # Hand-coded BeautifulSoup logic
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("article", class_="card")
        # ... 50+ lines of parsing logic ...
```

**Problems**:
- Every new source needs a new curator
- Can't adapt to website changes
- No learning or reuse
- Developer writes all logic

### After (Autonomous Approach)
```python
# User provides minimal instruction
curator = AutonomousCurator()
await curator.initialize(
    goal="Import Elden Ring merchandise",
    source="https://store.bandainamcoent.eu/elden-ring-collection-figurines/",
    collection_id="uuid"
)

# System does everything
await curator.run()
```

**Benefits**:
- Analyzes source automatically
- Generates optimal extraction strategy
- Adapts to changes (regenerates if needed)
- Learns patterns across sources
- Reuses knowledge for similar sites

## Next Steps

1. **Build AutonomousCurator class** - Core orchestrator
2. **Implement DiscoveryAgent** - Source analysis with LLM
3. **Build WorkflowGenerator** - Code generation from findings
4. **Create ExecutionEngine** - Safe artifact execution
5. **Test with Elden Ring** - Verify it generates the same result
6. **Test with new source** - Verify autonomous generalization
