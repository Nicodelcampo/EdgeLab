#!/usr/bin/env python3
"""Lector minimo de parquet para ambientes sin pyarrow/duckdb (sandbox de auditoria).

Escrito 2026-08-14 durante la replica de paridad W1 (ver
docs/research/HANDOFF_AUDITORIA_2026-08-14.md §5). Soporta lo que los parquets
canonicos de EdgeLab usan hoy:

- footer Thrift compact protocol (FileMetaData)
- paginas DATA_PAGE v1 y v2
- codecs: UNCOMPRESSED, ZSTD (via ctypes + libzstd del sistema), SNAPPY (raw,
  decodificador propio), GZIP
- PLAIN, RLE/bit-packed hybrid, RLE_DICTIONARY (diccionario + indices)
- columnas opcionales (definition levels) y requeridas

Uso:  python3 tools/sandbox_pqread.py <file.parquet> <out.npz> [col1,col2,...]

Nota de alcance: es un lector de DIAGNOSTICO para replicar paridad donde no hay
pyarrow. No reemplaza al lector canonico local; su unica garantia es haber
reproducido conteos y contenidos contra oraculos sellados el 2026-08-14.
"""
import struct, sys, ctypes, ctypes.util
import numpy as np

CT = dict(STOP=0, TRUE=1, FALSE=2, BYTE=3, I16=4, I32=5, I64=6, DBL=7, BIN=8, LIST=9, SET=10, MAP=11, STRUCT=12)

def rvarint(b, p):
    r = 0; s = 0
    while True:
        x = b[p]; p += 1
        r |= (x & 0x7f) << s
        if not (x & 0x80): break
        s += 7
    return r, p

def zz(v): return (v >> 1) ^ -(v & 1)

def read_val(b, p, t):
    if t == CT['TRUE']: return True, p
    if t == CT['FALSE']: return False, p
    if t == CT['BYTE']: return b[p], p + 1
    if t in (CT['I16'], CT['I32'], CT['I64']):
        v, p = rvarint(b, p); return zz(v), p
    if t == CT['DBL']: return struct.unpack('<d', b[p:p+8])[0], p + 8
    if t == CT['BIN']:
        n, p = rvarint(b, p)
        return b[p:p+n], p + n
    if t in (CT['LIST'], CT['SET']):
        h = b[p]; p += 1
        n, et = h >> 4, h & 0x0f
        if n == 15: n, p = rvarint(b, p)
        out = []
        for _ in range(n):
            v, p = read_val(b, p, et)
            out.append(v)
        return out, p
    if t == CT['STRUCT']:
        return read_struct(b, p)
    raise ValueError(f'tipo {t}')

def read_struct(b, p):
    out = {}
    last = 0
    while True:
        h = b[p]; p += 1
        if h == 0: break
        delta, t = h >> 4, h & 0x0f
        if delta == 0:
            fid, p = rvarint(b, p); fid = zz(fid)
        else:
            fid = last + delta
        last = fid
        v, p = read_val(b, p, t)
        out[fid] = v
    return out, p

# --- zstd via ctypes (libzstd del sistema) ---
_libname = ctypes.util.find_library('zstd') or 'libzstd.so.1'
_z = ctypes.CDLL(_libname)
_z.ZSTD_getFrameContentSize.restype = ctypes.c_ulonglong
_z.ZSTD_decompress.restype = ctypes.c_size_t
_z.ZSTD_isError.restype = ctypes.c_uint

def zstd_decomp(buf, out_size):
    dst = ctypes.create_string_buffer(out_size)
    r = _z.ZSTD_decompress(dst, out_size, buf, len(buf))
    if _z.ZSTD_isError(r): raise RuntimeError('zstd decompress error')
    return dst.raw[:r]

def snappy_decomp(buf):
    """Snappy RAW (no framed): varint total + elementos literal/copia LZ77."""
    buf = memoryview(bytes(buf))
    p = 0; total = 0; shift = 0
    while True:
        x = buf[p]; p += 1
        total |= (x & 0x7f) << shift
        if not (x & 0x80): break
        shift += 7
    out = bytearray(total)
    q = 0
    nbuf = len(buf)
    while p < nbuf:
        tag = buf[p]; p += 1
        typ = tag & 3
        if typ == 0:
            ln = tag >> 2
            if ln >= 60:
                nb = ln - 59
                ln = int.from_bytes(buf[p:p+nb], 'little'); p += nb
            ln += 1
            out[q:q+ln] = buf[p:p+ln]; p += ln; q += ln
        else:
            if typ == 1:
                ln = ((tag >> 2) & 7) + 4
                off = ((tag >> 5) << 8) | buf[p]; p += 1
            elif typ == 2:
                ln = (tag >> 2) + 1
                off = int.from_bytes(buf[p:p+2], 'little'); p += 2
            else:
                ln = (tag >> 2) + 1
                off = int.from_bytes(buf[p:p+4], 'little'); p += 4
            if off >= ln:
                out[q:q+ln] = out[q-off:q-off+ln]
                q += ln
            else:
                for _ in range(ln):
                    out[q] = out[q-off]; q += 1
    return bytes(out)

def decomp(buf, codec, out_size):
    if codec == 0: return bytes(buf)
    if codec == 6: return zstd_decomp(bytes(buf), out_size)
    if codec == 1: return snappy_decomp(buf)
    if codec == 2:
        import zlib; return zlib.decompress(bytes(buf), 31)
    raise RuntimeError(f'codec no soportado: {codec}')

