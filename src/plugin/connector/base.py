import os
import logging

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcehealth import ResourceHealthMgmtClient
from azure.mgmt.advisor import AdvisorManagementClient

from spaceone.core.connector import BaseConnector

DEFAULT_SCHEMA = 'azure_client_secret'
_LOGGER = logging.getLogger(__name__)


class AzureBaseConnector(BaseConnector):

    def __init__(self, *args, **kwargs):
        """
        kwargs
            - schema
            - options
            - secret_data

        secret_data(dict)
            - type: ..
            - project_id: ...
            - token_uri: ...
            - ...
        """

        super().__init__(*args, **kwargs)
        self.resource_health_client = None

    def set_connect(self, secret_data: dict):
        subscription_id = secret_data['subscription_id']

        os.environ["AZURE_SUBSCRIPTION_ID"] = subscription_id
        os.environ["AZURE_TENANT_ID"] = secret_data['tenant_id']
        os.environ["AZURE_CLIENT_ID"] = secret_data['client_id']
        os.environ["AZURE_CLIENT_SECRET"] = secret_data['client_secret']

        credential = DefaultAzureCredential()

        self.resource_health_client = ResourceHealthMgmtClient(credential=credential, subscription_id=subscription_id)
        self.resource_graph_client = ResourceGraphClient(credential=credential)
        self.subscription_client = SubscriptionClient(credential=credential)
        self.advisor_client = AdvisorManagementClient(credential=credential, subscription_id=subscription_id)

    def get_connector(self, cloud_service_group: str, cloud_service_type: str):
        pass
