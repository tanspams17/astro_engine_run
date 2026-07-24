# vendor/rg_cities1000.csv

Worldwide populated-places gazetteer (~144k rows: lat, lon, name, admin1,
admin2, country code), sourced from the `reverse_geocoder` PyPI package
(https://pypi.org/project/reverse-geocoder/, MIT-licensed code — the data
itself is a derivative of the GeoNames geographical database, CC BY 4.0,
https://www.geonames.org/). Vendored here (rather than installing the
`reverse_geocoder` package, which pulls in scipy/scikit-learn just to read
this file) so `regen_assets.py` can rebuild `frontend/cities.json`
offline and reproducibly. Used only at build time, never at runtime.
