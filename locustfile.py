from locust import HttpUser, task


class HealthCheck(HttpUser):
    @task
    def health(self):
        self.client.get("/_health")
