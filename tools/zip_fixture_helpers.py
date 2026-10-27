# SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
"""构造局部头兼容夹具。/ Build local-header compatibility fixtures."""
import io
import struct
import zipfile


def with_local_extra(data, extra):
    """Add a local-only field, preserving central sizes/CRC and fixing every local offset."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = sorted(archive.infolist(), key=lambda item: item.header_offset)
        directory = archive.start_dir
    output = bytearray()
    previous = 0
    offsets = {}
    for entry in entries:
        offset = entry.header_offset
        output.extend(data[previous:offset])
        offsets[offset] = len(output)
        header = bytearray(data[offset:offset + 30])
        name_len, extra_len = struct.unpack_from('<HH', header, 26)
        struct.pack_into('<H', header, 28, extra_len + len(extra))
        output.extend(header)
        previous = offset + 30 + name_len + extra_len
        output.extend(data[offset + 30:previous])
        output.extend(extra)
    output.extend(data[previous:directory])
    new_directory = len(output)
    position = directory
    for _ in entries:
        assert data[position:position + 4] == b'PK\x01\x02'
        record_len = 46 + sum(struct.unpack_from('<3H', data, position + 28))
        record = bytearray(data[position:position + record_len])
        struct.pack_into('<I', record, 42, offsets[struct.unpack_from('<I', record, 42)[0]])
        output.extend(record)
        position += record_len
    assert data[position:position + 4] == b'PK\x05\x06'
    end = bytearray(data[position:])
    struct.pack_into('<I', end, 16, new_directory)
    output.extend(end)
    return output

