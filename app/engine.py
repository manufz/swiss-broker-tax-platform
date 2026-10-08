"""Pinned-engine adapter for fixed-row Macro PDF417 byte capacity."""

import pdf417gen
from pdf417gen.encoding import (
    MACRO_FILE_NAME,
    MACRO_SEGMENT_COUNT,
    create_macro_control_block,
)

_encode_macro = pdf417gen.encode_macro


def encode_macro_fitting_rows(
    data,
    *,
    file_id,
    file_name,
    columns,
    force_rows,
    security_level,
    segment_size,
    force_binary,
):
    # The pinned renderer estimates overhead and rounds byte capacity up. Some
    # final segments overflow the fixed 35x13 symbol. Count the actual control
    # words, reserve the final-segment terminator, and use complete 6-byte groups
    # (each uses 5 codewords). Five-digit indices/counts use two numeric words.
    control = create_macro_control_block(
        segment_index=99998,
        file_id=file_id,
        optional_fields={MACRO_FILE_NAME: file_name, MACRO_SEGMENT_COUNT: 99999},
        is_last=True,
    )
    if force_binary and force_rows is not None:
        available = columns * force_rows - 2 ** (security_level + 1) - len(control) - 2
        # Reserve one word each for the length descriptor and byte-mode latch.
        capacity = (available // 5) * 6
        if capacity <= 0:
            raise ValueError("Macro PDF417 metadata leaves no byte capacity")
        segment_size = min(segment_size, capacity)
    return _encode_macro(
        data,
        file_id=file_id,
        file_name=file_name,
        columns=columns,
        force_rows=force_rows,
        security_level=security_level,
        segment_size=segment_size,
        force_binary=force_binary,
    )


def main():
    pdf417gen.encode_macro = encode_macro_fitting_rows
    from opensteuerauszug.steuerauszug import app

    app()


if __name__ == "__main__":
    main()
