from jev_router.transport.base import Transport
from jev_router.transport.http import HttpTransport

def test_http_transport_has_send():
    assert hasattr(HttpTransport("http://localhost:9"), "send")

def test_transport_protocol():
    assert hasattr(Transport, "send")
