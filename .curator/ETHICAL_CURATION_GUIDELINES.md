# Ethical Manual Curation Guidelines

**Purpose:** Guidelines for manually curating collectibles data in a compliant and ethical manner.

---

## Core Principles

### 1. Manual vs Automated
**Ethical:** Human visits website, reads information, manually enters data into database
**Not Ethical:** Automated scripts extracting data without permission

**Why it matters:** Manual curation is research, automated scraping can violate ToS and strain servers.

### 2. Attribution
**Always required:** Store source URL in `source_url` field for every entity
**Purpose:** Credit sources, allow users to verify information, transparent provenance

### 3. Factual Information Only
**Ethical to catalog:**
- Product names (factual)
- Release dates (factual)
- Sizes/dimensions (factual)
- Manufacturers (factual)
- Series names (factual)

**Not ethical to copy:**
- Marketing descriptions (creative work, copyrighted)
- Reviews or editorial content (copyrighted)
- Unique creative descriptions (copyrighted)

### 4. Respect Robots.txt
**Always check:** Visit `/robots.txt` before accessing any site
**Honor restrictions:** If `User-agent: *` disallows paths, don't access them

---

## Image Handling Guidelines

### Three-Tier Approach

#### Tier 1: Official Manufacturer Sources (Preferred)
**Sources:**
- Official Pop Mart product pages
- Official manufacturer press releases
- Official retailer product pages

**Rationale:**
- Manufacturers provide images for promotional purposes
- Product photos intended for public consumption
- Clear attribution path

