import logging
import time

from spaceone.core.error import ERROR_REQUIRED_PARAMETER
from spaceone.inventory.plugin.collector.lib.server import CollectorPluginServer

from plugin.manager.base import AzureBaseManager
from plugin.manager.subscriptions.subscriptions_manager import SubscriptionsManager

app = CollectorPluginServer()

_LOGGER = logging.getLogger("spaceone")

DEFAULT_RESOURCE_TYPES = [
    "inventory.CloudService",
    "inventory.CloudServiceType",
    "inventory.Metric",
    "inventory.Region",
]


@app.route("Collector.init")
def collector_init(params: dict) -> dict:
    """init plugin by options

    Args:
        params (CollectorInitRequest): {
            'options': 'dict',    # Required
            'domain_id': 'str'
        }

    Returns:
        PluginResponse: {
            'metadata': 'dict'
        }
    """

    metadata = {
        "options_schema": {
            "type": "object",
            "properties": {
                "cloud_service_groups": {
                    "title": "Specific services",
                    "type": "string",
                    "items": {"type": "string"},
                    "default": "ALL",
                    "enum": _get_all_cloud_service_groups(),
                    "description": "Choose one of the service to collect data. If you choose 'All', it will collect "
                    "all services.",
                }
            },
        }
    }
    return {"metadata": metadata}


@app.route("Collector.verify")
def collector_verify(params: dict) -> None:
    """Verifying collector plugin

    Args:
        params (CollectorVerifyRequest): {
            'options': 'dict',      # Required
            'secret_data': 'dict',  # Required
            'schema': 'str',
            'domain_id': 'str'
        }

    Returns:
        None
    """

    pass


@app.route("Collector.collect")
def collector_collect(params: dict) -> dict:
    """Collect external data

    Args:
        params (CollectorCollectRequest): {
            'options': 'dict',      # Required
            'secret_data': 'dict',  # Required
            'schema': 'str',
            'task_options': 'dict',
            'domain_id': 'str'
        }

    Returns:
        Generator[ResourceResponse, None, None]
        {
            'state': 'SUCCESS | FAILURE',
            'resource_type': 'inventory.CloudService | inventory.CloudServiceType | inventory.Region',
            'cloud_service_type': CloudServiceType,
            'cloud_service': CloudService,
            'region': Region,
            'match_keys': 'list',
            'error_message': 'str'
            'metadata': 'dict'
        }

        CloudServiceType
        {
            'name': 'str',           # Required
            'group': 'str',          # Required
            'provider': 'str',       # Required
            'is_primary': 'bool',
            'is_major': 'bool',
            'metadata': 'dict',      # Required
            'service_code': 'str',
            'tags': 'dict'
            'labels': 'list'
        }

        CloudService
        {
            'name': 'str',
            'cloud_service_type': 'str',  # Required
            'cloud_service_group': 'str', # Required
            'provider': 'str',            # Required
            'ip_addresses' : 'list',
            'account' : 'str',
            'instance_type': 'str',
            'instance_size': 'float',
            'region_code': 'str',
            'data': 'dict'               # Required
            'metadata': 'dict'           # Required
            'reference': 'dict'
            'tags' : 'dict'
        }

        Region
        {
            'name': 'str',
            'region_code': 'str',        # Required
            'provider': 'str',           # Required
            'tags': 'dict'
        }

        Only one of the cloud_service_type, cloud_service and region fields is required.
    """
    options: dict = params.get("options", {}) or {}
    secret_data: dict = params["secret_data"]
    schema: str = params.get("schema")
    task_options: dict = params.get("task_options", {}) or {}
    domain_id: str = params["domain_id"]
    subscription_id = secret_data.get("subscription_id")

    _check_secret_data(secret_data)

    start_time = time.time()
    _LOGGER.debug(
        f"[collector_collect] Start Collecting Azure Resources {subscription_id}"
    )

    cloud_service_groups = _get_cloud_service_groups_from_options_and_task_options(
        options, task_options
    )
    resource_type = task_options.get("resource_type")

    if resource_type == "inventory.Region":
        subscriptions_mgr = SubscriptionsManager()
        location_info = subscriptions_mgr.list_location_info(secret_data)
        yield from AzureBaseManager().collect_region(location_info)
    else:

        for manager in AzureBaseManager.list_managers_by_cloud_service_groups(
            cloud_service_groups
        ):
            if resource_type == "inventory.CloudService":
                yield from manager().collect_cloud_services(
                    options, secret_data, schema
                )
            elif resource_type == "inventory.CloudServiceType":
                yield from manager().collect_cloud_service_type()
            elif resource_type == "inventory.Metric":
                yield from AzureBaseManager.collect_metrics(manager.cloud_service_group)
            else:
                yield from manager().collect_resources(options, secret_data, schema)
    _LOGGER.debug(
        f"[collector_collect] Finished Collecting Azure Resources {subscription_id} duration: {time.time() - start_time} seconds"
    )


@app.route("Job.get_tasks")
def job_get_tasks(params: dict) -> dict:
    """Get job tasks

    Args:
        params (JobGetTaskRequest): {
            'options': 'dict',      # Required
            'secret_data': 'dict',  # Required
            'domain_id': 'str'
        }

    Returns:
        TasksResponse: {
            'tasks': 'list'
        }

    """
    domain_id = params["domain_id"]
    options = params.get("options", {})
    cloud_service_groups = options.get("cloud_service_groups", [])
    resource_types = options.get("resource_types", DEFAULT_RESOURCE_TYPES)

    tasks = []

    if not resource_types:
        resource_types = DEFAULT_RESOURCE_TYPES

    for manager in AzureBaseManager.list_managers_by_cloud_service_groups(
        cloud_service_groups
    ):
        if not manager.cloud_service_group:
            continue

        for resource_type in resource_types:
            tasks.append(
                {
                    "task_options": {
                        "resource_type": resource_type,
                        "cloud_service_groups": [manager.cloud_service_group],
                    }
                }
            )

    return {"tasks": tasks}


def _get_cloud_service_groups_from_options_and_task_options(
    options: dict, task_options: dict
) -> list:
    cloud_service_groups = options.get("cloud_service_groups", [])
    if task_options:
        cloud_service_groups = task_options.get(
            "cloud_service_groups", cloud_service_groups
        )
    return cloud_service_groups


def _check_secret_data(secret_data: dict):
    if "tenant_id" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.tenant_id")

    if "subscription_id" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.subscription_id")

    if "client_id" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.client_id")

    if "client_secret" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.client_secret")


def _get_all_cloud_service_groups():
    cloud_service_groups = ["ALL"]
    for manager in AzureBaseManager.list_managers_by_cloud_service_groups([]):
        if manager.cloud_service_group:
            cloud_service_groups.append(manager.cloud_service_group)
    return list(set(cloud_service_groups))
