import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="module")
def exporter_module():
    """Load intersight_exporter with external dependencies mocked."""
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    intersight_module = types.ModuleType("intersight")
    apis_module = types.ModuleType("intersight.apis")

    compute_blade_api = types.SimpleNamespace(ComputeBladeApi=MagicMock())
    compute_physical_summary_api = types.SimpleNamespace(
        ComputePhysicalSummaryApi=MagicMock()
    )
    compute_rack_unit_api = types.SimpleNamespace(ComputeRackUnitApi=MagicMock())
    hyperflex_cluster_api = types.SimpleNamespace(HyperflexClusterApi=MagicMock())
    hyperflex_health_api = types.SimpleNamespace(HyperflexHealthApi=MagicMock())

    apis_module.compute_blade_api = compute_blade_api
    apis_module.compute_physical_summary_api = compute_physical_summary_api
    apis_module.compute_rack_unit_api = compute_rack_unit_api
    apis_module.hyperflex_cluster_api = hyperflex_cluster_api
    apis_module.hyperflex_health_api = hyperflex_health_api

    intersight_module.apis = apis_module

    class FakeApiClient:
        def __init__(self, *_, **__):
            pass

    prometheus_client = types.SimpleNamespace(
        Gauge=MagicMock(), start_http_server=MagicMock()
    )

    sys.modules["intersight"] = intersight_module
    sys.modules["intersight.apis"] = apis_module
    sys.modules["intersight.apis.compute_blade_api"] = compute_blade_api
    sys.modules[
        "intersight.apis.compute_physical_summary_api"
    ] = compute_physical_summary_api
    sys.modules["intersight.apis.compute_rack_unit_api"] = compute_rack_unit_api
    sys.modules["intersight.apis.hyperflex_cluster_api"] = hyperflex_cluster_api
    sys.modules["intersight.apis.hyperflex_health_api"] = hyperflex_health_api
    sys.modules["intersight.intersight_api_client"] = types.SimpleNamespace(
        IntersightApiClient=FakeApiClient
    )
    sys.modules["prometheus_client"] = prometheus_client

    module = importlib.import_module("intersight_exporter")
    yield module

    for key in list(sys.modules.keys()):
        if key.startswith("intersight") or key == "prometheus_client":
            sys.modules.pop(key)


def test_load_api_params_success(tmp_path, exporter_module):
    api_params = {
        "api_base_uri": "https://example.com",
        "api_private_key_file": "/tmp/key.pem",
        "api_key_id": "12345",
    }
    config_file = tmp_path / "params.json"
    config_file.write_text(json.dumps(api_params), encoding="utf-8")

    loaded_params = exporter_module.load_api_params(str(config_file))

    assert loaded_params == api_params


def test_load_api_params_missing_key(tmp_path, exporter_module):
    api_params = {
        "api_base_uri": "https://example.com",
        "api_private_key_file": "/tmp/key.pem",
    }
    config_file = tmp_path / "params.json"
    config_file.write_text(json.dumps(api_params), encoding="utf-8")

    with pytest.raises(SystemExit):
        exporter_module.load_api_params(str(config_file))


def test_build_hx_cluster_lookup(exporter_module):
    class Cluster:
        def __init__(self, moid, name):
            self.moid = moid
            self.cluster_name = name

    clusters = [Cluster("1", "alpha"), Cluster("2", "beta")]

    class ClusterResponse:
        def __init__(self, results):
            self.results = results

    lookup = exporter_module.build_hx_cluster_lookup(ClusterResponse(clusters))

    assert lookup == {"1": "alpha", "2": "beta"}
