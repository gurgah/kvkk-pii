import sys
sys.path.insert(0, "/Users/jangis/Code/pii-tool")
import pytest
from kvkk_pii.async_detector import AsyncPiiDetector


@pytest.fixture
def detector():
    return AsyncPiiDetector(download_policy="auto")


@pytest.mark.asyncio
async def test_async_analyze(detector):
    result = await detector.analyze("TC: 10000000146")
    assert result.has("TC_KIMLIK")


@pytest.mark.asyncio
async def test_async_anonymize(detector):
    anon = await detector.anonymize("TC: 10000000146")
    assert "10000000146" not in anon


@pytest.mark.asyncio
async def test_async_two_way(detector):
    async def mock_ai(masked: str) -> str:
        import re
        ph = re.search(r'\[TC_KIMLIK_[a-z0-9]{3}\]', masked)
        return f"{ph.group(0) if ph else '[TC]'} için kayıt bulundu."

    result = await detector.two_way(
        "TC: 10000000146 hakkında bilgi ver.",
        call_fn=mock_ai,
    )
    assert result.safe
    assert "10000000146" in result.output


@pytest.mark.asyncio
async def test_async_paralel(detector):
    """Birden fazla analizi paralel çalıştır."""
    import asyncio
    texts = [
        "TC: 10000000146",
        "ali@test.com",
        "+90 532 123 45 67",
        "IBAN: TR330006100519786457841326",
    ]
    results = await asyncio.gather(*[detector.analyze(t) for t in texts])
    assert results[0].has("TC_KIMLIK")
    assert results[1].has("EMAIL")
    assert results[2].has("TELEFON_TR")
    assert results[3].has("IBAN_TR")
