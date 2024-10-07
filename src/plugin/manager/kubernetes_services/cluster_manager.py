import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from spaceone.inventory.plugin.collector.lib import *

from plugin.conf.cloud_service_conf import ICON_URL
from plugin.connector.kubernetes_service.container_service_conector import (
    ContainerServiceConnector,
)
from plugin.connector.subscriptions.subscriptions_connector import (
    SubscriptionsConnector,
)
from plugin.manager.base import AzureBaseManager

_LOGGER = logging.getLogger("spaceone")


class ClusterManager(AzureBaseManager):
    cloud_service_group = "AKS"
    cloud_service_type = "Cluster"
    service_code = "/Microsoft.ContainerService/managedClusters"

    def create_cloud_service(self, options: dict, secret_data: dict, schema: str):
        _LOGGER.debug(f"[create_cloud_service] options: {options}")
        cloud_services = []
        error_responses = []

        container_service_client = ContainerServiceConnector(secret_data=secret_data)
        subscription_conn = SubscriptionsConnector(secret_data=secret_data)

        subscription_obj = subscription_conn.get_subscription(
            secret_data["subscription_id"]
        )
        subscription_info = self.convert_nested_dictionary(subscription_obj)

        managed_clusters = container_service_client.list_managed_cluster()

        for managed_cluster in managed_clusters:
            try:
                managed_cluster_info = self.convert_nested_dictionary(managed_cluster)
                resource_id = managed_cluster_info.get("id")
                resource_group = self.get_resource_group_from_id(resource_id)

                managed_cluster_info.update(
                    {
                        "tenant_id": subscription_info.get("tenant_id"),
                        "subscription_id": subscription_info.get("subscription_id"),
                        "subscription_name": subscription_info.get("display_name"),
                        "resource_group": resource_group,
                    }
                )

                cloud_services.append(
                    make_cloud_service(
                        name=managed_cluster_info.get("name"),
                        account=secret_data["subscription_id"],
                        cloud_service_type=self.cloud_service_type,
                        cloud_service_group=self.cloud_service_group,
                        provider=self.provider,
                        region_code=managed_cluster_info.get("location"),
                        data=managed_cluster_info,
                        reference=self.make_reference(managed_cluster_info.get("id")),
                    )
                )
            except Exception as e:
                _LOGGER.error(f"[create_cloud_service] Error {self.service} {e}")
                error_responses.append(
                    make_error_response(
                        error=e,
                        provider=self.provider,
                        cloud_service_group=self.cloud_service_group,
                        cloud_service_type=self.cloud_service_type,
                    )
                )

        return cloud_services, error_responses

    def create_cloud_service_type(self):
        return make_cloud_service_type(
            name=self.cloud_service_type,
            group=self.cloud_service_group,
            provider=self.provider,
            service_code=self.service_code,
            metadata_path=self.get_metadata_path(),
            is_primary=True,
            is_major=True,
            labels=[],
            tags={"spaceone:icon": f"{ICON_URL}/aks.svg"},
        )

    @staticmethod
    def get_resource_group_from_id(resource_id) -> str:
        return resource_id.split("/")[4]
