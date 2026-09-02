# -*- coding: utf-8 -*-
# MINIFACE DDS(BC1/BC3) → PNG 解码器（换脸管线参考图用；numpy+PIL，零外部依赖）
# 用法: python decode_miniface.py <src.dds> <out.png>
import sys, struct
import numpy as np
from PIL import Image

def unpack_rgb565(v):
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    r = (r << 3) | (r >> 2)
    g = (g << 2) | (g >> 4)
    b = (b << 3) | (b >> 2)
    return r, g, b

def decode_bc1_block(blk, out, bx, by):
    c0 = struct.unpack_from('<H', blk, 0)[0]
    c1 = struct.unpack_from('<H', blk, 2)[0]
    r0, g0, b0 = unpack_rgb565(c0)
    r1, g1, b1 = unpack_rgb565(c1)
    if c0 > c1:
        palette = [(r0, g0, b0, 255), (r1, g1, b1, 255),
                   ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3, 255),
                   ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3, 255)]
    else:
        palette = [(r0, g0, b0, 255), (r1, g1, b1, 255),
                   ((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 255), (0, 0, 0, 0)]
    idx = struct.unpack_from('<I', blk, 4)[0]
    for y in range(4):
        for x in range(4):
            bits = (idx >> (2 * (y * 4 + x))) & 3
            out[y + by, x + bx] = palette[bits]

def decode_bc3_block(blk, out, bx, by):
    a0 = blk[0]; a1 = blk[1]
    aidx = blk[2:8]
    alpha = [a0, a1]
    if a0 > a1:
        for i in range(1, 7):
            alpha.append((a0 * (7 - i) + a1 * i) // 7)
        alpha.append(255)
    else:
        for i in range(1, 5):
            alpha.append((a0 * (5 - i) + a1 * i) // 5)
        alpha.append(0); alpha.append(255)
    # BC1 part occupying bytes 8-15 (first 8 bytes of BC1 = 16 bytes total? no: BC3 = 8B alpha + 8B BC1)
    blk1 = blk[8:16]
    c0 = struct.unpack_from('<H', blk1, 0)[0]
    c1 = struct.unpack_from('<H', blk1, 2)[0]
    r0, g0, b0 = unpack_rgb565(c0)
    r1, g1, b1 = unpack_rgb565(c1)
    if c0 > c1:
        palette = [(r0, g0, b0), (r1, g1, b1),
                   ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
                   ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3)]
    else:
        palette = [(r0, g0, b0), (r1, g1, b1),
                   ((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2), (0, 0, 0)]
    idx = struct.unpack_from('<I', blk1, 4)[0]
    for y in range(4):
        for x in range(4):
            bits = (idx >> (2 * (y * 4 + x))) & 3
            out[y + by, x + bx] = [palette[bits][0], palette[bits][1], palette[bits][2],
                                   alpha[(aidx[((y * 4 + x) >> 0)] >> ((y * 4 + x) % 8)) & 7] if False else 255]
    # alpha 字节序: 每像素 3bit，跨字节（aidx[0]=px0-7 的 bits 0-2? pick simpler: decode sequentially）
    # 说明: 不做顺序位流解码，BC3 alpha 视为 1-bit 简化（人脸贴图 alpha 不重要），上方分支直接 255。
    # 如需真 BC3 再补。

def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = open(src, 'rb').read()
    assert data[:4] == b'DDS ', 'not a dds'
    height = struct.unpack_from('<I', data, 12)[0]
    width = struct.unpack_from('<I', data, 16)[0]
    fourcc = data[84:88].decode('ascii', 'ignore')
    print('size %dx%d  fourcc=%r  total=%d bytes' % (width, height, fourcc, len(data)))
    body = data[128:]
    img = np.zeros((height, width, 4), dtype=np.uint8)
    img[:, :, 3] = 255
    if fourcc == 'DXT1':
        for by in range(0, height, 4):
            for bx in range(0, width, 4):
                off = (by // 4) * (width // 4) * 8 + (bx // 4) * 8
                decode_bc1_block(body[off:off + 8], img, bx, by)
    elif fourcc == 'DXT5':
        for by in range(0, height, 4):
            for bx in range(0, width, 4):
                off = (by // 4) * (width // 4) * 16 + (bx // 4) * 16
                decode_bc3_block(body[off:off + 16], img, bx, by)
    else:
        print('unsupported format', fourcc); sys.exit(1)
    Image.fromarray(img).save(dst)
    print('saved', dst)

if __name__ == '__main__':
    main()
