#!/usr/bin/env python3
"""
Read a G-code file back, draw what the cutter does, and check it against the
nested DXF: nothing cut outside the stock, no cut into a part, every part and hole
cut through, and tabs where the file says they are.

    python3 backplot.py <out.png> <nested sheet .dxf> <file.nc> [more .nc files run on the same zero]
"""
import argparse, math, re, sys
import ezdxf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely import prepared


def parse(path):
    """Yield (kind, x0, y0, z0, x1, y1, z1) with arcs split into short lines."""
    x = y = 0.0
    z = 50.0                      # unknown until the first Z move; assume clear
    mode = 0
    segs = []
    word = re.compile(r'([A-Z])(-?\d+\.?\d*)')
    for raw in open(path):
        line = re.sub(r'\(.*?\)', '', raw).strip().upper()
        if not line or line == '%':
            continue
        w = dict(word.findall(line))
        g = [int(float(v)) for k, v in word.findall(line) if k == 'G']
        for gg in g:
            if gg in (0, 1, 2, 3):
                mode = gg
        if not any(k in w for k in 'XYZ'):
            continue
        nx = float(w.get('X', x)); ny = float(w.get('Y', y)); nz = float(w.get('Z', z))
        if mode in (0, 1):
            segs.append((mode, x, y, z, nx, ny, nz))
        else:
            cx = x + float(w.get('I', 0)); cy = y + float(w.get('J', 0))
            r = math.hypot(x - cx, y - cy)
            a0 = math.atan2(y - cy, x - cx); a1 = math.atan2(ny - cy, nx - cx)
            if mode == 3:
                sweep = (a1 - a0) % (2 * math.pi) or 2 * math.pi
            else:
                sweep = -((a0 - a1) % (2 * math.pi) or 2 * math.pi)
            n = max(8, int(abs(sweep) * r / 0.5))
            px, py, pz = x, y, z
            for k in range(1, n + 1):
                a = a0 + sweep * k / n
                qx, qy, qz = cx + r * math.cos(a), cy + r * math.sin(a), z + (nz - z) * k / n
                segs.append((1, px, py, pz, qx, qy, qz))
                px, py, pz = qx, qy, qz
        x, y, z = nx, ny, nz
    return segs


def parts_from_dxf(path):
    msp = ezdxf.readfile(path).modelspace()
    stock = None
    polys, holes = [], []
    for e in msp:
        if e.dxftype() == 'LWPOLYLINE':
            pts = [(v.x, v.y) for v in ezdxf.path.make_path(e).flattening(0.02)]
            if e.dxf.layer.startswith('STOCK'):
                stock = Polygon(pts)
            else:
                polys.append(Polygon(pts))
        elif e.dxftype() == 'CIRCLE':
            holes.append((e.dxf.center.x, e.dxf.center.y, e.dxf.radius))
    return stock, polys, holes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('png'); ap.add_argument('dxf'); ap.add_argument('nc', nargs='+')
    ap.add_argument('--tool-d', type=float, default=6.35)
    a = ap.parse_args()
    r = a.tool_d / 2
    segs = [s for f in a.nc for s in parse(f)]
    stock, polys, holes = parts_from_dxf(a.dxf)
    solid = unary_union([p.difference(unary_union([Point(hx, hy).buffer(hr, 256) for hx, hy, hr in holes]))
                         for p in polys])
    # the part material the cutter must never enter, shrunk a hair for arc chord error
    keep = prepared.prep(solid.buffer(r - 0.05))
    cuts = [s for s in segs if s[0] == 1 and min(s[3], s[6]) < 0]
    zmin = min(min(s[3], s[6]) for s in cuts)
    problems = []

    for s in cuts:
        seg = LineString([(s[1], s[2]), (s[4], s[5])]) if (s[1], s[2]) != (s[4], s[5]) else Point(s[1], s[2])
        if keep.intersects(seg):
            problems.append(f'gouge near X{s[4]:.2f} Y{s[5]:.2f}')
        if stock is not None and not stock.buffer(-r).contains(seg):
            problems.append(f'cuts outside the stock near X{s[4]:.2f} Y{s[5]:.2f}')
    for s in segs:
        moves_xy = (s[1], s[2]) != (s[4], s[5])
        if s[0] == 0 and (s[6] < 1.0 or (moves_xy and min(s[3], s[6]) < 1.0)):
            problems.append(f'rapid below Z1 near X{s[4]:.2f} Y{s[5]:.2f}')

    # every hole reached full depth all the way round; every part fully cut except tabs
    for hx, hy, hr in holes:
        deep = [s for s in cuts if math.hypot(s[4] - hx, s[5] - hy) < hr and s[6] <= zmin + 1e-6]
        if len(deep) < 8:
            problems.append(f'hole at X{hx:.1f} Y{hy:.1f} not cut to depth')
    tab_lengths = []
    for p in polys:
        ring = p.buffer(r, quad_segs=64).exterior
        near = [s for s in cuts if ring.distance(Point(s[4], s[5])) < 0.2]
        full = [s for s in near if s[3] <= zmin + 1e-6 and s[6] <= zmin + 1e-6]
        cut_len = sum(math.hypot(s[4] - s[1], s[5] - s[2]) for s in full)
        tabs = ring.length - cut_len
        tab_lengths.append((round(ring.length), round(tabs)))
        if cut_len < 0.9 * ring.length:
            problems.append(f'part at {p.bounds[0]:.0f},{p.bounds[1]:.0f} only {cut_len:.0f} of {ring.length:.0f} mm at full depth')

    fig, ax = plt.subplots(figsize=(11, 11 * (stock.bounds[3] / stock.bounds[2]) if stock else 11))
    if stock is not None:
        ax.plot(*stock.exterior.xy, color='#888', lw=1)
    for p in polys:
        ax.fill(*p.exterior.xy, color='#e8d3b0', lw=0)
    rap = [((s[1], s[2]), (s[4], s[5])) for s in segs if s[0] == 0 and (s[1], s[2]) != (s[4], s[5])]
    ax.add_collection(LineCollection(rap, colors='#bbbbbb', lw=0.5, linestyles='dotted'))
    full = [((s[1], s[2]), (s[4], s[5])) for s in cuts if s[6] <= zmin + 1e-6 and s[3] <= zmin + 1e-6]
    part = [((s[1], s[2]), (s[4], s[5])) for s in cuts if not (s[6] <= zmin + 1e-6 and s[3] <= zmin + 1e-6)]
    ax.add_collection(LineCollection(part, colors='#e67e22', lw=1.8))
    ax.add_collection(LineCollection(full, colors='#1f5fbf', lw=1.0))
    for hx, hy, hr in holes:
        ax.add_patch(plt.Circle((hx, hy), hr, color='#c0392b', fill=False, lw=1))
    ax.set_aspect('equal'); ax.autoscale()
    ax.set_title(f'{" + ".join(f.split("/")[-1] for f in a.nc)}\nblue = through cut, orange = tabs / ramp laps, '
                 f'dotted = rapids; deepest Z {zmin:.2f} mm', fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(a.png, dpi=110)

    print(f'{" + ".join(a.nc)}: {len(segs)} moves, deepest Z {zmin:.2f}')
    print('  per part: toolpath length / length left as tabs (mm):', tab_lengths)
    if problems:
        print('  PROBLEMS:'); [print('   ', p) for p in sorted(set(problems))[:30]]
        sys.exit(1)
    print('  OK: no gouges, nothing outside the stock, all holes and profiles cut through')


if __name__ == '__main__':
    main()
