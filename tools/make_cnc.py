#!/usr/bin/env python3
"""
Nest the Bullitt X box panels for a Shapeoko and write DXF, SVG and G-code.

The design was drawn for 10 mm ply.  For thicker ply (1/2" is really 11.9-12.7 mm)
four things change, all worked out against the 3D assembly in Vermoot's STEP file:

  * Side panels: the links bolt to the inner face, so the extra thickness goes
    outward.  Nearest frame tube is 7.8 mm away at 10 mm, so nothing to change.
  * Front and back panels: bolted to the frame by their outer face, so they grow
    into the box.  The front and back links bolt to that inner face, so each link
    slides into the box by the extra thickness along the panel's normal.  The two
    link holes in the side panel move with them (front: 15 deg lean, back: 1 deg).
  * Floor: sits on the cross beams and grows upward, which eats Vermoot's 3 mm gap
    under the front and back panels.  Their bottom edges are trimmed by the extra
    thickness to give it back.
  * Bottom links: bolt to the side panel inner face and peg into the frame; unchanged.

Usage:
    python3 make_cnc.py <folder with Vermoot's front/back panel DXFs> [options]
"""
import argparse, copy, math, os
import ezdxf
from ezdxf.math import Matrix44
from shapely.geometry import Polygon, LineString, Point
from shapely.geometry.polygon import orient

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
INCH = 25.4

# Inward normals of the front and back panels in the side panel's (x, height) plane,
# taken from the STEP assembly: the front panel leans 15 deg, the back panel 1 deg.
FRONT_N = (-math.cos(math.radians(15)), math.sin(math.radians(15)))
BACK_N = (math.cos(math.radians(1)), math.sin(math.radians(1)))

# ---------------------------------------------------------------- part geometry

