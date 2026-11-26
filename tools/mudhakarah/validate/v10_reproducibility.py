"""V10 Reproducibility (blocking, in CI): two builds in separate clean folders give
identical manifests and bytes."""
from ..errors import BLOCKING, Finding


def compare(manifest_a, manifest_b, where):
    if manifest_a == manifest_b:
        return []
    keys = sorted(k for k in set(manifest_a) | set(manifest_b) if manifest_a.get(k) != manifest_b.get(k))
    return [Finding("V10.reproducibility", BLOCKING,
                    f"two clean builds gave different manifests (differing: {', '.join(keys)})", where)]
