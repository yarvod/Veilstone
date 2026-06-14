from __future__ import annotations

from voxel_sandbox.network.rate_limit import TokenBucket


def test_token_bucket_limits_burst_and_refills_over_time() -> None:
    bucket = TokenBucket(rate=2.0, capacity=2.0, updated_at=10.0)

    assert bucket.allow(now=10.0)
    assert bucket.allow(now=10.0)
    assert not bucket.allow(now=10.0)
    assert bucket.allow(now=10.5)
