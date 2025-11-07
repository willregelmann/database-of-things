# Power Rangers Toys Curator Plan

## Collection
- **Type:** Action figures, Zords, Megazords, playsets, and accessories
- **Parent Collection ID:** `d183e3a9-4eb7-40a5-b264-526b9a03ec30` (Power Rangers franchise)
- **Organization:** Hierarchical by series (MMPR → Zeo → Turbo → etc.)

## Data Sources
- **Primary:** GrnRngr.com (https://www.grnrngr.com/toys/power-rangers/)
- **Authentication:** None required (public catalog)
- **Method:** Web scraping with Beautiful Soup
- **Data Quality:** 233,480+ pieces of data, comprehensive catalog with images, item numbers, prices, release dates

## Target Structure

```
Power Rangers (franchise)
├── Mighty Morphin Power Rangers (series)
│   ├── Red Ranger Action Figure (toy)
│   ├── Megazord (toy)
│   └── ...
├── Power Rangers Zeo (series)
│   ├── Gold Ranger Action Figure (toy)
│   └── ...
└── ...
```

## Import Workflow

1. **Fetch season list** from grnrngr.com main Power Rangers page
2. **For each season/toyline:**
   - Create series entity if doesn't exist (e.g., "Mighty Morphin Power Rangers")
   - Link series to Power Rangers franchise with "contains" relationship
3. **Scrape toy entries** from each season page
4. **Parse toy data:**
   - Item number (e.g., "2200") → `external_ids.grnrngr`
   - Name (e.g., "Jason Red Ranger")
   - Image URL (e.g., `/toys/pictures/bandai/02200_1.jpg`)
   - Release date (e.g., "[Fall 1993]") → extract year
   - Price (e.g., "SRP: $14.99")
   - UPC/barcode
5. **Deduplicate** using item number: `external_ids.grnrngr`
6. **Import to database:**
   - Create entity for each toy
   - Link to series with "contains" relationship

## Deduplication Strategy

- **Key:** Item number in `external_ids.grnrngr` (e.g., "2200")
- **Method:** Check if entity exists with matching `external_ids->>'grnrngr'` value
- **Rationale:** Item numbers are unique identifiers assigned by manufacturers, providing reliable deduplication

## Data Model

**Series entity:**
```json
{
  "type": "series",
  "name": "Mighty Morphin Power Rangers",
  "year": 1993,
  "attributes": {
    "description": "The original Power Rangers series",
    "abbreviation": "MMPR"
  }
}
```

**Toy entity:**
```json
{
  "type": "toy",
  "name": "Jason Red Ranger",
  "year": 1993,
  "image_url": "https://www.grnrngr.com/toys/pictures/bandai/02200_1.jpg",
  "external_ids": {
    "grnrngr": "2200",
    "upc": "045557022009"
  },
  "attributes": {
    "item_number": "2200",
    "release_date": "Fall 1993",
    "price": "$9.99",
    "manufacturer": "Bandai America",
    "photo_url": "/toys/pictures/bandai/02200_1.jpg",
    "barcode_url": "/toys/upcs/bandai/04555702200.png"
  }
}
```

## Technical Notes

- grnrngr.com uses definition list HTML structure (`<dl>`, `<dt>`, `<dd>`)
- Rate limiting: 1 request per second to be respectful
- Images hosted on grnrngr.com, can be linked directly (e.g., https://www.grnrngr.com/toys/pictures/bandai/02200_1.jpg)
- Item numbers are unique identifiers for reliable deduplication
- Release dates need parsing (e.g., "[Fall 1993]" → year: 1993)
- Prices need parsing (e.g., "SRP: $14.99" → "$14.99")
- Instructions PDFs available for many toys
