#!/usr/bin/env python3
"""
Build the rain-hood parts for the Bullitt X box, from the parameters in
canopy_concept.py.

Printed (STL + STEP), per bike:
  hub-right, hub-left   1 each   flange on the side panel, sleeve the arms turn on,
                                 lugs that lock hoop 0 (the fixed hoop)
  hub-cap               2        bears on the sleeve end and the outer arm
  hub-washer            4        2 mm spacers between the arms
  knob                  2        star knob with a captive M6 nut: sets the fold friction
  elbow                 6        joins each arm to its bow (all six are the same part)

Cut from 12 mm ply (canopy-ply.dxf, true arcs):
  bow 0, bow 1, bow 2   1 each
  arm 0, arm 1, arm 2   2 each   (cut as drawn; the pair is not handed)

The script also assembles everything hood-up and folded, checks every pair of
parts for collisions, and renders the assembly.

    python3 tools/canopy_parts.py <out folder>

Needs cadquery (pip install cadquery ezdxf matplotlib).
"""
import os, sys, math, itertools, numpy as np, ezdxf
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canopy_concept as C

# ------------------------------------------------------------- fits & hardware
PLY_SLOT = 13.0          # slot for 1/2" ply, which is 11.9-12.7 mm: the elbow bolts pull it tight
SLEEVE_D = 24.0          # hub sleeve the arms turn on
ARM_HOLE = 24.5          # pivot hole in the arms (a 25 mm Forstner bit is fine by hand)
BOSS_R = 22.0            # round boss on the arm around the pivot
M5, M6, M8 = 5.5, 6.5, 8.5
M5_NUT_AF, M6_NUT_AF = 8.0, 10.0
# the pivot is Vermoot's back-link hole: 8 mm, so M6 (as in cnc/README.md), not M8
FIT = 0.3                # clearance on printed hex pockets
CLAMP = 0.6              # sleeve is this much shorter than the arm stack, so the knob clamps it
WASHER_T = C.ARM_PITCH - C.PLY

# elbow, in its own frame: x fore-aft, y across (0 = outer face of the arm, + outboard),
# z along the arm (0 = centre of the arm's round top)
EL_BELOW = 40.0          # how far the elbow runs down the arm
EL_SOCKET = 38.0         # depth of the bow-leg socket
EL_CHEEK = 7.0           # inboard cheek the arm bolts to
EL_WALL = 6.0            # socket walls either side of the bow leg
EL_LIP = 3.7             # lips wrapping the arm's edges
ARM_BOLTS = (-10.0, -29.0)
LEG_BOLTS = (11.0, 28.0)  # above the bottom of the bow leg


def hexagon(af):
    return (af + FIT) / math.cos(math.radians(30))


def xform(shape, rows):
    """Apply a 3x4 affine transform (rows) to a shape."""
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    t = gp_Trsf()
    t.SetValues(*rows[0], *rows[1], *rows[2])
    return cq.Shape.cast(BRepBuilderAPI_Transform(shape.wrapped, t, True).Shape())


