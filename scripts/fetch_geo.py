#!/usr/bin/env python3
"""
fetch_geo.py  -  Download Geoscience Australia electricity infrastructure as GeoJSON.

Source (validated Sept 2026):
  https://services.ga.gov.au/gis/rest/services/Electricity_Infrastructure/MapServer
     layer 0 = Substations        (fields: FEATURE_NAME, VOLTAGE_KV, STATUS, STATE, LOCALITY, ...)
     layer 1 = Major Power Stations
     layer 2 = Power Lines        (fields: FEATURE_NAME, CAPACITY_KV, STATUS, STATE, FEATURE_SUBTYPE, ...)
  Licence: CC BY 4.0, (c) Commonwealth of Australia (Geoscience Australia) 2026.
  maxRecordCount = 2000, supportsPagination = true, formats: json / geojson / pbf.

Outputs (written to argv[1]):
  transmission_lines.geojson   Power Lines, CAPACITY_KV >= 132 AND STATUS = 'Operational'
  substations.geojson          Substations, VOLTAGE_KV >= 132   (all statuses; STATUS kept as a property)

Strategy
  1. Page through <layer>/query with resultOffset / resultRecordCount (PAGE_SIZE, default 1000)
     until exceededTransferLimit is false or a short page is returned.
     f=geojson is requested first; if the server (or a proxy) refuses it, f=json (Esri JSON)
     is requested and converted to GeoJSON locally.
  2. If the REST service is unreachable, fall back to the ArcGIS Hub bulk download that the
     Digital Atlas of Australia exposes (one big GeoJSON per layer, supports a `where` filter):
       https://hub.arcgis.com/api/v3/datasets/<itemid>_<layer>/downloads/data?format=geojson&spatialRefId=4326&where=...
  3. Coordinates are rounded to 5 decimals (~1 m) and empty / null geometries dropped.

Only the standard library is used (urllib). Set env GA_BASE to point at another ArcGIS MapServer
(used by the offline mock test) and GA_PAGE_SIZE to change the page size.

Also fetches (best effort) TeleGeography's public submarine-cable geometry and Australian landing points:
  submarine_cables.geojson     cables with at least one Australian landing point
  (source: https://www.submarinecablemap.com/api/v3/ — (c) TeleGeography, for reference display only)

Usage:  python3 fetch_geo.py [/path/to/output_dir]      (default: site/data/geo)
Blocked network? The GitHub Actions workflow runs this for you (see .github/workflows/build-deploy.yml).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GA_BASE = os.environ.get(
    "GA_BASE",
    "https://services.ga.gov.au/gis/rest/services/Electricity_Infrastructure/MapServer",
)
PAGE_SIZE = int(os.environ.get("GA_PAGE_SIZE", "1000"))  # server cap is 2000; 1000 keeps responses small
TIMEOUT = 120
USER_AGENT = "au-dc-infra-map/1.0 (+python-urllib)"

# Digital Atlas of Australia Hub item ids (for the bulk-download fallback)
HUB_ITEMS = {
    0: "d5eae2d7c9e54581a5f19d7e95b9883b",  # Substations
    2: "70f23e91102a4d6899a776d093fa08ef",  # Power Lines
}

LAYERS = [
    {
        "layer": 2,
        "outfile": "transmission_lines.geojson",
        "where": "CAPACITY_KV >= 132 AND STATUS = 'Operational'",
        "out_fields": "FEATURE_NAME,FEATURE_SUBTYPE,CAPACITY_KV,STATUS,STATE,FEATURE_SOURCE,ATTRIBUTE_SOURCE_DATE",
        "pretty_name": "Power Lines (>=132 kV, operational)",
    },
    {
        "layer": 0,
        "outfile": "substations.geojson",
        "where": "VOLTAGE_KV >= 132",
        "out_fields": "FEATURE_NAME,VOLTAGE_KV,STATUS,STATE,LOCALITY,FEATURE_SOURCE,ATTRIBUTE_SOURCE_DATE",
        "pretty_name": "Substations (>=132 kV)",
    },
]


# --------------------------------------------------------------------------- HTTP helpers
def http_get_json(url, retries=3, backoff=2.0):
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict) and "error" in data:
                raise RuntimeError("ArcGIS error: %s" % json.dumps(data["error"])[:300])
            return data
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise last_err


def query_url(layer, params):
    return "%s/%d/query?%s" % (GA_BASE, layer, urllib.parse.urlencode(params))


# --------------------------------------------------------------------------- geometry helpers
def round_coords(coords, nd=5):
    if isinstance(coords, (int, float)):
        return round(coords, nd)
    return [round_coords(c, nd) for c in coords]


def esri_to_geojson_geometry(geom):
    """Convert an Esri JSON geometry (WGS84) to a GeoJSON geometry."""
    if not geom:
        return None
    if "x" in geom and "y" in geom:
        if geom["x"] is None or geom["y"] is None:
            return None
        return {"type": "Point", "coordinates": [geom["x"], geom["y"]]}
    if "paths" in geom:
        paths = [p for p in geom["paths"] if p]
        if not paths:
            return None
        if len(paths) == 1:
            return {"type": "LineString", "coordinates": paths[0]}
        return {"type": "MultiLineString", "coordinates": paths}
    if "rings" in geom:
        rings = [r for r in geom["rings"] if r]
        if not rings:
            return None
        return {"type": "Polygon", "coordinates": rings}
    if "points" in geom:
        return {"type": "MultiPoint", "coordinates": geom["points"]}
    return None


def esri_featureset_to_geojson(fs):
    feats = []
    for f in fs.get("features", []):
        g = esri_to_geojson_geometry(f.get("geometry"))
        if g is None:
            continue
        feats.append({"type": "Feature", "geometry": g, "properties": f.get("attributes", {})})
    return feats


def normalise_feature(f):
    """Round coordinates, lower-case property keys, drop features without geometry."""
    g = f.get("geometry")
    if not g or g.get("coordinates") in (None, []):
        return None
    g["coordinates"] = round_coords(g["coordinates"])
    props = {}
    for k, v in (f.get("properties") or {}).items():
        props[k.lower()] = v
    return {"type": "Feature", "geometry": g, "properties": props}


# --------------------------------------------------------------------------- paging download
def fetch_layer_paged(layer, where, out_fields):
    """Page through the REST query endpoint. Returns list of GeoJSON features (unrounded)."""
    features = []
    offset = 0
    use_geojson = True
    while True:
        params = {
            "where": where,
            "outFields": out_fields,
            "returnGeometry": "true",
            "outSR": 4326,
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "orderByFields": "OBJECTID",
            "f": "geojson" if use_geojson else "json",
        }
        url = query_url(layer, params)
        try:
            data = http_get_json(url)
        except Exception as e:  # noqa: BLE001
            if use_geojson:
                # some proxies / older servers refuse geo+json; fall back to Esri JSON
                sys.stderr.write("  f=geojson failed (%s); retrying with f=json\n" % str(e)[:120])
                use_geojson = False
                continue
            raise

        if use_geojson:
            page = data.get("features", [])
            exceeded = bool(data.get("exceededTransferLimit")) or bool(
                (data.get("properties") or {}).get("exceededTransferLimit")
            )
        else:
            page = esri_featureset_to_geojson(data)
            exceeded = bool(data.get("exceededTransferLimit"))

        features.extend(page)
        sys.stderr.write("  layer %d offset %d -> %d features (exceeded=%s)\n" % (layer, offset, len(page), exceeded))
        if not page or (len(page) < PAGE_SIZE and not exceeded):
            break
        offset += len(page)
        if offset > 200000:  # safety valve
            break
    return features


def fetch_layer_hub_bulk(layer, where):
    """Fallback: Digital Atlas / ArcGIS Hub bulk GeoJSON download (single file, supports where=)."""
    item = HUB_ITEMS.get(layer)
    if not item:
        raise RuntimeError("no Hub item id known for layer %d" % layer)
    # NOTE: Hub only serves its pre-built cache for where=1=1 (a custom `where` returns 404),
    # so the whole layer is downloaded (Power Lines ~3.1k features / ~9 MB, Substations ~1.9k)
    # and the voltage/status filter is applied locally in local_filter().
    url = "https://hub.arcgis.com/api/v3/datasets/%s_%d/downloads/data?%s" % (
        item,
        layer,
        urllib.parse.urlencode({"format": "geojson", "spatialRefId": 4326, "where": "1=1"}),
    )
    sys.stderr.write("  Hub bulk download: %s\n" % url)
    data = http_get_json(url, retries=2)
    return data.get("features", [])


def local_filter(features, layer):
    """Re-apply the voltage/status filter locally (Hub download may ignore `where`)."""
    out = []
    for f in features:
        p = {k.lower(): v for k, v in (f.get("properties") or {}).items()}
        if layer == 2:
            kv = p.get("capacity_kv")
            if kv is None or kv < 132 or (p.get("status") or "") != "Operational":
                continue
        elif layer == 0:
            kv = p.get("voltage_kv")
            if kv is None or kv < 132:
                continue
        out.append(f)
    return out


def fetch_layer(spec):
    layer = spec["layer"]
    sys.stderr.write("Fetching %s ...\n" % spec["pretty_name"])
    try:
        feats = fetch_layer_paged(layer, spec["where"], spec["out_fields"])
        source = "%s/%d/query" % (GA_BASE, layer)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("  REST query failed: %s\n  -> trying Hub bulk download\n" % str(e)[:200])
        feats = fetch_layer_hub_bulk(layer, spec["where"])
        source = "hub.arcgis.com bulk download"
    feats = local_filter(feats, layer)
    out = []
    for f in feats:
        nf = normalise_feature(f)
        if nf:
            out.append(nf)
    return out, source


def write_geojson(path, features, spec, source):
    fc = {
        "type": "FeatureCollection",
        "name": os.path.splitext(os.path.basename(path))[0],
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "metadata": {
            "source": source,
            "dataset": "Geoscience Australia - Electricity Infrastructure (Digital Atlas of Australia)",
            "licence": "CC BY 4.0 - (c) Commonwealth of Australia (Geoscience Australia)",
            "filter": spec["where"],
            "retrieved": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "feature_count": len(features),
        },
        "features": features,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))
    return os.path.getsize(path)


TG = "https://www.submarinecablemap.com/api/v3"


def fetch_submarine_cables(out_dir):
    """Cables touching Australia + their landing points, as one GeoJSON FeatureCollection."""
    sys.stderr.write("Fetching TeleGeography submarine cables (Australia) ...\n")
    country = http_get_json(TG + "/country/australia.json", retries=2)
    cable_ids = {c["id"] for c in country.get("cables", [])}
    geo = http_get_json(TG + "/cable/cable-geo.json", retries=2)
    lps = http_get_json(TG + "/landing-point/landing-point-geo.json", retries=2)
    feats = []
    for f in geo.get("features", []):
        if f.get("properties", {}).get("id") in cable_ids:
            nf = normalise_feature({"geometry": f["geometry"], "properties": {"kind": "cable", **f["properties"]}})
            if nf:
                feats.append(nf)
    for f in lps.get("features", []):
        p = f.get("properties", {})
        if "Australia" in (p.get("name") or ""):
            nf = normalise_feature({"geometry": f["geometry"], "properties": {"kind": "landing_point", **p}})
            if nf:
                feats.append(nf)
    path = os.path.join(out_dir, "submarine_cables.geojson")
    fc = {"type": "FeatureCollection", "name": "submarine_cables",
          "metadata": {"source": TG, "dataset": "TeleGeography Submarine Cable Map (public API)",
                       "licence": "(c) TeleGeography - reference display only, check terms before redistribution",
                       "retrieved": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "feature_count": len(feats)},
          "features": feats}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))
    print("%-28s %6d features  %8.1f KB  -> %s" % ("submarine_cables.geojson", len(feats), os.path.getsize(path) / 1024.0, path))


def main(argv):
    default_out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site", "data", "geo")
    out_dir = argv[1] if len(argv) > 1 else default_out
    os.makedirs(out_dir, exist_ok=True)
    rc = 0
    for spec in LAYERS:
        try:
            feats, source = fetch_layer(spec)
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("FAILED %s: %s\n" % (spec["pretty_name"], e))
            rc = 1
            continue
        path = os.path.join(out_dir, spec["outfile"])
        size = write_geojson(path, feats, spec, source)
        print("%-28s %6d features  %8.1f KB  -> %s" % (spec["outfile"], len(feats), size / 1024.0, path))
    try:
        fetch_submarine_cables(out_dir)
    except Exception as e:  # noqa: BLE001 - optional layer, never fail the build for it
        sys.stderr.write("submarine cables skipped: %s\n" % str(e)[:200])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
