# Far From Home

Where were the Victoria Crosses won, where were their recipients born, and how far apart were the two? Birthplaces for {{counts.birth_coords|int}} of {{counts.recipients|int}} recipients, a located place of action for {{counts.place_precise|int}} of {{counts.awards|int}} awards, and the distance from home to the deed.

**Interactive version:** https://tristan-hotham.github.io/victoria-cross/

This repository holds the interactive page, the per-award data and the analysis code for the data study *Far from Home: where the Victoria Cross was won and where its recipients were born* by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

## Headline results

- {{counts.awards|int}} Victoria Crosses to {{counts.recipients|int}} named recipients ({{counts.bars|int}} people won it twice), for deeds from {{counts.first_year|raw}} to {{counts.last_year|raw}}. {{groups.3.awards|int}} ({{ww1_share|pct0}}) were for the First World War; the busiest year was {{peak_year.year|raw}}, with {{peak_year.awards|int}}.
- {{birth_totals.England|int}} recipients ({{birth_share.England|pct0}}) were born in England, {{birth_totals.Scotland|int}} in Scotland, {{birth_totals.Wales|int}} in Wales and {{ireland.n|int}} ({{ireland.share|pct0}}) on the island of Ireland.
- The Irish-born share fell from {{irish_share_by_group.mutiny|pct0}} of Indian Mutiny awards to {{irish_share_by_group.ww2|pct0}} in the Second World War, while the share born in Australia, Canada, New Zealand and southern Africa rose from {{dominion_share_by_group.crimea|pct0}} in the Crimean War to {{dominion_share_by_group.ww2|pct0}}.
- The located places of action cluster at Ypres ({{hot.ypres.n|int}} awards), the Somme ({{hot.somme.n|int}}), Lucknow ({{hot.lucknow.n|int}}), Sevastopol ({{hot.sevastopol.n|int}}) and Delhi ({{hot.delhi.n|int}}).
- For the {{distance.n|int}} awards with both ends located, the median distance from birthplace to deed is {{distance.median|int}} km; reweighted to the full list's mix of birthplaces and conflicts, about {{distance.adjusted_median|int}} km. English-born First World War recipients with a located place: median {{ww1_distance_by_birth.England.median|int}} km. Australians: {{ww1_distance_by_birth.Australia.median|int}} km.
- {{lancashire.n|int}} recipients were born in today's Lancashire, Greater Manchester and Merseyside.

## Files

- `index.html`: the interactive page (Leaflet map, charts).
- `header.png`: social card.
- `data/vc_awards.csv`: one row per award, with rank, unit, campaign, conflict group, year, birthplace (Wikidata id, coordinates, country, GB county), place of action (text, coordinates, how it was located and the source), region of the deed and distance.
- `data/vc_actions.csv`: the joined table before cleaning, as written by step 2.
- `data/place_geocoding.csv`: every place-of-action entry in the six national lists, with the method used to locate it (Wikipedia link, Wikipedia title, GeoNames, Wikidata battle, region only or unmatched), the matched record and its URL.
- `data/birth_places.csv`, `data/birth_counties_gb.csv`: birthplaces and GB counties with counts.
- `data/hotspots.csv`: located places of action grouped within {{hotspot_radius|raw}} km.
- `data/flows.geojson`: a line from birthplace to place of action for each award where both are located.
- `data/results.json`: every number quoted on the page, in the paper and in the blog post.
- `code/`: Python scripts, run in order: `00_world.py`, `01_parse_lists.py`, `02_join_geocode.py`, `03_analyse.py`, `04_build_site.py`, `05_header.py`. The source files are not included (see below); the scripts expect them in `../_data2/`.

## Method in brief

The master list is the three Wikipedia tables "List of Victoria Cross recipients (A to F)", "(G to M)" and "(N to Z)". Birthplaces come from Wikidata, joined through each recipient's English Wikipedia article ({{counts.wikidata_matched|int}} matched). The main tables do not give a place of action, so places come from the six national lists that do (Irish, Indian Army, Australian, Canadian, New Zealand and by nationality), geocoded through the linked Wikipedia articles' coordinates (checked against the stated country), exact article titles, GeoNames towns of 1,000 or more people (unambiguous within the stated country) or Wikidata battles, plus {{counts.place_from_wikidata|int}} awards whose Wikidata record names a single specific battle. Of {{geocoding.rows|int}} national-list places, {{geocoding.precise|int}} were located to a named place, {{geocoding.region|int}} only to a region and {{geocoding.unmatched|int}} not at all.

Caveats: located places over-represent Irish-born, Indian Army and dominion recipients ({{distance_subset_share.Ireland|pct0}} of located awards are Irish-born against {{all_share.Ireland|pct0}} of all awards); the adjusted median corrects only for birthplace group and conflict period. Birthplaces inherit Wikidata's errors and are not always home. Counties are today's. There are no per-head rates because historical county populations were not available.

## Sources and licence

- Wikipedia: List of Victoria Cross recipients (A to F, G to M, N to Z); List of Irish Victoria Cross recipients; List of Victoria Cross recipients of the Indian Army; List of Australian, Canadian and New Zealand Victoria Cross recipients; List of Victoria Cross recipients by nationality. Text and tables CC BY-SA 4.0. Coordinates of linked articles from the Wikipedia API.
- Wikidata (CC0): recipients of the Victoria Cross (Q219578), place of birth, coordinates, conflicts, battles.
- GeoNames cities1000 (CC BY 4.0), https://www.geonames.org/
- Natural Earth 1:50m Admin 0 countries (public domain), via github.com/nvkelso/natural-earth-vector.
- GB county boundaries: Office for National Statistics, Open Government Licence v3.
- Base map tiles on the page: Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community. Map library: Leaflet.

Because the Wikipedia lists are CC BY-SA 4.0, the derived data and the page text are released under CC BY-SA 4.0. Code is MIT (see `LICENSE`).

## Citation

Hotham, T. (2026) *Far from Home: where the Victoria Cross was won and where its recipients were born.* Zenodo. https://doi.org/{{doi|raw}}

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
