from __future__ import annotations
from typing import Any, Dict, List, Tuple
import csv
import io
import json


def normalize_lat_lon_keys(header: List[str]) -> Dict[str, str]:
	normalized = [h.strip().lower() for h in header]
	key_map: Dict[str, str] = {}
	lat_candidates = {"lat", "latitude", "y"}
	lon_candidates = {"lon", "lng", "long", "longitude", "x"}
	for idx, name in enumerate(normalized):
		original = header[idx]
		if name in lat_candidates and "lat" not in key_map:
			key_map["lat"] = original
		if name in lon_candidates and "lon" not in key_map:
			key_map["lon"] = original
	return key_map


def validate_coordinate(lat: float, lon: float) -> bool:
	return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def parse_csv_points(file_bytes: bytes) -> List[Dict[str, Any]]:
	text = file_bytes.decode("utf-8-sig")
	reader = csv.DictReader(io.StringIO(text))
	if not reader.fieldnames:
		raise ValueError("CSV has no header")
	key_map = normalize_lat_lon_keys(reader.fieldnames)
	if "lat" not in key_map or "lon" not in key_map:
		raise ValueError("CSV must contain latitude and longitude columns")

	points: List[Dict[str, Any]] = []
	for row in reader:
		try:
			lat = float(row[key_map["lat"]])
			lon = float(row[key_map["lon"]])
		except Exception:
			continue
		if not validate_coordinate(lat, lon):
			continue
		attrs = {k: v for k, v in row.items() if k not in (key_map["lat"], key_map["lon"])}
		points.append({"lat": lat, "lon": lon, "attributes": attrs})
	return points


def parse_geojson_points(file_bytes: bytes) -> List[Dict[str, Any]]:
	try:
		data = json.loads(file_bytes.decode("utf-8"))
	except Exception as e:
		raise ValueError("Invalid GeoJSON") from e
	if data.get("type") != "FeatureCollection":
		raise ValueError("Only FeatureCollection is supported")
	features = data.get("features", [])
	points: List[Dict[str, Any]] = []
	for feat in features:
		geom = feat.get("geometry") or {}
		if geom.get("type") != "Point":
			continue
		coords = geom.get("coordinates") or []
		if not isinstance(coords, (list, tuple)) or len(coords) < 2:
			continue
		lon, lat = float(coords[0]), float(coords[1])
		if not validate_coordinate(lat, lon):
			continue
		attrs = feat.get("properties") or {}
		points.append({"lat": lat, "lon": lon, "attributes": attrs})
	return points


def compute_bbox(points: List[Dict[str, Any]]) -> Dict[str, float]:
	if not points:
		raise ValueError("No valid points found")
	min_lat = min(p["lat"] for p in points)
	max_lat = max(p["lat"] for p in points)
	min_lon = min(p["lon"] for p in points)
	max_lon = max(p["lon"] for p in points)
	return {"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon}


