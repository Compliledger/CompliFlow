class SessionKeyManager:

    def __init__(self) -> None:
        self._keys: dict[str, str] = {}

    def create(self, session_id: str, key: str) -> None:
        self._keys[session_id] = key

    def get(self, session_id: str) -> str | None:
        return self._keys.get(session_id)

    def revoke(self, session_id: str) -> None:
        self._keys.pop(session_id, None)
