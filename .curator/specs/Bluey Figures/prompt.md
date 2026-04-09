# Bluey Figures Curator

Fetch Bluey figures and playsets from the Blueypedia Fandom wiki and import them into the database.

## Data Source

Blueypedia (https://blueypedia.fandom.com) — the Bluey fan wiki on Fandom.

No API key required. Use the Fandom MediaWiki API.

Key requests:
- **Wikitext for section 1** (Figurines and Playsets):
  `GET https://blueypedia.fandom.com/api.php?action=parse&page=List_of_Toys_Merchandise&prop=wikitext&section=1&format=json`
- **Resolve image URL** (for each `File:` reference):
  `GET https://blueypedia.fandom.com/api.php?action=query&titles=File:{filename}&prop=imageinfo&iiprop=url&format=json`

## Hierarchy

All figures go directly under COLLECTION_ID — no sub-collections needed. The set is small enough (~100 items) to be flat.

```
Bluey Figures (top-level collection — this is COLLECTION_ID)
└── Figure/Playset (item)  e.g. "Bluey Family Picnic Set"
```

## Parsing the Wikitext

The section contains one or more `<gallery>` blocks. **Parse only the first gallery** (product figures), skip subsequent ones (packaging/boxes).

Gallery format:
```
<gallery widths="185">
File:BlueyFamilyPicnicSet.jpg|Bluey Family Picnic Set
File:SomeProduct.png|Product Name <small>(note)</small>
</gallery>
```

For each line:
1. Split on first `|` to get `filename` and `caption`
2. Clean caption: remove `<small>...</small>` annotations, strip wiki link markup `[[text|display]]` → `display`
3. Skip lines with empty captions after cleaning

Then for each item, resolve the image URL via the `imageinfo` API call using the filename.

## Entity Schema

### Figure/Playset (type: "item", category: "figures")

```json
{
  "name": "Bluey Family Picnic Set",
  "type": "item",
  "category": "figures",
  "image_url": "https://static.wikia.nocookie.net/blueypedia/images/...",
  "source_url": "https://blueypedia.fandom.com/wiki/List_of_Toys_Merchandise",
  "external_ids": {
    "blueypedia_title": "Bluey Family Picnic Set"
  },
  "attributes": {
    "manufacturer": "Moose Toys"
  }
}
```

No parent needed — items import directly into COLLECTION_ID.

## Rate Limiting

Wait 1 second between image URL resolution requests. The wikitext fetch is a single request; image resolution requires one request per item.

## Import

Single batch (dataset is small):

```
entities_upsert(collection_id=COLLECTION_ID, items=[...all figures...])
```