def read_part(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    poly = next(e for e in msp if e.dxftype() == 'LWPOLYLINE')
    holes = [(c.dxf.center.x, c.dxf.center.y, c.dxf.radius, '')
             for c in msp if c.dxftype() == 'CIRCLE']
    return list(poly.get_points('xyb')), holes


def adjust_for_thickness(parts, t):
    """Apply the thickness changes described in the module docstring, in place."""
    dt = t - 10.0
    side = parts['side']
    for i, (x, y, r, tag) in enumerate(side['holes']):
        if x > 900 and y > 150:                                  # front-link bolt
            side['holes'][i] = (x + FRONT_N[0] * dt, y + FRONT_N[1] * dt, r, 'front-link')
        elif x < 100 and y > 250:                                # back-link bolt
            side['holes'][i] = (x + BACK_N[0] * dt, y + BACK_N[1] * dt, r, tag)
    # Front panel: bottom edge is the straight one at x = 216.66 (x runs up the panel).
    parts['front']['pts'] = [(x + dt if x < 230 else x, y, b)
                             for x, y, b in parts['front']['pts']]
    # Back panel: bottom edge is the straight one at x = -22.71 (x runs down the panel).
    parts['back']['pts'] = [(x - dt if x > -45 else x, y, b)
                            for x, y, b in parts['back']['pts']]


def transform(pts, holes, m):
    """Apply a 2D affine (Matrix44) to bulge points and holes; mirroring flips bulges."""
    mirror = m.determinant() < 0
    out = []
    for x, y, b in pts:
        v = m.transform((x, y, 0))
        out.append((v.x, v.y, -b if mirror else b))
    hs = []
    for x, y, r, tag in holes:
        v = m.transform((x, y, 0))
        hs.append((v.x, v.y, r, tag))
    return out, hs


def flatten(pts, tol=0.02):
    """Bulge polyline -> list of (x, y), arcs split to chord error <= tol."""
    out = []
    n = len(pts)
    for i in range(n):
        x0, y0, b = pts[i]
        x1, y1, _ = pts[(i + 1) % n]
        out.append((x0, y0))
        if abs(b) < 1e-9:
            continue
        th = 4 * math.atan(b)
        chord = math.hypot(x1 - x0, y1 - y0)
        r = chord / (2 * math.sin(abs(th) / 2))
        # centre: perpendicular from chord midpoint
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        d = r * math.cos(abs(th) / 2)
        ux, uy = (x1 - x0) / chord, (y1 - y0) / chord
        s = 1 if (b > 0) == (abs(th) < math.pi) else -1
        cx, cy = mx - uy * d * s, my + ux * d * s
        a0 = math.atan2(y0 - cy, x0 - cx)
        seg = max(2, int(math.ceil(abs(th) / (2 * math.acos(max(-1, 1 - tol / r))))))
        for k in range(1, seg):
            a = a0 + th * k / seg
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def bbox(pts, holes=()):
    fl = flatten(pts)
    xs = [p[0] for p in fl]; ys = [p[1] for p in fl]
    return min(xs), min(ys), max(xs), max(ys)


def place(pts, holes, rot=0, mirror=False, at=(0, 0)):
    """Rotate/mirror a part, then move its bounding box's lower-left corner to `at`."""
    m = Matrix44()
    if mirror:
        m = m @ Matrix44.scale(-1, 1, 1)
    if rot:
        m = m @ Matrix44.z_rotate(math.radians(rot))
    p, h = transform(pts, holes, m)
    x0, y0, _, _ = bbox(p)
    return transform(p, h, Matrix44.translate(at[0] - x0, at[1] - y0, 0))


# ---------------------------------------------------------------- sheet layouts

def layouts(parts, gap, sheet_a, stock_b, margin_b):
    """Return [(sheet name, (w, h), [(label, pts, holes), ...]), ...]."""
    def size(p, **kw):
        q, _ = place(p['pts'], p['holes'], **kw)
        x0, y0, x1, y1 = bbox(q)
        return x1 - x0, y1 - y0

    # Sheet A: floor, then the two side panels stacked, centred on the sheet.
    W, H = sheet_a
    fw, fh = size(parts['floor'])
    sw, sh = size(parts['side'])
    y = (H - (fh + 2 * sh + 2 * gap)) / 2
    a = []
    a.append(('floor',) + place(parts['floor']['pts'], parts['floor']['holes'],
                                at=((W - fw) / 2, y)))
    y += fh + gap
    a.append(('side panel, RIGHT',) + place(parts['side']['pts'], parts['side']['holes'],
                                            at=((W - sw) / 2, y)))
    y += sh + gap
    a.append(('side panel, LEFT (mirrored)',) + place(parts['side']['pts'], parts['side']['holes'],
                                                      mirror=True, at=((W - sw) / 2, y)))

    # Sheet B: front and back panels side by side from the lower-left corner.
    b = []
    frw, frh = size(parts['front'])
    b.append(('front panel',) + place(parts['front']['pts'], parts['front']['holes'],
                                      at=(margin_b, margin_b)))
    b.append(('back panel',) + place(parts['back']['pts'], parts['back']['holes'],
                                     at=(margin_b + frw + gap, margin_b)))
    return [('sheet-A_floor-and-sides', sheet_a, a),
            ('sheet-B_front-and-back', stock_b, b)]


def check_layout(name, size, items, gap, tool_d, margin):
    W, H = size
    polys = [Polygon(flatten(p)) for _, p, _ in items]
    for (lab, p, holes), poly in zip(items, polys):
        assert poly.is_valid, lab
        x0, y0, x1, y1 = poly.bounds
        # the cutter runs tool_d outside the part; keep that inside the stock with room
        assert x0 - tool_d >= margin and y0 - tool_d >= margin, (name, lab, 'off sheet')
        assert x1 + tool_d <= W - margin and y1 + tool_d <= H - margin, (name, lab, 'off sheet')
        for hx, hy, r, _ in holes:
            assert poly.contains(Point(hx, hy).buffer(r + 3)), (name, lab, 'hole near edge')
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            d = polys[i].distance(polys[j])
            assert d >= gap - 0.01, (name, items[i][0], items[j][0], d)


# ---------------------------------------------------------------- DXF and SVG

def write_dxf(path, size, items):
    doc = ezdxf.new('R2010', setup=True)
    doc.units = ezdxf.units.MM
    doc.header['$INSUNITS'] = 4
    doc.header['$MEASUREMENT'] = 1
    doc.layers.add('STOCK_OUTLINE_do_not_cut', color=8)
    doc.layers.add('HOLES', color=1)
    doc.layers.add('HOLES_front_link_optional', color=6)
    doc.layers.add('PROFILES', color=5)
    msp = doc.modelspace()
    if size:
        W, H = size
        msp.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True,
                           dxfattribs={'layer': 'STOCK_OUTLINE_do_not_cut'})
    for _, pts, holes in items:
        msp.add_lwpolyline(pts, format='xyb', close=True, dxfattribs={'layer': 'PROFILES'})
        for x, y, r, tag in holes:
            layer = 'HOLES_front_link_optional' if tag == 'front-link' else 'HOLES'
            msp.add_circle((x, y), r, dxfattribs={'layer': layer})
    doc.saveas(path)


