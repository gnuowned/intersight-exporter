#!/usr/bin/env python
"""Add an Intersight user by providing Cisco.com user ID and role via the Intersight API."""
import sys
import json
import argparse
from intersight.intersight_api_client import IntersightApiClient
from intersight.apis import iam_permission_api
from intersight.apis import iam_idp_reference_api
from intersight.apis import iam_user_api
from intersight.apis import hyperflex_cluster_api, compute_physical_summary_api, compute_blade_api, compute_rack_unit_api, hyperflex_health_api
from prometheus_client import start_http_server, Summary, Gauge, Enum, Info
import time



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


def hyperflex_clusters (intersight_api_params, api_instance):
    hx_clusters_handle = hyperflex_cluster_api.HyperflexClusterApi (api_instance)
    hx_clusters = hx_clusters_handle.hyperflex_clusters_get()
    return hx_clusters

def hyperflex_clusters_moid (intersight_api_params, api_instance, moid):
    hx_clusters_handle = hyperflex_cluster_api.HyperflexClusterApi (api_instance)
    hx_clusters = hx_clusters_handle.hyperflex_clusters_moid_get(moid)
    return hx_clusters 




def hyperflex_health (intersight_api_params, api_instance):
    handle = hyperflex_health_api.HyperflexHealthApi(api_instance)
    api_call = handle.hyperflex_healths_get()
    return api_call





if __name__ == "__main__":
    # settings are pulled from the json string or JSON file passed as an arg
    parser = argparse.ArgumentParser()
    help_str = 'Pooling time in seconds, default 5 seconds'
    parser.add_argument('-t', '--pooltime', default=5, help=help_str)
    help_str = 'bind por, default 8000'
    parser.add_argument('-p', '--port', default=8000, help=help_str)
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


    print(f'Starting HTTP Server at port {args.port}')
    # Start up the server to expose the metrics.
    start_http_server(args.port)
    # Metrics Declaration
    compute_physical_summary_gauge = Gauge ('intersight_compute_physical_summary', 'Consolidated view of Blades and RackUnits', ['deviceType'])
    hx_clusters_gauge = Gauge ('intersight_hx_cluster_gauge', 'This is the cluster Gauge')

    hyperflex_health_status = Gauge('intersight_hyperflex_health', 'intersight_hyperflex_health status UNKNOWN = 0,ONLINE = 1, OFFLINE = 2, ENOSPACE = 3, READONLY = 4', ['cluster'])
    
    hyperflex_nodes_summary = Gauge('intersight_hyperflex_nodes_symmary', 'how many and kind of nodes we have in each HX Cluster', ['cluster','nodeType'])

    #Mapping health status to numbers, prometheus only support numbers as metrics
    switcher = {
        'UNKNOWN': 0,
        'ONLINE': 1,
        'OFFLINE': 2,
        'ENOSPACE': 3,
        'READONLY': 4
    }


    while True:
        

        
        compute_physical_summary_gauge.labels(deviceType='all').set(compute_physical_summary(intersight_api_params, api_instance))
        compute_physical_summary_gauge.labels(deviceType='blades').set(compute_blade(intersight_api_params, api_instance))
        compute_physical_summary_gauge.labels(deviceType='rack_units').set(compute_rack_unit(intersight_api_params, api_instance))


        #We get HX Cluster results, we will use in several metrics

        hx_clusters = hyperflex_clusters(intersight_api_params, api_instance)    
    

        cluster_dict = {}
        for cluster in hx_clusters.results:
            cluster_dict[cluster.moid] = cluster.cluster_name

        #how many cluster do we have?
        hx_clusters_gauge.set(len(hx_clusters.results))

        
        #what is the status for every cluster
        for health in hyperflex_health(intersight_api_params, api_instance).results:
            hyperflex_health_status.labels(cluster=cluster_dict[health.cluster.moid]).set(switcher.get(health.state))

        for cluster in hx_clusters.results:
            hyperflex_nodes_summary.labels(cluster=cluster.cluster_name,nodeType='computeNodeCount').set(cluster.compute_node_count)
            hyperflex_nodes_summary.labels(cluster=cluster.cluster_name,nodeType='convergedNodeCount').set(cluster.converged_node_count)



        time.sleep(args.pooltime)





    sys.exit(0)