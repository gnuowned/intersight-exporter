#!/usr/bin/env python
"""Add an Intersight user by providing Cisco.com user ID and role via the Intersight API."""
import sys
import json
import argparse
from intersight.intersight_api_client import IntersightApiClient
from intersight.apis import iam_permission_api
from intersight.apis import iam_idp_reference_api
from intersight.apis import iam_user_api
from intersight.apis import hyperflex_cluster_api, compute_physical_summary_api, compute_blade_api, compute_rack_unit_api
from prometheus_client import start_http_server, Summary, Gauge
import time



compute_physical_summary_gauge = Gauge ('compute_physical_summary', 'Consolidated view of Blades and RackUnits', ['deviceType'])

def compute_physical_summary (intersight_api_params, api_instance):
    handle = compute_physical_summary_api.ComputePhysicalSummaryApi(api_instance)
    api_call = handle.compute_physical_summaries_get(count=True)
    return api_call.count

def compute_blade (intersight_api_params, api_instance):
    handle = compute_blade_api.ComputeBladeApi(api_instance)
    api_call = handle.compute_blades_get(count=True)
    return api_call.count

def compute_rack_unit (intersight_api_params, api_instance):
    handle = compute_rack_unit_api.ComputeRackUnitApi(api_instance)
    api_call = handle.compute_rack_units_get(count=True)
    return api_call.count


hx_clusters_gauge = Gauge ('hx_cluster_gauge', 'This is the cluster Gauge')

def hyperflex_clusters (intersight_api_params, api_instance):
    hx_clusters_handle = hyperflex_cluster_api.HyperflexClusterApi (api_instance)
    hx_clusters = hx_clusters_handle.hyperflex_clusters_get(count=True)
    return hx_clusters.count



if __name__ == "__main__":
    # settings are pulled from the json string or JSON file passed as an arg
    parser = argparse.ArgumentParser()
    help_str = 'Pooling time in seconds, default 5 seconds'
    parser.add_argument('-p', '--pooltime', default=5, help=help_str)
    help_str = 'JSON file with Intersight API parameters.  Default: intersight_api_params.json'
    parser.add_argument('-a', '--api_params', default='intersight_api_params.json', help=help_str)
    args = parser.parse_args()
    with open(args.api_params, 'r') as api_file:
        intersight_api_params = json.load(api_file)
    # argument array for connection. 
    api_instance = IntersightApiClient(
        host=intersight_api_params['api_base_uri'],
        private_key=intersight_api_params['api_private_key_file'],
        api_key_id=intersight_api_params['api_key_id'],
    )



    # Start up the server to expose the metrics.
    start_http_server(8000)
    # Generate some requests.
    while True:
        hx_clusters_gauge.set(hyperflex_clusters(intersight_api_params, api_instance))
        compute_physical_summary_gauge.labels(deviceType='all').set(compute_physical_summary(intersight_api_params, api_instance))
        compute_physical_summary_gauge.labels(deviceType='blades').set(compute_blade(intersight_api_params, api_instance))
        compute_physical_summary_gauge.labels(deviceType='rack_units').set(compute_rack_unit(intersight_api_params, api_instance))
        time.sleep(args.pooltime)





    sys.exit(0)