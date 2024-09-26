import os
import logging

import azure.core.exceptions
import requests
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcehealth import ResourceHealthMgmtClient
from azure.mgmt.advisor import AdvisorManagementClient
from azure.mgmt.containerservice import ContainerServiceClient

from spaceone.core.connector import BaseConnector

DEFAULT_SCHEMA = 'azure_client_secret'
_LOGGER = logging.getLogger("spaceone")


class AzureBaseConnector(BaseConnector):
    region_display_map = {}

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
        self.next_link = None

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
        self.container_service_client = ContainerServiceClient(credential=credential, subscription_id=subscription_id)

    def get_connector(self, cloud_service_group: str, cloud_service_type: str):
        pass

    def request_azure_api(self, url: str, method: str = "GET", parameter: dict = None) -> dict:
        headers = self._make_request_headers()
        try:

            response = requests.request(method=method, url=url, headers=headers, json=parameter)
            response_json = response.json()

            if isinstance(response_json, dict):
                properties = response_json.get("properties", {})
            else:
                properties = {}

            if properties:
                self.next_link = properties.get("nextLink", None)

            if response_error := response_json.get("error"):
                if response_error.get("code") != "NotFound":
                    raise azure.core.exceptions.HttpResponseError(response_json)
                else:
                    return {}

            return response_json
        except azure.core.exceptions.HttpResponseError as e:
            _LOGGER.error(f"[ERROR] request_azure_api with azure error model :{e}")
            raise
        except Exception as e:
            _LOGGER.error(f"[ERROR] request_azure_api :{e}")
            raise e

    def _make_request_headers(self, client_type=None):
        access_token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        if client_type:
            headers["ClientType"] = client_type

        return headers

    @staticmethod
    def _get_access_token():
        try:
            credential = DefaultAzureCredential(logging_enable=True)
            scopes = ["https://management.azure.com/.default"]
            token_info = credential.get_token(*scopes)
            return token_info.token
        except Exception as e:
            _LOGGER.error(f"[ERROR] _get_access_token :{e}")
            raise e
