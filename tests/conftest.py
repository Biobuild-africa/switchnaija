import gzip
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def ede_weather() -> pd.DataFrame:
    """Real PVGIS (SARAH3) hourly output for 1 kWp in Ede, Osun State, 2023 (West Africa Time).

    Stored compactly: PV output rounded to 0.01 kW per kWp and air temperature to 0.5 C
    (8,760 bytes each, gzipped). Annual yield is unchanged to within 0.01%.
    """
    raw = np.frombuffer(gzip.decompress((FIX / "pvgis_ede_2023_q.bin.gz").read_bytes()), dtype=np.uint8)
    n = raw.size // 2
    idx = pd.date_range("2023-01-01 01:00", periods=n, freq="h")
    return pd.DataFrame({"pv_kw_per_kwp": raw[:n] / 100.0, "temp_c": raw[n:] / 2.0}, index=idx)
