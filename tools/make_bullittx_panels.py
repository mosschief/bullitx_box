#!/usr/bin/env python3
"""
Stretch the Vermoots Bullitt box panels to fit a Bullitt X.

The Bullitt X cargo bay is 220 mm longer than the Original Bullitt and the extra
length is all at the front: with the rear of the bay used as datum, the Bullitt X's
first three floor transverses land on the Original's three, and a fourth sits
220 mm further forward.  So the panels are not scaled -- they are cut in the
straight middle section and the front half is slid forward by 220 mm.  Every
profile, radius and bolt position at either end is left exactly as Vermoot drew it.

Usage:
    python3 make_bullittx_panels.py <folder with the Vermoots DXFs> <output folder>

--extension changes the 220 mm if you measure something different on your own bike.
"""
import argparse, math, os, ezdxf

# Relief cut in the floor edge at a bottom-link station, as offsets from the socket
# centre: (dx, y, bulge).  Taken verbatim from Vermoot's fond.dxf.  It clears both the
# frame's 18 mm accessory socket and the inboard part of the link that plugs into it.
RELIEF = [(+26.3186, 197.0, 0.41421356), (+16.0, 186.68144154, -1.0),
          (-16.0, 186.68144154, 0.41421356), (-26.3185, 197.0, 0.0)]


def arc_radius(p0, p1, bulge):
    return math.dist(p0, p1) / (2 * math.sin(abs(4 * math.atan(bulge)) / 2))


def side_panel(src, out, ext, cut, extra_link_x):
    doc = ezdxf.readfile(os.path.join(src, 'Side panel.dxf'))
    msp = doc.modelspace()
    poly = next(e for e in msp if e.dxftype() == 'LWPOLYLINE')
    pts = [list(p) for p in poly.get_points('xyb')]

    # v3 -> v4 is the long, shallow arc along the top rim.  Holding its bulge scales
    # the curve with the chord, so the rim keeps its height and its clean fall to the
    # front; holding the radius instead would crown it ~9 mm over the back panel.
    p4, b3 = (pts[4][0], pts[4][1]), pts[3][2]
    r_old = arc_radius((pts[3][0], pts[3][1]), p4, b3)

    for v in pts:
        if v[0] > cut:
            v[0] += ext
    poly.set_points([tuple(v) for v in pts], format='xyb')
    poly.closed = True
    r_new = arc_radius((pts[3][0], pts[3][1]), p4, pts[3][2])

    for c in [e for e in msp if e.dxftype() == 'CIRCLE']:
        if c.dxf.center.x > cut:                       # front-link bolt follows the front
            c.dxf.center = (c.dxf.center.x + ext, c.dxf.center.y, c.dxf.center.z)
    if extra_link_x:
        msp.add_circle((extra_link_x, 59.0), 4.0)      # extra bottom-link bolt
    doc.saveas(os.path.join(out, 'Side panel X.dxf'))
    print(f'  side panel: top rim arc {r_old:.0f} -> {r_new:.0f} mm radius')


def floor(src, out, ext, cut, extra_link_x):
    doc = ezdxf.readfile(os.path.join(src, 'fond.dxf'))
    msp = doc.modelspace()
    poly = next(e for e in msp if e.dxftype() == 'LWPOLYLINE')
    pts = [list(p) for p in poly.get_points('xyb')]
    for v in pts:
        if v[0] > cut:
            v[0] += ext

    out_pts = []
    for i, v in enumerate(pts):
        out_pts.append(tuple(v))
        if extra_link_x and i == 3:      # +Y edge, running with X descending
            out_pts += [(extra_link_x + dx, y, b) for dx, y, b in RELIEF]
        if extra_link_x and i == 28:     # -Y edge, running with X ascending
            out_pts += [(extra_link_x - 26.3185, -197.0, 0.41421356),
                        (extra_link_x - 16.0, -186.68144154, -1.0),
                        (extra_link_x + 16.0, -186.68144154, 0.41421356),
                        (extra_link_x + 26.3186, -197.0, 0.0)]
    poly.set_points(out_pts, format='xyb')
    poly.closed = True

    for y in (-150.0, 0.0, 150.0):       # bolt row for the fourth transverse
        msp.add_circle((710.0 + ext, y), 5.0)
    doc.saveas(os.path.join(out, 'fond X.dxf'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--extension', type=float, default=220.0)
    ap.add_argument('--cut', type=float, default=600.0,
                    help='x to split at; must land in the straight middle of both panels')
    ap.add_argument('--extra-link-x', type=float, default=0.0,
                    help='extra bottom-link station, if your frame has a third socket '
                         'pair; adds the panel bolt and the matching floor relief')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    print(f'stretching by {a.extension} mm at x > {a.cut}')
    side_panel(a.src, a.out, a.extension, a.cut, a.extra_link_x)
    floor(a.src, a.out, a.extension, a.cut, a.extra_link_x)
    print('wrote', a.out)