**Best Practice:**
- Link to source page in `source_url`
- Download and host locally (don't hotlink)
- Add attribution in image metadata if possible

#### Tier 2: No Images Initially (Acceptable)
**Approach:**
- Create entities with metadata only
- Leave `image_url` NULL
- Wait for community contributions with explicit licenses

**Rationale:**
- Completely safe legally
- Better than using questionable sources
- Encourages community participation

#### Tier 3: Community Contributions (Ideal Long-term)
**Approach:**
- Users upload their own photos
- Explicit license grant to DBoT
- User retains attribution

**Why this is best:**
- Explicit permission
- Community ownership
- Sustainable and compliant

---

## Ethical Manual Curation Process

### Step 1: Check Compliance
```bash
# Check robots.txt
curl https://www.example.com/robots.txt

# Look for ToS/Terms
# Visit /terms, /tos, /legal pages
```

**If robots.txt blocks access → STOP, don't proceed**
**If ToS prohibits data collection → STOP, don't proceed**
**If no robots.txt or ToS → Proceed with caution, attribute sources**

### Step 2: Manual Data Collection
**Tools:** Just a web browser and notepad/spreadsheet

**Process:**
1. Visit product page (as normal user)
2. Read product information
3. Take notes on factual information:
   - Name
   - Series
   - Release date
   - Size
   - Manufacturer
4. Copy source URL
5. Do NOT copy descriptions or marketing text

**Example Notes:**
```
Name: Labubu - Mona Lisa
Series: Art Series
Release Date: 2023
Size: 3-4 inches
Manufacturer: Pop Mart
Source: https://www.popmart.com/us/products/...
Image: Official product image available (note URL for later)
```

### Step 3: Manual Data Entry
**Either:**
- Add directly to database via Supabase Studio
- Create CSV/JSON file for batch import
- Use a simple web form (future community system)

**Required fields:**
```json
{
  "name": "Labubu - Mona Lisa",
  "type": "figure",
  "year": 2023,
  "source_url": "https://www.popmart.com/us/products/...",
  "external_ids": {},
  "attributes": {
    "series": "Art Series",
    "size": "3-4 inches",
    "manufacturer": "Pop Mart"
  }
}
```

### Step 4: Image Handling Decision Tree

```
Do we need an image right now?
├─ No → Leave image_url NULL, add later
└─ Yes → Where can we get it?
    ├─ Official manufacturer site → Download and host locally
    ├─ User contribution → Requires license grant
    └─ Third-party site → Skip for now, too risky
```

---

## Source-Specific Guidelines

### Pop Mart Official (popmart.com)

**Check robots.txt:**
```bash
curl https://www.popmart.com/robots.txt
```

**Ethical approach:**
- ✅ Manual browsing of product pages
- ✅ Recording factual information (names, dates, sizes)
- ✅ Attributing source URLs
- ✅ Using official product images (with attribution)
- ❌ Automated scraping
- ❌ Copying marketing descriptions

**Images:** Official product images are promotional material, likely OK to use with attribution

### PopMartWorld.com (Fan Site)

**Status:** Fan-run catalog

**Ethical approach:**
- ⚠️ Manual browsing OK for research
- ⚠️ Cross-reference with official sources
- ❌ Don't copy images (site states images belong to copyright holders)
- ✅ Use as reference to find official sources

**Better approach:** Use PopMartWorld to *discover* products, then verify on official Pop Mart site

### Retailer Sites (Rotofugi, myplasticheart, etc.)

**Check each site's robots.txt and ToS**

**Ethical approach:**
- ✅ Manual browsing of product listings
- ✅ Recording factual information
- ✅ Attributing sources
- ⚠️ Images: Check if retailer allows product image use
- Consider reaching out for partnership

---

## Rate Limiting (Even for Manual Work)

**Be respectful:**
- Don't visit 100s of pages in rapid succession
- Space out research sessions
- Act like a normal user, not a bot

**Good practice:**
- Take breaks between pages
- Don't overwhelm servers
- If manually recording 50 items, spread over multiple sessions

---

## Attribution Best Practices

### In Database
**Always include:**
```json
{
  "source_url": "https://www.popmart.com/us/products/labubu-art-series",
  "attributes": {
    "source_attribution": "Product information from Pop Mart official website"
  }
}
```

### In Application UI
**Display attribution:**
- Link to source page
- "Data from [Source Name]"
- "Images courtesy of [Manufacturer]"

---

## Ethical Decision Framework

### Ask yourself:
1. **Would I do this as a regular user?**
   - If yes → Probably ethical
   - If no → Probably not ethical

2. **Am I straining their servers?**
   - If yes → Slow down
   - If no → OK to proceed

3. **Am I copying creative work?**
   - If yes → Don't do it
   - If no (factual data only) → OK

4. **Would I feel comfortable telling them what I'm doing?**
   - If yes → Probably ethical
   - If no → Reconsider approach

5. **Does this align with DBoT's mission?**
   - Preservation: ✅
   - Attribution: ✅
   - Community benefit: ✅
   - Respect for sources: ✅

---

## Manual Curation Workflow

### Initial Dataset (50-100 items)

**Week 1: Research & Planning**
1. Identify 50-100 most popular Labubu figures
2. Find official sources for each
3. Check robots.txt for all sources
4. Create spreadsheet for tracking

**Week 2: Data Collection**
5. Manually visit each product page
6. Record factual information in spreadsheet
7. Note source URLs
8. Flag images that are available from official sources

**Week 3: Data Entry**
9. Enter data into database
10. Generate embeddings for search
11. Download and host official images (with attribution)
12. Verify data accuracy

**Week 4: Review & Document**
13. Review dataset for completeness
14. Document sources and attribution
15. Create "Sources" page for transparency
16. Plan next batch if successful

### Spreadsheet Template

```csv
name,series,year,size,manufacturer,source_url,image_url,notes
"Labubu - Mona Lisa","Art Series",2023,"3-4 inches","Pop Mart","https://...","https://...","Official Pop Mart product page"
```

---

## When in Doubt

### Safe Defaults:
1. **Don't copy creative content** (descriptions, reviews)
2. **Only factual information** (names, dates, dimensions)
3. **Always attribute** (source_url required)
4. **Respect robots.txt** (no exceptions)
5. **Manual only** (no automated scripts)
6. **Ask permission** (contact manufacturers/retailers)
7. **Skip images** (if source is unclear, leave NULL)

### Red Flags to STOP:
❌ Site explicitly prohibits data collection
❌ Robots.txt blocks access
❌ ToS says "no commercial use" (DBoT has paid features)
❌ Content is clearly copyrighted (descriptions, photos)
❌ You feel uncomfortable explaining what you're doing

---

## Legal Safe Harbors

### Facts Are Not Copyrightable
**Safe to catalog:**
- "This figure is named 'Labubu - Mona Lisa'"
- "It was released in 2023"
- "It measures 3-4 inches"
- "It's part of the Art Series"
- "Manufactured by Pop Mart"

**These are facts, not creative expression.**

### Fair Use Considerations
**Using product names:** Generally OK (nominative fair use)
**Using product images:** More complex
- Official promotional images: Likely OK with attribution
- User photos: Need permission
- Third-party photos: Usually not OK without permission

---

## Transparency & Documentation

### Create "Sources" Page
Document where data comes from:
```markdown
# Data Sources

## Labubu / Pop Mart Designer Toys

**Primary Source:** Pop Mart Official Website (popmart.com)
- Method: Manual curation of product pages
- Data collected: Product names, series, release dates, sizes
- Images: Official product images used with attribution
- Last updated: [Date]

**Attribution:** Product information courtesy of Pop Mart.
Images are promotional materials provided by manufacturer.
```

### Per-Entity Attribution
Every entity links to source:
- `source_url` field always populated
- Users can verify information
- Transparent provenance

---

## Community Contribution Model (Future)

### Why This Is Ultimate Solution
1. **Explicit permission** (users grant license)
2. **Community ownership** (users proud to contribute)
3. **Scalable** (crowdsourced data collection)
4. **Compliant** (no legal grey areas)

### Implementation
```
User uploads:
├─ Photo (they took themselves)
├─ Information (they researched)
└─ License grant (explicit checkbox)
    "I grant DBoT permission to use this photo and information"
```

---

## Summary: Ethical Manual Curation Checklist

Before curating from any source:
- [ ] Check robots.txt - No blocks?
- [ ] Review ToS - No prohibitions?
- [ ] Public information - Not behind login?
- [ ] Factual data only - No creative content?
- [ ] Will attribute source - source_url ready?
- [ ] Normal user behavior - Not straining servers?
- [ ] Would feel comfortable explaining - To source owner?

If all YES → Proceed with manual curation
If any NO → Stop and reconsider approach

---

**Remember:** When in doubt, err on the side of caution. It's better to wait for explicit permission or community contributions than to risk legal issues.

**The goal:** Build an ethical, transparent, community-valued resource that respects all sources and contributors.

---

**Last Updated:** November 14, 2025
**Next Review:** Quarterly or when sources change
