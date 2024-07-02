import logging

from plugin.connector.base import AzureBaseConnector

_LOGGER = logging.getLogger("spaceone")


class AdvisorConnector(AzureBaseConnector):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_connect(kwargs.get('secret_data'))

    def list_recommendations(self, recommendation_filter: str = None):
        return self.advisor_client.recommendations.list(api_version="2023-01-01", filter=recommendation_filter)

    def get_metadata(self, name: str):
        return self.advisor_client.recommendation_metadata.get(name=name)

    def list_metadata(self):
        return self.advisor_client.recommendation_metadata.list(expand="ibiza")
