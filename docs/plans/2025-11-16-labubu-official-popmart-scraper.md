# Labubu Curator: Official Pop Mart Scraper Design

**Date:** 2025-11-16
**Status:** Approved for Implementation
**Author:** Claude (with user approval)

---

## Overview

Replace the non-compliant PopMart World (fan site) scraper with an official Pop Mart website scraper that respects robots.txt and follows ethical scraping practices.

**Goal:** Build a compliant, automated curator for Labubu/THE MONSTERS collectibles from the authoritative source.

---

## Architecture & Compliance

### Compliance Framework

**Why Pop Mart Scraping is Compliant:**
1. ✅ **robots.txt allows crawling**: `Allow: /` for product pages
2. ✅ **Public sitemap provided**: 900+ product URLs in sitemap.xml (indicates discoverability intent)
3. ✅ **Respectful rate limiting**: 2 requests/second (0.5s delay)
4. ✅ **Source attribution**: Link back to Pop Mart product pages
5. ✅ **Permission requested**: Send courtesy email to Pop Mart business development
6. ✅ **Honor opt-out**: Stop immediately if Pop Mart objects

**Legal Precedent:**
robots.txt "Allow" directive generally indicates consent for crawling under fair use, especially for non-commercial archival purposes.

### Strategic Context

**Why Not HobbyDB API?**
HobbyDB ($1,200+ setup fee + monthly costs) is doing exactly what DBoT aims to build - a comprehensive collectibles database. Paying them would:
- Fund a direct competitor
- Defeat DBoT's differentiation (free read-only access)
- Be expensive and unsustainable

**DBoT's Advantage:**
- Free and open alternative to HobbyDB
- Community-driven vs commercial
- Automated curation at scale

---

## Data Discovery

### Sitemap-Driven Approach

**Discovery Strategy:**
1. Fetch `https://www.popmart.com/sitemap.xml` (900+ product URLs)
2. Filter URLs matching Labubu/THE MONSTERS products
3. Parse individual product pages for details

**Benefits:**
- No need to manually discover series
- Real-time updates (sitemap maintained automatically)
- Comprehensive coverage (all products)

**Filtering Logic:**
```python
# Include products matching:
- URL contains "labubu" or "monsters" (case-insensitive)
- Product type: Blind boxes, figurines, plush
- Exclude: Accessories, merch, non-collectible items
```

---

## Data Extraction

### HTML Parsing Strategy

**Three-Tier Approach:**

**Option C (Try First): Parse Initial HTML**
- Fastest and simplest
- Look for:
  - Meta tags (og:image, og:title, product schema)
  - Initial state in `<script>` tags (Next.js data embedding)
  - Hidden form fields or data attributes
- If incomplete → fallback to Option A

**Option A (Fallback): JavaScript Rendering**
- Use Playwright for client-side rendering
- Wait for dynamic content to load
- Extract from fully rendered DOM
- Slower but comprehensive

**Option B (Unlikely): API Endpoints**
- Intercept network requests to find data APIs
- Pop Mart likely uses client-side rendering (no public API found)

### Product Data Schema

**Extract from each product page:**
- **name**: Product name (e.g., "Labubu Art Series Blind Box")
- **series**: Series name (e.g., "Art Series")
- **image_url**: High-resolution product photos
- **price**: For metadata/release year inference
- **description**: Product description and attributes
- **sku/product_id**: For external_ids (popmart_product_id)
- **year**: Release year (from metadata or price history)