# ------------------------------------------------------------------ printed
def hub():
    """Print frame: flange on z = 0 (against the panel), sleeve up (+z = outboard),
    +x = forward.  The anti-rotation lobe points forward, so left and right are
    mirror images."""
    t = C.HUB_FLANGE
    r1, r2, d = 32.0, 14.0, 45.0
    a = math.acos((r1 - r2) / d)
    p1 = (r1 * math.cos(a), r1 * math.sin(a)); p2 = (d + r2 * math.cos(a), r2 * math.sin(a))
    flange = (cq.Workplane('XY').moveTo(*p1).lineTo(*p2)
              .threePointArc((d + r2, 0), (p2[0], -p2[1])).lineTo(p1[0], -p1[1])
              .threePointArc((-r1, 0), p1).close().extrude(t))
    flange = flange.edges('>Z').fillet(2.0)
    stack = 3 * C.PLY + 2 * WASHER_T
    sleeve = cq.Workplane('XY').workplane(offset=t).circle(SLEEVE_D / 2).extrude(stack - CLAMP)
    body = flange.union(sleeve)
    body = body.faces('>Z').edges().chamfer(0.6)
    # two lugs either side of the innermost arm lock hoop 0 at its angle: it is the fixed hoop
    th = math.radians(C.OPEN[0])
    for f in (-1, 1):
        h, ff = 28.0, f * (C.ARM_W / 2 + 0.3 + 3.5)
        cx = h * math.sin(th) + ff * math.cos(th)
        cy = -h * math.cos(th) + ff * math.sin(th)
        lug = (cq.Workplane('XY').box(7.0, 12.0, t + C.PLY, centered=(True, True, False))
               .edges('|Z').fillet(1.0)
               .rotate((0, 0, 0), (0, 0, 1), C.OPEN[0]).translate((cx, cy, 0)))
        body = body.union(lug)
    # M6 through; captive M6 jam nut (3.2 mm) at flange level, loaded from the sleeve end
    bore = cq.Workplane('XY').circle(M6 / 2).extrude(80)
    nut = cq.Workplane('XY').workplane(offset=t - 3.4).polygon(6, hexagon(M6_NUT_AF)).extrude(3.4)
    well = cq.Workplane('XY').workplane(offset=t).circle(hexagon(M6_NUT_AF) / 2 + 0.25).extrude(80)
    anti = (cq.Workplane('XY').center(d, 0).circle(M6 / 2).extrude(t)
            .union(cq.Workplane('XY').workplane(offset=t - 3.2).center(d, 0).circle(5.8).extrude(3.2)))
    return body.cut(bore).cut(nut).cut(well).cut(anti)


def hub_cap():
    spigot_d = hexagon(M6_NUT_AF) + 0.5 - 0.4
    cap = cq.Workplane('XY').circle(20).extrude(5).edges('>Z').fillet(1.5)
    cap = cap.union(cq.Workplane('XY').workplane(offset=-3).circle(spigot_d / 2).extrude(3))
    return cap.cut(cq.Workplane('XY').workplane(offset=-3).circle(M6 / 2).extrude(10))


def washer():
    return (cq.Workplane('XY').circle(20).circle(ARM_HOLE / 2 + 0.1).extrude(WASHER_T))


def knob():
    sk = cq.Sketch().circle(15)
    sk = sk.push([(18 * math.cos(math.radians(60 * i)), 18 * math.sin(math.radians(60 * i)))
                  for i in range(6)]).circle(6.5).reset()
    sk = sk.push([(24 * math.cos(math.radians(60 * i + 30)), 24 * math.sin(math.radians(60 * i + 30)))
                  for i in range(6)]).circle(6.5, mode='s').reset()
    k = cq.Workplane('XY').placeSketch(sk).extrude(14)
    try:
        k = k.faces('>Z').edges().chamfer(1.2)
    except Exception:
        pass
    k = k.cut(cq.Workplane('XY').circle(M6 / 2).extrude(14))
    return k.cut(cq.Workplane('XY').workplane(offset=14 - 5.2).polygon(6, hexagon(M6_NUT_AF)).extrude(5.2))


