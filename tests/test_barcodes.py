from math import floor

import pytest
import zxingcpp
from pdf417gen import encode_macro, render_image
from pdf417gen.compaction import compact_text

from app.engine import encode_macro_fitting_rows

FILE_NAME = "CH19334IBKRU0000000XX2025123101"
OPTIONS = {
    "file_id": [100, 200, 150, 250],
    "file_name": FILE_NAME,
    "columns": 13,
    "force_rows": 35,
    "security_level": 4,
    "force_binary": True,
}
LEGACY_SEGMENT_SIZE = floor(
    (455 - 46 - len(list(compact_text(FILE_NAME.encode()))) - 1) / 5 * 6
)


def test_fixed_row_capacity_regression():
    data = b"\xff" * LEGACY_SEGMENT_SIZE
    with pytest.raises(ValueError, match="Not enough space"):
        encode_macro(data, segment_size=LEGACY_SEGMENT_SIZE, **OPTIONS)
    symbols = encode_macro_fitting_rows(
        data, segment_size=LEGACY_SEGMENT_SIZE, **OPTIONS
    )
    decoded = []
    for symbol in symbols:
        assert len(symbol) == 35
        result = zxingcpp.read_barcode(render_image(symbol))
        assert result is not None and result.valid
        assert result.extra["FileName"] == FILE_NAME
        decoded.append(result.bytes)
    assert b"".join(decoded) == data


@pytest.mark.parametrize("length", [461, 462, 463, 464, 468, 925, 3500])
def test_binary_payload_survives_segmentation_at_boundaries(length):
    data = bytes(range(256)) * (length // 256) + bytes(range(length % 256))
    symbols = encode_macro_fitting_rows(
        data, segment_size=LEGACY_SEGMENT_SIZE, **OPTIONS
    )
    decoded = []
    for symbol in symbols:
        result = zxingcpp.read_barcode(render_image(symbol))
        assert result is not None and result.valid
        decoded.append(result.bytes)
    assert b"".join(decoded) == data