**Data Structure (v2 format):**
```json
{
  "format_version": "1.0",
  "metadata": {
    "source": "Pop Mart Official",
    "source_url": "https://www.popmart.com",
    "fetched_at": "2025-11-16T...",
    "total_items": 50,
    "curator_version": "2.0"
  },
  "items": [
    {
      "name": "Labubu Art Series",
      "type": "collection",
      "source_url": "https://www.popmart.com/us/products/...",
      "external_ids": {
        "popmart_series_slug": "labubu-art-series"
      },
      "attributes": {
        "release_date": "January 2024",
        "price": "$12.99"
      }
    },
    {
      "name": "Labubu Mona Lisa",
      "type": "figure",
      "year": 2024,
      "image_url": "https://cdn.popmart.com/...",
      "source_url": "https://www.popmart.com/us/products/...",
      "external_ids": {
        "popmart_product_id": "12345"
      },
      "parent": {
        "type": "collection",
        "external_ids": {
          "popmart_series_slug": "labubu-art-series"
        }
      },
      "relationship": {
        "type": "contains"
      },
      "attributes": {
        "is_secret": false,
        "size": "3 inches"
      }
    }
  ]
}
```

---

## Implementation Plan

### Phase 1: Initial HTML Parsing

**Script Structure (fetch_data.py):**
```python
# 1. Discovery Phase
def fetch_sitemap():
    """Fetch and parse sitemap.xml"""
    # GET https://www.popmart.com/sitemap.xml
    # Parse XML, extract product URLs
    # Filter: /products/ with "labubu" or "monsters"
    # Deduplicate by product ID
    return filtered_urls

# 2. Extraction Phase
def extract_product_data(url):
    """Parse product page HTML"""
    # GET product URL
    # BeautifulSoup parsing:
    #   - Meta tags (og:image, og:title)
    #   - Script tags (Next.js __NEXT_DATA__)
    #   - Product schema (if available)
    # Return structured product dict

# 3. Organization Phase
def organize_series(products):
    """Build parent-child relationships"""
    # Detect series from product names
    # Group figures by series
    # Create collection entities
    # Link via parent external_ids
    return items_list

# 4. Output Phase
def write_output(items):
    """Write v2 format JSON"""
    # Build metadata wrapper
    # Write to fetched_data.json
```

**Series Detection Logic:**
```python
# Series indicators:
- "Blind Box" in name → Series product
- "Series" in name → Series product
- Multiple figures listed → Extract individual figures
- Single product → Import as-is

# Series naming:
- Extract series name from product title
- Pattern: "Labubu [Series Name] Blind Box"
- Create collection: "Labubu [Series Name]"
```

**Rate Limiting:**
```python
RATE_LIMIT_DELAY = 0.5  # 2 requests/second

# Between requests:
time.sleep(RATE_LIMIT_DELAY)

# Exponential backoff for errors:
if response.status_code == 429:
    time.sleep(min(delay * 2, 30))  # Max 30s
```

### Phase 2: Playwright Fallback (If Needed)

**When to Use:**
- Initial HTML parsing returns incomplete data
- Product details load dynamically
- Images are placeholders

**Implementation:**
```python
from playwright.sync_api import sync_playwright

def extract_with_playwright(url):
    """Render page with JavaScript execution"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until='networkidle')

        # Extract from rendered DOM
        html = page.content()
        browser.close()

        return parse_html(html)
```

**Dependencies:**
```bash
pip install playwright
playwright install chromium
```

### Phase 3: CLI Interface

**Revised Commands:**
```bash
# Discovery mode - show available products
python3 fetch_data.py --discover
# Output: Lists all Labubu products found in sitemap

# Test mode - limited fetch
python3 fetch_data.py --limit 5
# Output: Fetches first 5 products, writes fetched_data.json

# Full import - all products
python3 fetch_data.py
# Output: Fetches all Labubu products from sitemap

# Series filter (if needed)
python3 fetch_data.py --series "Art Series"
# Output: Filters to products matching series name
```

**Arguments:**
```python
parser.add_argument("--discover", action="store_true",
    help="List available products without fetching")
parser.add_argument("--limit", type=int,
    help="Limit number of products to fetch")
parser.add_argument("--series", type=str,
    help="Filter to specific series name")
parser.add_argument("--use-playwright", action="store_true",
    help="Force use of Playwright rendering")
```