def elbow():
    """Frame: x fore-aft, y across (0 = outer face of the arm, + outboard),
    z along the arm (0 = centre of the arm's round top).  Prints lying on its
    flat outer face (y = 0)."""
    hw = C.ARM_W / 2 + 0.3                  # arm slot half-width
    ox = hw + EL_LIP                        # lower block half-width
    leg_w = C.BOW_W
    z_leg = C.LEG_GAP                       # bottom of the bow leg
    lower = cq.Workplane('XY').box(2 * ox, C.PLY + EL_CHEEK, EL_BELOW + z_leg,
                                   centered=(True, False, False)).translate((0, -(C.PLY + EL_CHEEK), -EL_BELOW))
    sx = PLY_SLOT / 2 + EL_WALL
    upper = cq.Workplane('XY').box(2 * sx, leg_w + 5, EL_SOCKET + 4,
                                   centered=(True, False, False)).translate((0, -(leg_w + 5), z_leg - 4))
    body = lower.union(upper)
    try:
        body = body.edges('|Z').fillet(1.5)
    except Exception:
        pass
    arm = cq.Workplane('XY').box(2 * hw, PLY_SLOT, EL_BELOW + C.ARM_W / 2 + 0.5,
                                 centered=(True, False, False)).translate((0, -PLY_SLOT + 0.2, -EL_BELOW - 0.1))
    leg = cq.Workplane('XY').box(PLY_SLOT, leg_w + 0.4, EL_SOCKET + 0.1,
                                 centered=(True, False, False)).translate((0, -leg_w - 0.4 + 0.2, z_leg))
    body = body.cut(arm).cut(leg)
    # arm bolts: M5 countersunk from the outboard face of the arm, nyloc in the cheek
    yi = -(C.PLY + EL_CHEEK)
    for z in ARM_BOLTS:
        body = body.cut(cq.Workplane('XZ', origin=(0, 5, z)).circle(M5 / 2).extrude(40))
        body = body.cut(cq.Workplane('XZ', origin=(0, yi + 5.2, z)).polygon(6, hexagon(M5_NUT_AF)).extrude(5.2 + 1))
    # leg bolts: M5 fore-aft, cap head one side, nyloc the other
    yc = -leg_w / 2
    for dz in LEG_BOLTS:
        z = z_leg + dz
        body = body.cut(cq.Workplane('YZ', origin=(-sx - 1, yc, z)).circle(M5 / 2).extrude(2 * sx + 2))
        body = body.cut(cq.Workplane('YZ', origin=(sx - 3.5, yc, z)).circle(4.6).extrude(5))
        body = body.cut(cq.Workplane('YZ', origin=(-sx - 1, yc, z)).polygon(6, hexagon(M5_NUT_AF)).extrude(4.5))
    return body


# --------------------------------------------------------------- ply, 2D
BULGE_90 = math.tan(math.radians(90) / 4)


def bow_polyline(i):
    """(u, h, bulge) outline of bow i: legs at u = +/-a, from h0 up to the top."""
    a = C.bow_half(i); H = C.GEOM[i][0]; R = C.SHOULDER_R; w = C.BOW_W
    h0 = C.ARM_LENS[i] + C.LEG_GAP
    return [(a, h0, 0), (a, H - R, BULGE_90), (a - R, H, 0), (-a + R, H, BULGE_90),
            (-a, H - R, 0), (-a, h0, 0), (-a + w, h0, 0), (-a + w, H - R, -BULGE_90),
            (-a + R, H - w, 0), (a - R, H - w, -BULGE_90), (a - w, H - R, 0), (a - w, h0, 0)]


def bow_holes(i):
    a = C.bow_half(i); h0 = C.ARM_LENS[i] + C.LEG_GAP
    return [(s * (a - C.BOW_W / 2), h0 + dz) for s in (-1, 1) for dz in LEG_BOLTS]


def arm_polyline(i):
    """(f, h, bulge) outline of arm i: 44 mm boss at the pivot, 36 wide, round top."""
    L, r = C.ARM_LENS[i], C.ARM_W / 2
    hj = math.sqrt(BOSS_R ** 2 - r ** 2)
    sweep = 360 - 2 * math.degrees(math.atan2(hj, r))       # boss arc, round the bottom
    return [(r, hj, 0), (r, L, 1.0), (-r, L, 0), (-r, hj, math.tan(math.radians(sweep) / 4))]


def arm_holes(i):
    L = C.ARM_LENS[i]
    return [(0, 0, ARM_HOLE / 2)] + [(0, L + z, M5 / 2) for z in ARM_BOLTS]