def svg_path(pts, H):
    """Bulge polyline -> SVG path with true arcs, y flipped so the sheet's (0,0) is bottom-left."""
    def P(x, y):
        return f'{x:.4f},{H - y:.4f}'
    d = [f'M{P(pts[0][0], pts[0][1])}']
    n = len(pts)
    for i in range(n):
        x0, y0, b = pts[i]
        x1, y1, _ = pts[(i + 1) % n]
        if abs(b) < 1e-9:
            d.append(f'L{P(x1, y1)}')
        else:
            th = 4 * math.atan(b)
            r = math.hypot(x1 - x0, y1 - y0) / (2 * math.sin(abs(th) / 2))
            large = 1 if abs(th) > math.pi else 0
            sweep = 0 if b > 0 else 1        # the y flip reverses the turning direction
            d.append(f'A{r:.4f},{r:.4f} 0 {large} {sweep} {P(x1, y1)}')
    return ' '.join(d) + ' Z'


def write_svg(path, size, items):
    W, H = size
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}mm" height="{H:.2f}mm" '
           f'viewBox="0 0 {W:.3f} {H:.3f}">',
           f'<rect id="stock_outline_do_not_cut" x="0" y="0" width="{W:.3f}" height="{H:.3f}" '
           f'fill="none" stroke="#999" stroke-width="0.5"/>']
    for n, (lab, pts, holes) in enumerate(items, 1):
        gid = f'part{n}_' + lab.replace(',', '').replace('(', '').replace(')', '').replace(' ', '_')
        out.append(f'<g id="{gid}">')
        out.append(f'<path d="{svg_path(pts, H)}" fill="none" stroke="#1f5fbf" stroke-width="0.5"/>')
        for x, y, r, tag in holes:
            extra = ' class="front_link_hole_optional"' if tag else ''
            out.append(f'<circle{extra} cx="{x:.4f}" cy="{H - y:.4f}" r="{r:.4f}" '
                       f'fill="none" stroke="#c0392b" stroke-width="0.5"/>')
        out.append('</g>')
    out.append('</svg>')
    open(path, 'w').write('\n'.join(out) + '\n')


# ---------------------------------------------------------------- G-code

class Gcode:
    def __init__(self, a):
        self.a = a
        self.lines = []
        self.z = None

    def emit(self, s):
        self.lines.append(s)

    def rapid_to(self, x, y):
        self.emit(f'G0 Z{self.a.safe_z:.3f}')
        self.emit(f'G0 X{x:.3f} Y{y:.3f}')
        self.z = self.a.safe_z


def fmt(v):
    return f'{v:.3f}'


def helical_hole(g, x, y, r_hole, depth):
    a = g.a
    rt = a.tool_d / 2
    rh = r_hole - rt
    assert rh > 0.2, 'hole too small for this cutter'
    g.emit(f'( hole d{2 * r_hole:.1f} at X{x:.2f} Y{y:.2f} )')
    g.rapid_to(x + rh, y)
    g.emit(f'G0 Z{a.clear_z:.3f}')
    g.emit(f'G1 Z0.000 F{a.plunge:.0f}')
    z = 0.0
    g.emit(f'F{a.hole_feed:.0f}')
    while z > -depth + 1e-6:
        z = max(z - a.helix_pitch, -depth)
        # G3 = counter-clockwise = climb milling inside a hole with a clockwise spindle
        g.emit(f'G3 X{fmt(x + rh)} Y{fmt(y)} Z{fmt(z)} I{fmt(-rh)} J0')
    g.emit(f'G3 X{fmt(x + rh)} Y{fmt(y)} I{fmt(-rh)} J0')     # clean-up lap at full depth
    g.emit(f'G1 X{fmt(x)} Y{fmt(y)}')                         # off the wall before lifting
    g.emit(f'G0 Z{a.safe_z:.3f}')


