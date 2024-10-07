import logging

from plugin.connector.base import AzureBaseConnector

_LOGGER = logging.getLogger("spaceone")


class ContainerServiceConnector(AzureBaseConnector):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_connect(kwargs.get('secret_data'))

    def list_managed_cluster(self):
        return self.container_service_client.managed_clusters.list()