def wire_from(poly):
    """Polyline with bulges -> cadquery workplane wire."""
    wp = cq.Workplane('XY').moveTo(poly[0][0], poly[0][1])
    n = len(poly)
    for k in range(n):
        x0, y0, b = poly[k]; x1, y1, _ = poly[(k + 1) % n]
        if abs(b) < 1e-9:
            if k < n - 1:
                wp = wp.lineTo(x1, y1)
        else:
            th = 4 * math.atan(b); cx_, cy_ = (x0 + x1) / 2, (y0 + y1) / 2
            dx, dy = x1 - x0, y1 - y0; chord = math.hypot(dx, dy)
            sag = b * chord / 2               # b > 0: CCW arc, so it bulges to the right of travel
            mx, my = cx_ + dy / chord * sag, cy_ - dx / chord * sag
            wp = wp.threePointArc((mx, my), (x1, y1))
    return wp.close()


def ply_solid(poly, holes):
    s = wire_from(poly).extrude(C.PLY)
    for x, y, r in holes:
        s = s.cut(cq.Workplane('XY').center(x, y).circle(r).extrude(C.PLY))
    return s


def bow_solid(i):
    return ply_solid(bow_polyline(i), [(u, h, M5 / 2) for u, h in bow_holes(i)])


def arm_solid(i):
    return ply_solid(arm_polyline(i), arm_holes(i))


# --------------------------------------------------------------- assembly
def to_hoop(shape, theta):
    """Hoop frame (x fore-aft, y across, z out from the pivot) -> world."""
    s = shape.rotate((0, 0, 0), (0, 1, 0), theta)
    return s.translate((C.PIVOT[0], 0, C.PIVOT[1]))


def assembly(angles):
    parts = {}
    hub_w = xform(hub().val(), [[1, 0, 0, C.PIVOT[0]], [0, 0, 1, C.PANEL_OUT], [0, -1, 0, C.PIVOT[1]]])
    parts['hub R'] = hub_w
    parts['hub L'] = hub_w.mirror('XZ')
    el = elbow().val()
    for i, th in enumerate(angles):
        a0, a1 = C.arm_y(i)
        # arm: 2D (f, h) extruded 10 -> x = -f, y = a0 + z, z = h
        arm = xform(arm_solid(i).val(), [[-1, 0, 0, 0], [0, 0, 1, a0], [0, 1, 0, 0]])
        arm = to_hoop(arm, th)
        parts[f'arm {i} R'] = arm; parts[f'arm {i} L'] = arm.mirror('XZ')
        # bow: 2D (u, h) extruded 10 -> x = z - 5, y = u, z = h
        bow = xform(bow_solid(i).val(), [[0, 0, 1, -C.PLY / 2], [1, 0, 0, 0], [0, 1, 0, 0]])
        parts[f'bow {i}'] = to_hoop(bow, th)
        e = to_hoop(el.translate((0, a1, C.ARM_LENS[i])), th)
        parts[f'elbow {i} R'] = e; parts[f'elbow {i} L'] = e.mirror('XZ')
    return parts


def panel_solid():
    pts = [tuple(p) for p in C.PROF[::3]]
    w = cq.Workplane('XY').polyline(pts).close().extrude(C.PLY)
    s = xform(w.val(), [[1, 0, 0, 0], [0, 0, -1, C.PANEL_OUT], [0, 1, 0, 0]])   # y 197..209
    return s


def hoop_of(name):
    for t in name.split():
        if t.isdigit():
            return int(t)
    return None


def clashes(parts, panel):
    out = []
    names = list(parts)
    allp = dict(parts); allp['panel R'] = panel; allp['panel L'] = panel.mirror('XZ')
    for a, b in itertools.combinations(allp, 2):
        ha, hb = hoop_of(a), hoop_of(b)
        if ha is not None and ha == hb:
            continue                      # an arm, its elbow and its bow are meant to touch
        A, B = allp[a], allp[b]
        ba, bb = A.BoundingBox(), B.BoundingBox()
        if (ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin
                or ba.zmax < bb.zmin or bb.zmax < ba.zmin):
            continue
        try:
            v = A.intersect(B).Volume()
        except Exception:
            continue
        if v > 1.0:
            out.append((a, b, v))
    return out


