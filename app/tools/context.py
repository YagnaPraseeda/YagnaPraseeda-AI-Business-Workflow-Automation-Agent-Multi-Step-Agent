_state: dict = {}


def reset() -> None:
    _state.clear()


def set(key: str, value) -> None:
    _state[key] = value


def get(key: str, default=None):
    return _state.get(key, default)