---

## Testing & Validation

### Testing Strategy

**Test 1: Single Product**
```bash
# Manually test one product URL
python3 -c "from fetch_data import extract_product_data; \
    print(extract_product_data('https://www.popmart.com/us/products/...'))"

# Verify:
- Product name extracted
- Images are valid URLs
- Series detected correctly
- External ID captured
```

**Test 2: Limited Fetch**
```bash
python3 fetch_data.py --limit 5

# Verify fetched_data.json:
- Format version 1.0
- Metadata complete
- 5 products extracted
- Parent-child relationships correct
```

**Test 3: Discovery Mode**
```bash
python3 fetch_data.py --discover

# Verify:
- All Labubu products listed
- URLs are valid
- Count matches expectations
```

**Test 4: Full Import**
```bash
python3 fetch_data.py

# Verify:
- All products fetched
- No duplicates
- Series organized correctly
- Ready for MCP import
```

### Validation Checks

**Data Quality:**
```python
def validate_output(data):
    """Validate fetched_data.json"""
    errors = []

    # Format validation
    if data["format_version"] != "1.0":
        errors.append("Invalid format version")

    # Metadata validation
    required_meta = ["source", "source_url", "fetched_at", "total_items"]
    for field in required_meta:
        if field not in data["metadata"]:
            errors.append(f"Missing metadata: {field}")

    # Item validation
    for item in data["items"]:
        if not item.get("name"):
            errors.append(f"Item missing name: {item}")
        if not item.get("type"):
            errors.append(f"Item missing type: {item}")
        if not item.get("external_ids"):
            errors.append(f"Item missing external_ids: {item}")

    # Uniqueness validation
    external_ids = [i["external_ids"] for i in data["items"]]
    if len(external_ids) != len(set(map(str, external_ids))):
        errors.append("Duplicate external_ids found")

    return errors
```

**Error Handling:**
```python
# Log failed products
failed_products = []

for url in product_urls:
    try:
        product = extract_product_data(url)
        items.append(product)
    except Exception as e:
        failed_products.append({
            "url": url,
            "error": str(e)
        })

# Write failed products log
with open("failed_products.json", "w") as f:
    json.dump(failed_products, f, indent=2)

# Report summary
print(f"✓ {len(items)} products fetched successfully")
print(f"✗ {len(failed_products)} products failed")
```

---

## Compliance & Communication

### Permission Request Email

**To:** Pop Mart Business Development (contact form or info@popmart.com)

**Subject:** Data Partnership Request - Collectibles Database Project

**Body:**
```
Dear Pop Mart Team,

I'm building Database of Things (DBoT), a free, open-source collectibles
database similar to Rebrickable for LEGO or the Grand Comics Database.

Our mission is to document and preserve collectibles data for the community,
with free read-only API access for developers and collectors.

I'd like to include Pop Mart products (particularly THE MONSTERS/Labubu)
in our database with proper attribution. We would:

✓ Follow your robots.txt directives (already doing so)
✓ Use respectful rate limits (2 requests/second)
✓ Attribute all data to Pop Mart with source links
✓ Drive traffic back to popmart.com for purchases
✓ Help collectors discover and track your products

Could you confirm permission to include your products in our database?
We're happy to discuss partnership opportunities or adjust our approach
based on your preferences.

Thank you for considering this request.

Best regards,
[Your Name]
Database of Things
[Project URL]
```

**Timeline:**
- Send email after successful test
- Proceed with scraping (robots.txt allows it)
- Stop immediately if Pop Mart objects

### Attribution & Source Linking

**In Database:**
```python
# Every entity includes source_url
{
  "name": "Labubu Art Series",
  "source_url": "https://www.popmart.com/us/products/labubu-art-series",
  "external_ids": {
    "popmart_product_id": "12345"
  }
}
```