# --------------------------------------------------------------- outputs
def write_dxf(out):
    doc = ezdxf.new('R2010'); msp = doc.modelspace()
    doc.layers.add('CUT', color=1); doc.layers.add('HOLES', color=5); doc.layers.add('LABEL', color=8)
    x0 = 0.0
    for i in range(3):
        a = C.bow_half(i); h0 = C.ARM_LENS[i] + C.LEG_GAP
        poly = [(x0 + a + u, h - h0, b) for u, h, b in bow_polyline(i)]
        msp.add_lwpolyline(poly, format='xyb', close=True, dxfattribs={'layer': 'CUT'})
        for u, h in bow_holes(i):
            msp.add_circle((x0 + a + u, h - h0), M5 / 2, dxfattribs={'layer': 'HOLES'})
        msp.add_text(f'BOW {i}  x1', height=10, dxfattribs={'layer': 'LABEL'}).set_placement((x0 + a - 30, 20))
        x0 += 2 * a + 20
    y0 = -40.0
    for i in range(3):
        for k in range(2):
            L = C.ARM_LENS[i]
            # (f, h) -> (h, -f) is a rotation, so the bulge signs still hold
            msp.add_lwpolyline([(h + BOSS_R, y0 - f, b) for f, h, b in arm_polyline(i)],
                               format='xyb', close=True, dxfattribs={'layer': 'CUT'})
            for f, h, r in arm_holes(i):
                msp.add_circle((h + BOSS_R, y0 - f), r, dxfattribs={'layer': 'HOLES'})
            msp.add_text(f'ARM {i}', height=8, dxfattribs={'layer': 'LABEL'}).set_placement((L / 2, y0 - 4))
            y0 -= 2 * BOSS_R + 8
    doc.saveas(os.path.join(out, 'canopy-ply.dxf'))


def tess(shape, tol=0.4):
    v, f = shape.tessellate(tol, 0.3)
    v = np.array([(p.x, p.y, p.z) for p in v])
    return [v[list(t)] for t in f]


def render(parts_open, parts_folded, panel, out):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    col = {'hub': C.HUBC, 'elbow': C.HUBC, 'arm': '#c0975f', 'bow': '#ad8550'}
    fig = plt.figure(figsize=(16, 8))
    for n, (parts, title) in enumerate(((parts_open, 'Hood up (fabric hidden)'),
                                        (parts_folded, 'Folded'))):
        ax = fig.add_subplot(1, 2, n + 1, projection='3d')
        polys, cols = [], []
        for name, s in list(parts.items()) + [('panel', panel), ('panel', panel.mirror('XZ'))]:
            tris = tess(s, 0.6 if name == 'panel' else 0.3)
            polys += tris; cols += [col.get(name.split()[0], C.PLYC)] * len(tris)
        fc = C.shade(polys, cols)
        pc = Poly3DCollection(polys, facecolors=fc, linewidths=0)
        ax.add_collection3d(pc, autolim=False)
        ax.set_xlim(-80, 820); ax.set_ylim(-450, 450); ax.set_zlim(150, 1050)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=18, azim=-62)
        ax.set_axis_off(); ax.set_title(title, fontsize=13)
    plt.subplots_adjust(left=0, right=1, top=0.95, bottom=0, wspace=0)
    plt.savefig(os.path.join(out, 'canopy-assembly.png'), dpi=110); plt.close(fig)



