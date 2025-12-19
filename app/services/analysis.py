from __future__ import annotations
from typing import Any, Dict, List, Tuple
from collections import Counter, defaultdict
import math

import numpy as np
from sklearn.cluster import DBSCAN


EARTH_RADIUS_KM = 6371.0088


def compute_summary(points: List[Dict[str, Any]], category_field: str | None = "category") -> Dict[str, Any]:
	n = len(points)
	if n == 0:
		return {"total_points": 0, "bbox": None, "mean_center": None, "category_counts": {}}
	lats = np.array([p["lat"] for p in points], dtype=float)
	lons = np.array([p["lon"] for p in points], dtype=float)
	bbox = {
		"min_lat": float(lats.min()),
		"max_lat": float(lats.max()),
		"min_lon": float(lons.min()),
		"max_lon": float(lons.max()),
	}
	mean_center = {"lat": float(lats.mean()), "lon": float(lons.mean())}
	category_counts: Dict[str, int] = {}
	if category_field:
		values = []
		for p in points:
			attrs = p.get("attributes") or {}
			if category_field in attrs:
				values.append(str(attrs[category_field]))
		category_counts = dict(Counter(values))
	return {"total_points": n, "bbox": bbox, "mean_center": mean_center, "category_counts": category_counts}


def grid_density(points: List[Dict[str, Any]], grid_cell_size: float) -> Dict[str, Any]:
	if not points:
		return {"grid_cell_size": grid_cell_size, "cells": [], "bbox": None}
	min_lat = min(p["lat"] for p in points)
	max_lat = max(p["lat"] for p in points)
	min_lon = min(p["lon"] for p in points)
	max_lon = max(p["lon"] for p in points)

	def cell_index(lat: float, lon: float) -> Tuple[int, int]:
		i = int(math.floor((lat - min_lat) / grid_cell_size))
		j = int(math.floor((lon - min_lon) / grid_cell_size))
		return i, j

	counts: Dict[Tuple[int, int], int] = defaultdict(int)
	for p in points:
		idx = cell_index(p["lat"], p["lon"])
		counts[idx] += 1

	cells = []
	for (i, j), count in counts.items():
		cell_min_lat = min_lat + i * grid_cell_size
		cell_min_lon = min_lon + j * grid_cell_size
		cell_max_lat = cell_min_lat + grid_cell_size
		cell_max_lon = cell_min_lon + grid_cell_size
		cells.append(
			{
				"min_lat": cell_min_lat,
				"max_lat": cell_max_lat,
				"min_lon": cell_min_lon,
				"max_lon": cell_max_lon,
				"count": count,
			}
		)
	return {
		"grid_cell_size": grid_cell_size,
		"bbox": {"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon},
		"cells": cells,
	}


def dbscan_clustering(
	points: List[Dict[str, Any]],
	eps_km: float | None,
	min_samples: int,
	eps_degrees: float | None = None,
) -> Dict[str, Any]:
	if not points:
		return {"labels": [], "clusters": [], "num_clusters": 0, "num_noise": 0}

	coords_deg = np.array([[p["lat"], p["lon"]] for p in points], dtype=float)

	if eps_km is not None:
		coords_rad = np.radians(coords_deg)
		eps = eps_km / EARTH_RADIUS_KM
		model = DBSCAN(eps=eps, min_samples=min_samples, metric="haversine")
		labels = model.fit_predict(coords_rad)
	else:
		eps = eps_degrees if eps_degrees is not None else 0.01
		model = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean")
		labels = model.fit_predict(coords_deg)

	labels_list = labels.tolist()

	# Aggregate clusters
	cluster_to_points: Dict[int, List[int]] = defaultdict(list)
	for idx, lab in enumerate(labels_list):
		if lab != -1:
			cluster_to_points[lab].append(idx)

	clusters = []
	for lab, indices in cluster_to_points.items():
		cluster_coords = coords_deg[indices]
		centroid = {"lat": float(cluster_coords[:, 0].mean()), "lon": float(cluster_coords[:, 1].mean())}
		clusters.append({"cluster_id": int(lab), "size": len(indices), "centroid": centroid})

	num_noise = int((labels == -1).sum())
	return {
		"labels": labels_list,
		"clusters": clusters,
		"num_clusters": len(clusters),
		"num_noise": num_noise,
	}


