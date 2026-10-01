"""
MockAnumatiClient mirrors AnumatiClient's method signatures exactly, using
an in-memory counter instead of network calls. This is what lets the SRIP
test suite (and local dev without a running Anumati instance) exercise the
full screening -> selection -> admission flow with zero network access --
see architecture doc S12, "one adapter, not scattered calls."

Swap which one is used via ANUMATI_MOCK in settings; nothing that calls
get_anumati_client() needs to know or care which it got.
"""
import itertools

from django.conf import settings

from .client import AnumatiClient


class MockAnumatiClient:
    _id_counter = itertools.count(1000)

    def __init__(self, *args, **kwargs):
        self.created_lockers = {}
        self.created_connection_types = {}
        self.created_connections = {}

    def create_locker(self, name, description="", username=None, password=None, refresh_token=None):
        locker_id = next(self._id_counter)
        self.created_lockers[locker_id] = {"name": name, "description": description}
        return {"success": True, "id": locker_id, "name": name, "description": description}

    def create_connection_type(
        self,
        *,
        connection_name,
        connection_description,
        locker_name,
        validity_iso,
        directions,
        post_conditions=None,
        username=None,
        password=None,
        refresh_token=None,
    ):
        ct_id = next(self._id_counter)
        self.created_connection_types[ct_id] = {
            "name": connection_name,
            "locker_name": locker_name,
            "directions": directions,
        }
        return ct_id

    def create_connection(
        self,
        *,
        connection_type_id,
        connection_name,
        host_locker_name,
        guest_locker_name,
        host_username,
        guest_username,
        connection_description="",
        password=None,
        refresh_token=None,
    ):
        conn_id = next(self._id_counter)
        self.created_connections[conn_id] = {
            "connection_type_id": connection_type_id,
            "name": connection_name,
            "status": "pending",
            "host_username": host_username,
            "guest_username": guest_username,
        }
        return conn_id

    def close_connection_host(self, connection_id, username=None, password=None, refresh_token=None):
        if connection_id in self.created_connections:
            self.created_connections[connection_id]["status"] = "closed"
        return {"message": "Connection closed successfully (unilateral)."}

    def give_consent(self, **kwargs):
        conn = self.created_connections.get(kwargs.get("connection_id"))
        if conn:
            conn["status"] = "live"
        return {"success": True, "message": "Consent status updated successfully"}

    def build_authorize_url(self, *, redirect_uri, state, client_id=None):
        from urllib.parse import urlencode

        qs = urlencode({"client_id": client_id or "mock-client", "redirect_uri": redirect_uri, "state": state})
        return f"http://mock-anumati/oauth/authorize/?{qs}"

    def exchange_code(self, *, code, redirect_uri, client_id=None, client_secret=None):
        """Mock exchange: deterministic, no network. Real client_secret
        validation is Anumati's job, tested against the live instance --
        see anumati_integration/tests.py's AnumatiClientAgainstNewBackendTests
        for the mocked-HTTP version of that check."""
        token_id = next(self._id_counter)
        return {
            "success": True,
            "username": f"mock_user_{code[:6]}",
            "locker_id": token_id,
            "locker_name": "Academic",
            "access_token": f"mock-access-{token_id}",
            "refresh_token": f"mock-refresh-{token_id}",
        }


def get_anumati_client():
    """Single place that decides real vs. mock. Everything else in
    anumati_integration calls this instead of instantiating a client
    directly."""
    if getattr(settings, "ANUMATI_MOCK", True):
        return MockAnumatiClient()
    return AnumatiClient()
