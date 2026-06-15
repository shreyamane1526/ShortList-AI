from functools import lru_cache


@lru_cache(maxsize=128)
def cached_skill_lookup(
    skill_name: str,
):

    return skill_name.lower().strip()