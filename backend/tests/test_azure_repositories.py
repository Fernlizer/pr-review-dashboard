import unittest
from unittest.mock import AsyncMock
from services.azure_client import AzureDevOpsClient


class RepositoryDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_lists_unique_enabled_repositories(self):
        client = AzureDevOpsClient()
        client._get = AsyncMock(return_value={"value": [
            {"name": "purchase"}, {"name": "new-repo"}, {"name": "purchase"},
            {"name": "disabled", "isDisabled": True}, {},
        ]})
        self.assertEqual(await client.list_repositories(), ["new-repo", "purchase"])
        client._get.assert_awaited_once_with(
            f"{client.repo_base}?includeHidden=true&api-version=7.1"
        )