def resample(coords, step):
    """Closed ring -> points no more than `step` apart, with cumulative distance."""
    out = []
    s = 0.0
    for i in range(len(coords) - 1):
        (x0, y0), (x1, y1) = coords[i], coords[i + 1]
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(math.ceil(L / step)))
        for k in range(n):
            out.append((x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, s + L * k / n))
        s += L
    out.append((coords[-1][0], coords[-1][1], s))
    return out, s


def pick_tabs(ring, part_poly, n_tabs, tab_len):
    """Choose tab centres (as distance along the toolpath) on straight stretches."""
    total = ring.length
    centres = []
    for k in range(n_tabs):
        want = total * (k + 0.5) / n_tabs
        best = None
        for shift in range(0, int(total / n_tabs / 2), 5):
            for sgn in (1, -1):
                s = (want + sgn * shift) % total
                # straight if the path is a line over the tab window
                p0 = ring.interpolate(s - tab_len / 2 - 5)
                p1 = ring.interpolate(s + tab_len / 2 + 5)
                pm = ring.interpolate(s)
                dev = LineString([p0, p1]).distance(pm)
                if dev < 0.05 and s - tab_len > 0 and s + tab_len < total:
                    best = s
                    break
            if best is not None:
                break
        centres.append(best if best is not None else want)
    return sorted(centres)


def profile(g, label, pts, depth):
    """Outside profile, climb milled, spiralling down one step per lap, with tabs."""
    a = g.a
    rt = a.tool_d / 2
    part = Polygon(flatten(pts))
    path = part.buffer(rt, quad_segs=64, join_style='round')
    ring = orient(path, sign=-1.0).exterior          # clockwise = climb on the outside
    coords = list(ring.coords)
    # start on the lowest-left point so every part starts somewhere predictable
    i0 = min(range(len(coords) - 1), key=lambda i: (coords[i][1], coords[i][0]))
    coords = coords[i0:-1] + coords[:i0] + [coords[i0]]
    ring = LineString(coords)
    total = ring.length

    n_tabs = max(4, int(round(total / a.tab_spacing)))
    span = a.tab_len + a.tool_d          # path length held up so tab_len of wood is left
    tabs = pick_tabs(ring, part, n_tabs, span)
    z_tab = -depth + a.tab_h

    def in_tab(s):
        s %= total
        return any(abs(s - c) <= span / 2 + 1e-6 for c in tabs)

    pts_s, _ = resample(coords, 2.0)
    # add the exact tab edges so the cutter steps up and down on the tab boundary
    edges = sorted(set([c - span / 2 for c in tabs] + [c + span / 2 for c in tabs]))

    g.emit(f'( profile: {label.replace("(", "").replace(")", "")}, {len(tabs)} tabs {a.tab_len:.0f} mm long x {a.tab_h:.0f} mm thick )')
    x0, y0 = coords[0]
    g.rapid_to(x0, y0)
    g.emit(f'G0 Z{a.clear_z:.3f}')
    g.emit(f'G1 Z0.000 F{a.plunge:.0f}')
    g.emit(f'F{a.feed:.0f}')

    laps = int(math.ceil(depth / a.stepdown - 1e-9))
    zc = 0.0
    for lap in range(laps + 1):
        final = lap == laps
        z_start = -min(depth, lap * a.stepdown)
        z_end = -min(depth, (lap + 1) * a.stepdown)
        seq = [(x, y, s) for x, y, s in pts_s[1:]]
        # merge in tab edges as extra points
        extra = []
        for e in edges:
            p = ring.interpolate(e % total)
            extra.append((p.x, p.y, e % total))
        seq = sorted(seq + extra, key=lambda t: t[2])
        for x, y, s in seq:
            zt = z_end if final else z_start + (z_end - z_start) * s / total
            want = z_tab if (in_tab(s) and zt < z_tab) else zt
            if want > zc + 1e-6:
                # reached the start of a tab: finish the move at depth, then lift onto it
                g.emit(f'G1 X{fmt(x)} Y{fmt(y)} Z{fmt(zt)}')
                g.emit(f'G1 Z{fmt(want)}')
            elif want < zc - 0.5:
                # just left a tab: step back down where we are, at plunge rate
                g.emit(f'G1 Z{fmt(want)} F{a.plunge:.0f}')
                g.emit(f'G1 X{fmt(x)} Y{fmt(y)} F{a.feed:.0f}')
            else:
                g.emit(f'G1 X{fmt(x)} Y{fmt(y)} Z{fmt(want)}')
            zc = want
    g.emit(f'G0 Z{a.safe_z:.3f}')
    return tabs, ring


