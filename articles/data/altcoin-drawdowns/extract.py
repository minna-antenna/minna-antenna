"""Extract only numeric price observations from one pinned research snapshot.

Run: python extract.py /path/to/LDA_t2_s0_basetable.p > input.csv
No object deserialization. Positions are valid only for the required SHA-256.
"""
import csv
import hashlib
import math
import pickletools
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

DIGEST = 'f66e55dec3c1e965906163ef79b4d72d9dc6f77ff69fef9be01531a9ce42584a'
ASSETS = ('BTC', 'ETH', 'XRP', 'LTC')


def extract(source, output):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DIGEST:
        raise ValueError('Unexpected source snapshot')
    # Audited columns: float block row 1 = close, rows 2/3 = base/quote volume.
    ops = {pos: (op.name, value) for op, value, pos in pickletools.genops(raw)}
    numeric = ops[63876][1]
    stamps = ops[1038][1]
    n = len(stamps) // 8
    if struct.unpack('<23q', ops[1373092][1])[:5] != (2, 3, 4, 5, 6):
        raise ValueError('Unexpected float block layout')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['date', 'symbol', 'close_usd', 'volume_base', 'volume_usd'])
    labels = []
    memo = {}
    for pos, (op, value) in ops.items():
        if 1344564 <= pos < 1358516:
            if op == 'SHORT_BINUNICODE':
                memo[126 + len(memo)] = value
                labels.append(value)
            elif op == 'BINGET':
                labels.append(memo[value])
    if len(labels) != n:
        raise ValueError('Price and symbol dimensions differ')
    observed = {}
    for i, symbol in enumerate(labels):
        timestamp = struct.unpack_from('<q', stamps, i * 8)[0]
        when = datetime.fromtimestamp(timestamp // 10**9, timezone.utc)
        day = when.date().isoformat()
        if symbol not in ASSETS or not '2017-01-01' <= day <= '2019-04-06':
            continue
        if timestamp % (86400 * 10**9):
            raise ValueError('Unexpected timestamp')
        values = [struct.unpack_from('<d', numeric, (col*n + i)*8)[0] for col in (1, 2, 3)]
        if not all(math.isfinite(v) and v > 0 for v in values):
            raise ValueError(f'Invalid price or volume for {symbol} {day}')
        key = day, symbol
        if key in observed:
            if values != observed[key]:
                raise ValueError(f'Conflicting observations for {key}')
            continue
        observed[key] = values
        writer.writerow([day, symbol, *values])


if __name__ == '__main__':
    extract(Path(sys.argv[1]), sys.stdout)