# --- RLE / bit-packed hybrid ---
def rle_hybrid(buf, p, bitwidth, n):
    vals = np.empty(n, dtype=np.int64)
    filled = 0
    while filled < n:
        h, p = rvarint(buf, p)
        if h & 1 == 0:
            cnt = h >> 1
            nb = (bitwidth + 7) // 8
            v = int.from_bytes(buf[p:p+nb], 'little') if nb else 0
            p += nb
            vals[filled:filled+cnt] = v
            filled += cnt
        else:
            groups = h >> 1
            nv = groups * 8
            nbytes = groups * bitwidth
            chunk = buf[p:p+nbytes]; p += nbytes
            x = int.from_bytes(chunk, 'little')
            mask = (1 << bitwidth) - 1
            for i in range(nv):
                if filled >= n: break
                vals[filled] = (x >> (i * bitwidth)) & mask
                filled += 1
    return vals, p

def plain_decode(buf, ptype, n):
    if ptype == 1: return np.frombuffer(buf, '<i4', n).astype(np.int64), 4*n
    if ptype == 2: return np.frombuffer(buf, '<i8', n).astype(np.int64), 8*n
    if ptype == 6:
        out = []; p = 0
        for _ in range(n):
            ln = struct.unpack('<i', buf[p:p+4])[0]; p += 4
            out.append(buf[p:p+ln]); p += ln
        return np.array(out), p
    raise RuntimeError(f'plain tipo {ptype}')

def decode_column(d, meta, ptype, optional=False):
    codec = meta.get(4, 0)
    nvals = meta.get(5)
    data_off = meta.get(9)
    dict_off = meta.get(11)
    dictionary = None
    if dict_off is not None:
        p = dict_off
        hdr, p = read_struct(d, p)
        assert hdr.get(1) == 2, f'esperaba DICTIONARY_PAGE, got {hdr.get(1)}'
        raw = decomp(d[p:p+hdr[3]], codec, hdr[2])
        dh = hdr.get(7, {})
        dictionary, _ = plain_decode(raw, ptype, dh.get(1))
    out = np.empty(nvals, dtype=object if ptype == 6 else np.int64)
    filled = 0
    p = data_off
    while filled < nvals:
        hdr, p = read_struct(d, p)
        ptype_page = hdr.get(1)
        unc, comp_size = hdr[2], hdr[3]
        comp = d[p:p+comp_size]
        p = p + comp_size
        if ptype_page == 0:  # DATA_PAGE v1
            raw = decomp(comp, codec, unc)
            dh = hdr[5]
            n = dh[1]; enc = dh[2]
            q = 0
            if optional:
                ln = struct.unpack('<i', raw[q:q+4])[0]; q += 4
                deflv, q = rle_hybrid(raw, q, 1, n)
                n_pres = int(deflv.sum())
            else:
                n_pres = n
            if enc in (2, 8) and dictionary is not None:
                bw = raw[q]; q += 1
                idx, q = rle_hybrid(raw, q, bw, n_pres)
                vals = dictionary[idx]
            elif enc == 0:
                vals, used = plain_decode(raw[q:], ptype, n_pres)
                q += used
            else:
                raise RuntimeError(f'encoding v1 {enc}')
            out[filled:filled+n] = vals
            filled += n
        elif ptype_page == 3:  # DATA_PAGE v2
            dh = hdr[8]
            n = dh[1]; n_nulls = dh.get(2, 0); enc = dh[4]
            deflen = dh.get(5, 0); replen = dh.get(6, 0)
            raw = decomp(comp, codec, unc)
            q = replen
            if deflen:
                deflv, q2 = rle_hybrid(raw, q, 1, n)
                q = q2
            if enc in (8, 2):
                bw = raw[q]; q += 1
                idx, q = rle_hybrid(raw, q, bw, n - n_nulls)
                vals = dictionary[idx]
            elif enc == 0:
                vals, used = plain_decode(raw[q:], ptype, n - n_nulls)
                q += used
            else:
                raise RuntimeError(f'encoding v2 {enc}')
            out[filled:filled+n] = vals
            filled += n
        else:
            raise RuntimeError(f'page type {ptype_page}')
    return out

def main():
    path, outnpz = sys.argv[1], sys.argv[2]
    want = set(sys.argv[3].split(',')) if len(sys.argv) > 3 else None
    d = open(path, 'rb').read()
    flen = struct.unpack('<i', d[-8:-4])[0]
    meta, _ = read_struct(d, len(d) - 8 - flen)
    schema = meta[2]
    leafs = [s for s in schema[1:]]
    names = [s.get(4).decode() for s in leafs]
    types = {s.get(4).decode(): s.get(1) for s in leafs}
    rept  = {s.get(4).decode(): s.get(3) for s in leafs}
    print('filas totales:', meta[3])
    cols = {n: [] for n in names if want is None or n in want}
    for rg in meta[4]:
        for ch in rg[1]:
            m = ch[3]
            nm = m[3][0].decode() if isinstance(m[3][0], bytes) else m[3][0]
            if nm not in cols: continue
            cols[nm].append(decode_column(d, m, types[nm], optional=(rept[nm] == 1)))
    final = {}
    for nm, parts in cols.items():
        if not parts: continue
        final[nm] = np.concatenate(parts)
        print(nm, 'filas:', len(final[nm]))
    np.savez(outnpz, **final)
    print('guardado en', outnpz)

if __name__ == '__main__':
    main()
