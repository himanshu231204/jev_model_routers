from __future__ import annotations
class JevRoutedModel:
    def __init__(self, router, candidates): self.router = router; self.candidates = candidates
    def select(self, normalized) -> str:
        return self.router.route(normalized).final_model
