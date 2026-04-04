from ulid import ULID


def prefixed_ulid(prefix: str) -> str:
    return f"{prefix}_{str(ULID()).lower()}"


def _make_generator(prefix: str):
    def generate() -> str:
        return prefixed_ulid(prefix)

    generate.__name__ = f"generate_{prefix}_id"
    generate.__qualname__ = f"generate_{prefix}_id"
    return generate


generate_prd_id = _make_generator("prd")
generate_ord_id = _make_generator("ord")
generate_itm_id = _make_generator("itm")
