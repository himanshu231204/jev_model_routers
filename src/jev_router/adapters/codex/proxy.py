class CodexProxy:
    def __init__(self, transport): self.transport = transport
    def forward(self, request: dict) -> dict:
        return self.transport.send({"path": "/v1/responses", "body": request})