def render_printed(printed, out):
    """One view per printed part, as it comes off the printer."""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    order = [('hub-right', 'hub (x1, + mirrored x1)'), ('elbow', 'elbow (x6)'),
             ('knob', 'knob (x2)'), ('hub-cap', 'cap (x2)'), ('hub-washer', 'washer (x4)')]
    fig = plt.figure(figsize=(17, 4.2))
    for n, (k, title) in enumerate(order):
        ax = fig.add_subplot(1, len(order), n + 1, projection='3d')
        tris = tess(printed[k].val(), 0.08)
        ax.add_collection3d(Poly3DCollection(tris, facecolors=C.shade(tris, ['#4a5a66'] * len(tris)),
                                             linewidths=0), autolim=False)
        bb = printed[k].val().BoundingBox(); c = bb.center; r = max(bb.xlen, bb.ylen, bb.zlen) / 2
        ax.set_xlim(c.x - r, c.x + r); ax.set_ylim(c.y - r, c.y + r); ax.set_zlim(c.z - r, c.z + r)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(28, -50 if k != 'elbow' else 35)
        ax.set_axis_off()
        ax.set_title(f'{title}\n{bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm', fontsize=10)
    plt.subplots_adjust(left=0, right=1, top=0.86, bottom=0, wspace=0)
    plt.savefig(os.path.join(out, 'canopy-printed.png'), dpi=110); plt.close(fig)


def render_dxf(out):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from ezdxf.path import make_path
    msp = ezdxf.readfile(os.path.join(out, 'canopy-ply.dxf')).modelspace()
    fig, ax = plt.subplots(figsize=(15, 6.5))
    for e in msp:
        if e.dxftype() == 'LWPOLYLINE':
            a = np.array([(p.x, p.y) for p in make_path(e).flattening(0.1)])
            ax.fill(a[:, 0], a[:, 1], color=C.PLYC, ec=C.PLYD, lw=1)
        elif e.dxftype() == 'CIRCLE':
            ax.add_patch(__import__('matplotlib.pyplot').pyplot.Circle(
                (e.dxf.center.x, e.dxf.center.y), e.dxf.radius, color='w', ec=C.PLYD, lw=0.8))
        elif e.dxftype() == 'TEXT':
            ax.text(e.dxf.insert.x, e.dxf.insert.y, e.dxf.text, fontsize=8, color='0.3')
    ax.set_aspect('equal'); ax.grid(alpha=.25); ax.set_xlabel('mm')
    ax.set_title('canopy-ply.dxf: 12 mm ply, three bows and six arms')
    plt.tight_layout(); plt.savefig(os.path.join(out, 'canopy-ply.png'), dpi=100); plt.close(fig)


def main(out):
    os.makedirs(out, exist_ok=True)
    stl = os.path.join(out, 'print'); os.makedirs(stl, exist_ok=True)
    printed = {'hub-right': hub(), 'hub-cap': hub_cap(), 'hub-washer': washer(),
               'knob': knob(), 'elbow': elbow()}
    printed['hub-left'] = printed['hub-right'].mirror('YZ')
    for name, wp in printed.items():
        cq.exporters.export(wp, os.path.join(stl, f'{name}.stl'), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(wp, os.path.join(stl, f'{name}.step'))
        bb = wp.val().BoundingBox()
        print(f'  {name:11s} {bb.xlen:5.1f} x {bb.ylen:5.1f} x {bb.zlen:5.1f} mm  {wp.val().Volume() / 1000:5.1f} cm3')
    write_dxf(out)

    panel = panel_solid()
    status = 0
    states = {}
    for label, angles in (('open', C.OPEN), ('folded', C.FOLDED)):
        parts = assembly(angles); states[label] = parts
        bad = clashes(parts, panel)
        print(f'{label}: ' + ('no collisions' if not bad else
                             '; '.join(f'{a} x {b}: {v:.0f} mm3' for a, b, v in bad)))
        status |= bool(bad)
    render(states['open'], states['folded'], panel, out)
    render_printed(printed, out)
    render_dxf(out)
    print('wrote', out)
    return status


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'canopy'))
