#!/usr/bin/env python
"""Expose Intersight inventory metrics to Prometheus."""

import argparse
import json
import logging
import time
from typing import Dict

from intersight.apis import (
    compute_blade_api,
    compute_physical_summary_api,
    compute_rack_unit_api,
    hyperflex_cluster_api,
    hyperflex_health_api,
)
from intersight.intersight_api_client import IntersightApiClient
from prometheus_client import Gauge, start_http_server


HEALTH_STATUS = {
    "UNKNOWN": 0,
    "ONLINE": 1,
    "OFFLINE": 2,
    "ENOSPACE": 3,
    "READONLY": 4,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish Intersight inventory metrics to Prometheus.",
    )
    parser.add_argument(
        "-t",
        "--pooltime",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Port to bind the HTTP exporter (default: 8000)",
    )
    parser.add_argument(
        "-a",
        "--api_params",
        default="intersight_api_params.json",
        help="JSON file with Intersight API parameters",
    )
    return parser.parse_args()


def load_api_params(path: str) -> Dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as api_file:
            params = json.load(api_file)
    except OSError as exc:  # pragma: no cover - runtime guard
        logging.error("Unable to open API configuration file: %s", path)
        raise SystemExit(exc) from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - runtime guard
        logging.error("Invalid JSON in API configuration file: %s", path)
        raise SystemExit(exc) from exc

    for key in ("api_base_uri", "api_private_key_file", "api_key_id"):
        if key not in params:
            raise SystemExit(f"Missing required API parameter: {key}")

    return params


def create_api_client(params: Dict[str, str]) -> IntersightApiClient:
    return IntersightApiClient(
        host=params["api_base_uri"],
        private_key=params["api_private_key_file"],
        api_key_id=params["api_key_id"],
    )


def compute_physical_summary(api_instance: IntersightApiClient) -> int:
    handle = compute_physical_summary_api.ComputePhysicalSummaryApi(api_instance)
    api_call = handle.compute_physical_summaries_get(count=True)
    return api_call.count


def compute_blade(api_instance: IntersightApiClient) -> int:
    handle = compute_blade_api.ComputeBladeApi(api_instance)
    api_call = handle.compute_blades_get(count=True)
    return api_call.count


def compute_rack_unit(api_instance: IntersightApiClient) -> int:
    handle = compute_rack_unit_api.ComputeRackUnitApi(api_instance)
    api_call = handle.compute_rack_units_get(count=True)
    return api_call.count


def hyperflex_clusters(api_instance: IntersightApiClient):
    handle = hyperflex_cluster_api.HyperflexClusterApi(api_instance)
    return handle.hyperflex_clusters_get()


def hyperflex_health(api_instance: IntersightApiClient):
    handle = hyperflex_health_api.HyperflexHealthApi(api_instance)
    return handle.hyperflex_healths_get()


def build_hx_cluster_lookup(hx_clusters) -> Dict[str, str]:
    return {cluster.moid: cluster.cluster_name for cluster in hx_clusters.results}


def update_metrics(api_instance: IntersightApiClient, gauges: Dict[str, Gauge]) -> None:
    gauges["physical_summary"].labels(deviceType="all").set(
        compute_physical_summary(api_instance)
    )
    gauges["physical_summary"].labels(deviceType="blades").set(
        compute_blade(api_instance)
    )
    gauges["physical_summary"].labels(deviceType="rack_units").set(
        compute_rack_unit(api_instance)
    )

    hx_clusters = hyperflex_clusters(api_instance)
    cluster_lookup = build_hx_cluster_lookup(hx_clusters)

    gauges["hx_clusters"].set(len(hx_clusters.results))

    for health in hyperflex_health(api_instance).results:
        cluster_name = cluster_lookup.get(health.cluster.moid, health.cluster.moid)
        gauges["hx_health"].labels(cluster=cluster_name).set(
            HEALTH_STATUS.get(health.state, HEALTH_STATUS["UNKNOWN"])
        )

    for cluster in hx_clusters.results:
        gauges["hx_nodes_summary"].labels(
            cluster=cluster.cluster_name, nodeType="computeNodeCount"
        ).set(cluster.compute_node_count)
        gauges["hx_nodes_summary"].labels(
            cluster=cluster.cluster_name, nodeType="convergedNodeCount"
        ).set(cluster.converged_node_count)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    args = parse_args()
    api_params = load_api_params(args.api_params)
    api_instance = create_api_client(api_params)

    logging.info("Starting HTTP server on port %s", args.port)
    start_http_server(args.port)

    gauges: Dict[str, Gauge] = {
        "physical_summary": Gauge(
            "intersight_compute_physical_summary",
            "Consolidated view of Blades and RackUnits",
            ["deviceType"],
        ),
        "hx_clusters": Gauge(
            "intersight_hx_cluster_gauge",
            "Number of configured HyperFlex clusters",
        ),
        "hx_health": Gauge(
            "intersight_hyperflex_health",
            "HyperFlex health status UNKNOWN = 0, ONLINE = 1, OFFLINE = 2, ENOSPACE = 3, READONLY = 4",
            ["cluster"],
        ),
        "hx_nodes_summary": Gauge(
            "intersight_hyperflex_nodes_summary",
            "Node counts per HyperFlex cluster",
            ["cluster", "nodeType"],
        ),
    }

    while True:
        try:
            update_metrics(api_instance, gauges)
        except Exception as exc:  # pragma: no cover - runtime guard
            logging.exception("Failed to update metrics", exc_info=exc)
        time.sleep(args.pooltime)


if __name__ == "__main__":
    main()
