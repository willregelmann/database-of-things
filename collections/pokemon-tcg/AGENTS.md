# Pokémon TCG — curation hints

## Identifying items

Cards are identified by their **collector number within a set**, formatted as
`number/total` (e.g. `4/102`). This is the single most reliable disambiguator —
prefer it over name matching, since many cards share a name across sets (multiple
"Charizard" printings exist across dozens of sets) and even within a set via
reprints/alt-art variants.

## Verifying a set is complete

A set's total card count is public and fixed (encoded in every card's `number`
field, e.g. `.../102`). To check completeness:
1. Read any card's `number` field to get the set total.
2. Confirm that many distinct numbers 1..N exist as entity files in the set
   directory.
3. Cross-reference the full checklist against an authoritative source (Bulbapedia,
   Pokémon TCG API, or Serebii) rather than assuming — some sets have secret rares
   numbered above the printed total (e.g. `103/102`).

## Naming files

`<slugified-name>-<number>-<total>.yaml`, e.g. `charizard-4-102.yaml`. Reprints of
the same name within a set get disambiguated by number, which is already unique.

## Common pitfalls

- Don't confuse a set's *TCG expansion name* with its *physical product name*
  (booster box vs. theme deck exclusives) — the set directory should represent the
  expansion, not a retail SKU.
- Promo cards are not part of any numbered set — they belong in a separate
  `promos` collection, not shoehorned into the nearest numbered set.
- Rarity naming should follow the modern Pokémon TCG conventions (`Common`,
  `Uncommon`, `Rare`, `Holo Rare`, `Rare Holo EX`, etc.) — don't invent new labels.