def write_gcode(path, title, holes, profiles, stock_t, a, sheet_size):
    """One job: the given holes first, then the given part profiles."""
    depth = stock_t + a.through
    g = Gcode(a)
    W, H = sheet_size
    g.emit(f'( Bullitt X cargo box - {title} )')
    g.emit(f'( stock {W:.0f} x {H:.0f} mm, {stock_t:.1f} mm thick; cut depth {depth:.1f} mm )')
    g.emit(f'( tool: {a.tool_d / INCH:.3f} in {a.tool_d:.2f} mm flat end mill, 2 flute )')
    g.emit('( ZERO: X0 Y0 = front-left corner of the stock, Z0 = TOP of the stock )')
    g.emit(f'( spindle {a.rpm} rpm, feed {a.feed:.0f} mm/min, plunge {a.plunge:.0f} mm/min, '
           f'{a.stepdown:.1f} mm per lap )')
    if profiles:
        g.emit('( order: holes first, then part profiles with tabs )')
    g.emit('G21 G90 G17 G94')
    g.emit(f'G0 Z{a.safe_z:.3f}')
    g.emit(f'M3 S{a.rpm}')
    g.emit('G4 P5')
    for x, y, r in holes:
        helical_hole(g, x, y, r, depth)
    tabinfo = []
    for lab, pts in profiles:
        tabs, ring = profile(g, lab, pts, depth)
        tabinfo.append((lab, tabs, ring))
    g.emit(f'G0 Z{a.safe_z:.3f}')
    g.emit('M5')
    g.emit('M30')
    for ln in g.lines:          # grbl ends a comment at the first ')', so no nesting
        assert ln.count('(') == ln.count(')') <= 1, ln
    open(path, 'w').write('\n'.join(g.lines) + '\n')
    return tabinfo


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('vermoot', help="folder with Vermoot's 'front panel.dxf' and 'back panel.dxf'")
    ap.add_argument('--panels', default=os.path.join(REPO, 'panels'),
                    help='folder with Side panel X.dxf and fond X.dxf')
    ap.add_argument('--out', default=os.path.join(REPO, 'cnc'))
    ap.add_argument('--thickness', type=float, default=12.0,
                    help='ply thickness the geometry is adjusted for (mm)')
    ap.add_argument('--gcode-stock', type=float, nargs='+', default=[12.0, 12.7],
                    help='write one set of G-code per stock thickness (mm)')
    ap.add_argument('--through', type=float, default=0.5, help='cut this far past the stock (mm)')
    ap.add_argument('--sheet', type=float, nargs=2, default=[48 * INCH, 48 * INCH])
    ap.add_argument('--stock-b', type=float, nargs=2, default=[720, 470],
                    help='minimum stock for the front/back panels (mm)')
    ap.add_argument('--gap', type=float, default=12.0,
                    help='space between parts; under 2 tool diameters so no loose slivers')
    ap.add_argument('--tool-d', type=float, default=0.25 * INCH)
    ap.add_argument('--rpm', type=int, default=18000)
    ap.add_argument('--feed', type=float, default=1500)
    ap.add_argument('--plunge', type=float, default=400)
    ap.add_argument('--hole-feed', type=float, default=800)
    ap.add_argument('--helix-pitch', type=float, default=1.0)
    ap.add_argument('--stepdown', type=float, default=2.5)
    ap.add_argument('--tab-len', type=float, default=10.0)
    ap.add_argument('--tab-h', type=float, default=3.0)
    ap.add_argument('--tab-spacing', type=float, default=350.0)
    ap.add_argument('--safe-z', type=float, default=15.0)
    ap.add_argument('--clear-z', type=float, default=2.0)
    a = ap.parse_args()

    parts = {}
    for key, folder, fname in [('side', a.panels, 'Side panel X.dxf'), ('floor', a.panels, 'fond X.dxf'),
                               ('front', a.vermoot, 'front panel.dxf'), ('back', a.vermoot, 'back panel.dxf')]:
        pts, holes = read_part(os.path.join(folder, fname))
        parts[key] = {'pts': pts, 'holes': holes}
    adjust_for_thickness(parts, a.thickness)

    os.makedirs(os.path.join(a.out, 'parts'), exist_ok=True)
    os.makedirs(os.path.join(a.out, 'gcode'), exist_ok=True)
    tag = f'{a.thickness:g}mm'
    for key, fname in [('side', 'Side panel X'), ('floor', 'fond X'),
                       ('front', 'front panel'), ('back', 'back panel')]:
        p = parts[key]
        write_dxf(os.path.join(a.out, 'parts', f'{fname} ({tag} ply).dxf'),
                  None, [(key, p['pts'], p['holes'])])

    sheets = layouts(parts, a.gap, tuple(a.sheet), tuple(a.stock_b), 40.0)
    report = {}
    for name, size, items in sheets:
        check_layout(name, size, items, a.gap, a.tool_d, 10.0)
        write_dxf(os.path.join(a.out, f'{name}.dxf'), size, items)
        write_svg(os.path.join(a.out, f'{name}.svg'), size, items)
        holes = [(x, y, r) for _, _, hs in items for x, y, r, tag in sorted(hs) if not tag]
        optional = [(x, y, r) for _, _, hs in items for x, y, r, tag in sorted(hs) if tag]
        profiles = [(lab, pts) for lab, pts, _ in items]
        for st in a.gcode_stock:
            fn = os.path.join(a.out, 'gcode', f'{name}_{st:g}mm-stock.nc')
            report[(name, st)] = write_gcode(fn, name, holes, profiles, st, a, size)
            if optional:
                fn = os.path.join(a.out, 'gcode', f'{name}_front-link-holes-optional_{st:g}mm-stock.nc')
                write_gcode(fn, f'{name}, OPTIONAL front-link holes only', optional, [], st, a, size)
        print(f'{name}: {", ".join(i[0] for i in items)}')
    draw_sheets(os.path.join(REPO, 'preview', 'cnc-sheets.png'), sheets, report, a.gcode_stock[0], a)
    return parts, sheets, report



