import zlib

import pytest
import zxingcpp


@pytest.fixture
def decode_barcode_xml():
    def decode(pdf):
        chunks = []
        file_ids = set()
        for page in pdf.pages:
            page_chunks = []
            for arguments, operator in page.get_contents().operations:
                if operator != b"Do":
                    continue
                image = page.images[arguments[0]].image
                barcodes = zxingcpp.read_barcodes(
                    image, formats=zxingcpp.BarcodeFormat.PDF417
                )
                for barcode in barcodes:
                    assert barcode.valid
                    file_ids.add(barcode.extra["FileId"])
                    page_chunks.append(barcode.bytes)
            # The pinned renderer rotates the symbols clockwise and draws each
            # page's segments in reverse order (right to left).
            chunks.extend(reversed(page_chunks))
        assert chunks
        assert len(file_ids) == 1
        return zlib.decompress(b"".join(chunks))

    return decode