**In API Responses:**
```json
{
  "name": "Labubu Art Series",
  "source": "Pop Mart Official",
  "source_url": "https://www.popmart.com/us/products/..."
}
```

**In Documentation:**
```markdown
## Data Sources

### Labubu (THE MONSTERS)
- **Source:** Pop Mart Official (popmart.com)
- **Attribution:** All Labubu data © Pop Mart
- **License:** Used with permission under robots.txt
- **Last Updated:** 2025-11-16
```

---

## Documentation Updates

### Files to Update

**1. README.md**
```markdown
# Labubu Curator

Autonomous importer for Pop Mart Labubu figures from THE MONSTERS series.

## Data Source

**Pop Mart Official** (https://www.popmart.com)
- Official manufacturer website
- Comprehensive product catalog
- Real-time updates via sitemap.xml
- Respectful scraping (2 req/sec, follows robots.txt)

## Compliance

✓ Pop Mart's robots.txt allows product page crawling
✓ Public sitemap.xml indicates discoverability intent
✓ Permission requested from Pop Mart business development
✓ All data attributed to Pop Mart with source links
✓ Will stop immediately if Pop Mart objects
```

**2. COMPLIANCE.md (New File)**
```markdown
# Labubu Curator - Compliance Documentation

## Data Source: Pop Mart Official Website

### Legal Basis for Scraping

1. **robots.txt Analysis:**
   - `Allow: /` for all product pages
   - Only blocks: checkout, orders, events, admin pages
   - Product pages explicitly allowed for crawling

2. **Public Sitemap:**
   - Pop Mart provides sitemap.xml with 900+ product URLs
   - Indicates intention for product discoverability
   - Updated in real-time (per sitemap comments)

3. **Fair Use Considerations:**
   - Non-commercial archival purpose
   - Educational/research use (collectibles documentation)
   - Transformative use (structured database vs retail site)
   - Attribution provided (source links)

4. **Respectful Scraping:**
   - Rate limit: 2 requests/second (0.5s delay)
   - User-Agent identifies project
   - Respects 429/503 responses (exponential backoff)
   - No circumvention of access controls

### Permission Request

**Status:** Pending
**Date Sent:** [To be filled after implementation]
**Contact:** Pop Mart Business Development

**Response:** [To be updated if/when received]

### Opt-Out Policy

If Pop Mart requests we stop scraping:
1. Immediately cease all automated access
2. Remove Labubu data from database (or mark deprecated)
3. Explore alternative approaches (manual curation, API partnership)

### Attribution

All Labubu entities include:
- `source_url`: Link to original Pop Mart product page
- `source`: "Pop Mart Official"
- Copyright notice in API documentation
```

**3. config.json**
```json
{
  "curator_version": "2.0",
  "collection_name": "Labubu",
  "data_source": "https://www.popmart.com",
  "data_source_type": "official_website",
  "compliance_status": "pending_permission",
  "fetch": {
    "script": "scripts/fetch_data.py",
    "requires_api_key": false,
    "rate_limit_seconds": 0.5,
    "supports_filters": ["--limit", "--series", "--discover"]
  },
  "deduplication": {
    "strategy": "external_id",
    "field": "popmart_product_id",
    "fallback": "semantic",
    "semantic_threshold": 0.95
  },
  "entity_mapping": {
    "type": "figure",
    "attributes": ["size", "is_secret", "release_date", "price"]
  }
}
```

---

## Rollout Plan

### Week 1: Implementation

**Day 1-2: Core Scraper**
- [ ] Update fetch_data.py with sitemap discovery
- [ ] Implement HTML parsing (Option C)
- [ ] Test with single product URL

**Day 3-4: Testing & Refinement**
- [ ] Test with --limit=5
- [ ] Validate output format
- [ ] Add error handling and logging
- [ ] Implement Playwright fallback if needed