def draw_sheets(png, sheets, report, stock_t, a):
    """Cut-sheet picture: part names, holes, tab positions and the zero corner."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(16, 9.5), gridspec_kw={'width_ratios': [1219, 720]})
    for ax, (name, (W, H), items) in zip(axes, sheets):
        ax.add_patch(plt.Rectangle((0, 0), W, H, fc='#f3ead8', ec='#777', lw=1))
        tabinfo = report[(name, stock_t)]
        for (lab, pts, holes), (_, tabs, ring) in zip(items, tabinfo):
            fl = flatten(pts)
            ax.fill([p[0] for p in fl], [p[1] for p in fl], fc='#d9b77e', ec='#1f5fbf', lw=1.2)
            for x, y, r, tag in holes:
                ax.add_patch(plt.Circle((x, y), r, fc='white',
                                        ec='#8e44ad' if tag else '#c0392b', lw=1.2))
            for c in tabs:
                p = ring.interpolate(c)
                ax.plot(p.x, p.y, marker='s', ms=6, color='#e67e22')
            poly = Polygon(fl)
            ax.text(poly.centroid.x, poly.centroid.y, lab, ha='center', va='center', fontsize=10,
                    weight='bold', color='#3b2a10')
        ax.plot(0, 0, marker='o', ms=10, color='#27ae60', clip_on=False)
        ax.annotate('X0 Y0 (Z0 = top of stock)', (0, 0), (12, -16), textcoords='offset points',
                    fontsize=9, color='#27ae60', annotation_clip=False)
        ax.set_xlim(-30, W + 30); ax.set_ylim(-70, H + 30)
        ax.set_aspect('equal'); ax.grid(alpha=0.25)
        title = ('Sheet A - 4 x 4 ft half sheet' if name.startswith('sheet-A')
                 else f'Sheet B - any piece at least {W:.0f} x {H:.0f} mm')
        ax.set_title(title, fontsize=12)
    fig.suptitle(f'Bullitt X box on {stock_t:g} mm ply, 1/4" end mill.  Orange squares = tabs, '
                 'purple = optional front-link holes.  Face up on the machine = outside of the box.',
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(png, dpi=100)


if __name__ == '__main__':
    main()
