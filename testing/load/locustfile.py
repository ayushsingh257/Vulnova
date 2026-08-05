"""Locust Load Testing Suite evaluating Vulnova API Gateway rate limiting and 2000+ req/sec stability."""

import random
from locust import HttpUser, between, task


class VulnovaLoadTestUser(HttpUser):
    """Simulates high-concurrency user traffic hitting Vulnova API endpoints."""

    wait_time = between(0.01, 0.05)  # High throughput load generation

    @task(5)
    def test_status_endpoint(self) -> None:
        """Hit public status endpoint to test baseline rate limit headers."""
        with self.client.get("/api/v1/status", catch_response=True) as response:
            if response.status_code in [200, 429]:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(3)
    def test_health_endpoint(self) -> None:
        """Hit exempt health probe endpoint."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health probe failed: {response.status_code}")

    @task(2)
    def test_burst_rate_limiting(self) -> None:
        """Simulate high-frequency request bursts to trigger HTTP 429 responses."""
        fake_ip = f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}"
        headers = {"X-Forwarded-For": fake_ip}
        with self.client.get("/api/v1/status", headers=headers, catch_response=True) as response:
            if response.status_code in [200, 429]:
                response.success()
            else:
                response.failure(f"Burst request failed: {response.status_code}")