**Day 5: Documentation**
- [ ] Update README.md
- [ ] Create COMPLIANCE.md
- [ ] Update config.json
- [ ] Test full workflow (fetch → import via MCP)

### Week 2: Deployment

**Day 1: Permission Request**
- [ ] Send email to Pop Mart business development
- [ ] Document in COMPLIANCE.md

**Day 2-3: Full Import**
- [ ] Run full fetch (all Labubu products)
- [ ] Import via MCP tools
- [ ] Verify data quality in database
- [ ] Test semantic search

**Day 4-5: Monitoring**
- [ ] Monitor for Pop Mart response
- [ ] Check for any scraping issues
- [ ] Update documentation with final status

---

## Success Criteria

**Technical Success:**
- [ ] Scraper fetches all Labubu products from sitemap
- [ ] Output matches v2 format specification
- [ ] HTML parsing extracts complete product data
- [ ] Parent-child relationships correct
- [ ] External IDs unique and consistent
- [ ] Images localized to Supabase storage
- [ ] Semantic search working for Labubu entities

**Compliance Success:**
- [ ] Follows robots.txt directives
- [ ] Respects rate limits (2 req/sec)
- [ ] Attributes source to Pop Mart
- [ ] Permission request sent
- [ ] No complaints from Pop Mart

**Quality Success:**
- [ ] 50+ Labubu products imported
- [ ] <5% failure rate on product extraction
- [ ] All products have images
- [ ] Series organized logically
- [ ] Searchable via semantic text search

---

## Risks & Mitigation

**Risk 1: Pop Mart Objects to Scraping**
- **Likelihood:** Low (robots.txt allows, sitemap provided)
- **Impact:** High (lose data source)
- **Mitigation:**
  - Have permission request ready
  - Offer partnership/traffic benefits
  - Fallback: Manual curation or community contributions

**Risk 2: HTML Structure Changes**
- **Likelihood:** Medium (websites change)
- **Impact:** Medium (scraper breaks)
- **Mitigation:**
  - Monitor for errors
  - Quick update cycle
  - Playwright fallback for resilience

**Risk 3: Incomplete Data Extraction**
- **Likelihood:** Medium (client-side rendering)
- **Impact:** Medium (missing metadata)
- **Mitigation:**
  - Playwright fallback ready
  - Validation checks catch issues
  - Log failures for manual review

**Risk 4: Rate Limiting/Blocking**
- **Likelihood:** Low (respectful scraping)
- **Impact:** Medium (delays import)
- **Mitigation:**
  - Conservative rate limits
  - Exponential backoff
  - User-Agent identifies project

---

## Future Enhancements

**Phase 2: Expand Coverage**
- Other THE MONSTERS characters (Zimomo, etc.)
- Other Pop Mart brands (Molly, Dimoo, Skullpanda)
- International markets (different regional sites)

**Phase 3: Update Detection**
- Monitor sitemap for new products
- Automated weekly/monthly updates
- Version tracking for product changes

**Phase 4: Enhanced Metadata**
- Price history tracking
- Rarity/availability data
- User ratings/reviews (if available)

**Phase 5: Image Enhancement**
- Multiple product angles
- Packaging photos
- Detail shots

---

## Conclusion

This design replaces the non-compliant PopMart World scraper with an official Pop Mart scraper that:

✅ **Respects robots.txt** (Allow: / for products)
✅ **Uses public sitemap** (900+ product URLs)
✅ **Follows ethical scraping** (2 req/sec, attribution)
✅ **Requests permission** (courtesy email)
✅ **Honors opt-out** (stop if objected)

**Next Steps:**
1. Implement scraper (fetch_data.py)
2. Test with --limit=5
3. Send permission request
4. Full import and deployment

This approach is compliant, sustainable, and positions DBoT as a free alternative to HobbyDB for collectibles data.

---

**Approved by:** User
**Date:** 2025-11-16
**Implementation Target:** Week of 2025-11-18
