from django.test import TestCase
from rest_framework.test import APIClient

from configuration.models import Location


class ApiEndpointSmokeTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _assert_paginated_ok(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("results", payload)
        self.assertIn("count", payload)
        self.assertIn("next", payload)
        self.assertIn("previous", payload)

    def test_configuration_locations_list_endpoint(self):
        Location.objects.create(name="Mumbai")
        self._assert_paginated_ok("/api/v1/configuration/locations/")

    def test_entity_drivers_list_endpoint(self):
        self._assert_paginated_ok("/api/v1/entity/drivers/")

    def test_operations_shipments_list_endpoint(self):
        self._assert_paginated_ok("/api/v1/operations/shipments/")

    def test_financial_invoices_list_endpoint(self):
        self._assert_paginated_ok("/api/v1/financial/invoices/")

    def test_maintenance_records_list_endpoint(self):
        self._assert_paginated_ok("/api/v1/maintenance/maintenance-records/")
