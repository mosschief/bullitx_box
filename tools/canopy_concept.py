#!/usr/bin/env python3
"""
Concept: a folding rain hood for the Bullitt X box, built the way the box is built,
from flat 12 mm ply parts joined by 3D-printed links.

Each of the three hoops is
  * two ARMS: flat ply strips lying against the outside of the side panels,
    pivoting on a printed hub, the way the struts of a pram hood do
  * one BOW: a flat ply U across the top
  * two printed ELBOWS joining bow to arms at 90 degrees, as Vermoot's links
    join the box panels

The hub is centred on Vermoot's existing back-link bolt (50.7, 303). Hoop 0 is
fixed just ahead of the back panel, behind the kids' heads; hoops 1 and 2 swing
forward. Hood up, the roof runs almost flat over the seat and one windscreen
line falls from hoop 1 to the nose of the box, following the side panel's own
falling rim. A separate apron zips to hoop 2 and press-studs along the outside
of the panels. Folded, the three hoops stand together behind the seat.

Coordinates match the DXFs: x forward from the back of the bay, z up (the side
panel's own y), y across the bike (0 = centre line).

    python3 tools/canopy_concept.py <out folder>

writes canopy-side.png, canopy-front.png and canopy-3d.png.  The parameters here
are shared with canopy_parts.py, which makes the cut files and printed parts.
"""
import os, sys, math, numpy as np, ezdxf
from ezdxf.path import make_path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
PANELS = os.path.join(HERE, '..', 'panels')

# ---------------------------------------------------------------- parameters
PIVOT = (52.7, 303.0)   # Vermoot's back-link bolt, as moved 2 mm forward for 12 mm ply (cnc/parts)
PLY = 12.0              # the box is cut from 1/2" (12 mm) ply; the hood uses the same
PANEL_OUT = 209.0       # outside face of the side panels (floor edge 197 + 12)
HUB_FLANGE = 7.0        # printed hub flange between the panel and the first arm
ARM_PITCH = 14.0        # arms stack on the hub: 12 mm ply + 2 mm printed washer
ARM_W = 36.0            # width of an arm (its boss round the pivot is 44)
# pivot to the centre of each arm's rounded top.  Staggered by 102 so that, folded,
# each elbow sits clear above the elbow and arm of the hoop inside it.
ARM_LENS = [170.0, 272.0, 374.0]
LEG_GAP = 22.0          # bow leg starts this far above its arm's top centre
BOW_W = 36.0            # width of the ply ring in the bows
SHOULDER_R = 150.0      # corner radius of the bows, seen from the front
# where the top of each hoop sits with the hood up (x, z).  The roof runs almost
# flat from 0 to 1, then 1 -> 2 -> the nose is one straight windscreen line.
OPEN_TOPS = [(25.0, 835.0), (330.0, 790.0), (585.0, 600.0)]
FOLDED = [-2.8, 5.5, 12.0]    # hoop angles folded (deg forward of vertical)
NOSE = (976.0, 258.0)        # top front corner of the side panel: the apron lands here
FABRIC_DROP = 25.0           # fabric laps this far down the outside of the panels
FLOOR_Z = 48.0

GREEN, GREEN_D, WINDOW = '#2f5d50', '#244a40', '#bcd9e6'
PLYC, PLYD, HUBC = '#d9b98a', '#7a5a2e', '#33404a'
HOOPC = ['#9a7442', '#ad8550', '#c0975f']


def _geom():
    out = []
    for x, z in OPEN_TOPS:
        dx, dz = x - PIVOT[0], z - PIVOT[1]
        out.append((math.hypot(dx, dz), math.degrees(math.atan2(dx, dz))))
    return out


GEOM = _geom()                    # (pivot-to-top, open angle) per hoop
OPEN = [a for _, a in GEOM]
FOLDED[0] = OPEN[0]               # hoop 0 is fixed: the hub's lugs hold it there


def arm_y(i):
    """Inner and outer face of hoop i's arm, across the bike."""
    inner = PANEL_OUT + HUB_FLANGE + ARM_PITCH * i
    return inner, inner + PLY


def bow_half(i):
    """Outer edge of hoop i's bow: flush with the outside of its arm."""
    return arm_y(i)[1]


def side_profile():
    msp = ezdxf.readfile(os.path.join(PANELS, 'Side panel X.dxf')).modelspace()
    poly = next(e for e in msp if e.dxftype() == 'LWPOLYLINE')
    a = np.array([(p.x, p.y) for p in make_path(poly).flattening(0.2)])
    holes = [(c.dxf.center.x, c.dxf.center.y) for c in msp if c.dxftype() == 'CIRCLE']
    return a, holes


PROF, HOLES = side_profile()
_top = PROF[PROF[:, 1] > 240]
_top = _top[np.argsort(_top[:, 0])]


def rim_z(x):
    """Height of the side panel's top edge at x."""
    return np.interp(x, _top[:, 0], _top[:, 1])


def bow_outline(i, inset=0.0, n=24):
    """Edge of hoop i's bow in its own plane, as (u, h): u across the bike,
    h out from the pivot axis.  Its legs start at the elbow."""
    L = GEOM[i][0]
    a, H, R = bow_half(i) - inset, L - inset, SHOULDER_R - inset
    h0 = ARM_LENS[i] + LEG_GAP
    pts = [(a, h0)]
    pts += [(a - R + R * math.cos(t), H - R + R * math.sin(t)) for t in np.linspace(0, math.pi / 2, n)]
    pts += [(-a + R + R * math.cos(t), H - R + R * math.sin(t)) for t in np.linspace(math.pi / 2, math.pi, n)]
    pts.append((-a, h0))
    return np.array(pts)


def bow_ring(i, n=24):
    o, k = bow_outline(i, n=n), bow_outline(i, BOW_W, n=n)
    return np.vstack([o, k[::-1]])


def arm_outline(i, n=16):
    """Arm in its own plane (along, across): round top; the pivot boss is drawn
    to the arm width here (the cut part has a 44 mm boss)."""
    r = ARM_W / 2
    pts = [(r * math.cos(t), r * math.sin(t)) for t in np.linspace(math.pi / 2, 3 * math.pi / 2, n)]
    pts += [(ARM_LENS[i] + r * math.cos(t), r * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, n)]
    return np.array(pts)


def resample(uh, n):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(uh, axis=0), axis=1))]
    s = np.linspace(0, d[-1], n)
    return np.c_[np.interp(s, d, uh[:, 0]), np.interp(s, d, uh[:, 1])]


def place(uh, theta, dx=0.0):
    """Bow-plane (u, h) -> world (x, y, z), hoop tilted forward by theta; dx shifts
    the plane along its normal."""
    t = math.radians(theta)
    u, h = uh[:, 0], uh[:, 1]
    return np.c_[PIVOT[0] + h * math.sin(t) + dx * math.cos(t), u,
                 PIVOT[1] + h * math.cos(t) - dx * math.sin(t)]


def radial(theta, h):
    t = math.radians(theta)
    return PIVOT[0] + h * math.sin(t), PIVOT[1] + h * math.cos(t)


def arm_side(i, theta):
    """Arm outline in side view (x, z)."""
    t = math.radians(theta)
    a = arm_outline(i)
    along, across = a[:, 0], a[:, 1]
    return np.c_[PIVOT[0] + along * math.sin(t) + across * math.cos(t),
                 PIVOT[1] + along * math.cos(t) - across * math.sin(t)]


# ------------------------------------------------------------ side elevation
def panel(ax):
    ax.fill(PROF[:, 0], PROF[:, 1], color=PLYC, ec=PLYD, lw=1.4, zorder=2)
    for hx, hz in HOLES:
        ax.add_patch(plt.Circle((hx, hz), 4, color=PLYD, zorder=3))


def hub(ax, z=9):
    ax.add_patch(plt.Circle(PIVOT, 30, color=HUBC, zorder=z))
    ax.add_patch(plt.Circle(PIVOT, 11, color='#c9d1d6', zorder=z + 0.1))


def kid(ax):
    # ~4-year-old (sitting height ~580 mm) on a 100 mm cushion, back to the back panel
    seat = FLOOR_Z + 10 + 100
    k = dict(ls=(0, (2, 2)), color='0.2', lw=1.2, zorder=12)
    ax.add_patch(plt.Circle((128, seat + 500), 80, fill=False, **k))
    ax.plot([75, 95, 290, 330], [seat + 415, seat, seat + 50, FLOOR_Z + 12], **k)
    ax.text(128, seat + 500, '4 yr', ha='center', va='center', fontsize=8, color='0.2', zorder=12)


def hoops_side(ax, angles, z0=6):
    for i, a in enumerate(angles):
        ax.fill(*arm_side(i, a).T, color=HOOPC[i], ec='0.25', lw=0.6, zorder=z0 + i * 0.1)
        x0, z_ = radial(a, ARM_LENS[i] + LEG_GAP); x1, z1 = radial(a, GEOM[i][0])
        ax.plot([x0, x1], [z_, z1], color=HOOPC[i], lw=4.5, solid_capstyle='butt', zorder=z0 + i * 0.1)
        ex, ez = radial(a, ARM_LENS[i] + 10)
        ax.add_patch(plt.Circle((ex, ez), 15, color=HUBC, zorder=z0 + 0.5))


def draw_side(out):
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.6))

    ax = axes[0]
    panel(ax)
    hoops_side(ax, OPEN, z0=3.5)
    tops = [radial(a, GEOM[i][0]) for i, a in enumerate(OPEN)]
    xs = np.linspace(NOSE[0] - 10, 0, 160)
    rim = np.c_[xs, rim_z(xs) - FABRIC_DROP]
    sil = np.vstack([[[4, rim_z(10) - FABRIC_DROP]], tops, [[NOSE[0] + 8, NOSE[1] - 2]], rim])
    ax.fill(sil[:, 0], sil[:, 1], color=GREEN, zorder=4, lw=0)
    # seams along the bows, and the roof line
    for i, a in enumerate(OPEN):
        x0, z_ = radial(a, GEOM[i][0])
        hb = (rim_z(x0) - PIVOT[1]) / math.cos(math.radians(a))
        x1, z1 = radial(a, max(hb, ARM_LENS[i] + LEG_GAP))
        ax.plot([x0, x1], [z_, z1], color=GREEN_D, lw=2.2, zorder=4.2)
    ax.plot(*np.array(tops + [NOSE]).T, color=GREEN_D, lw=2.2, zorder=4.2)
    # side window between hoops 1 and 2, windscreen in the apron
    t1, t2, nose = np.array(tops[1]), np.array(tops[2]), np.array(NOSE)
    p1, p2 = np.array(radial(OPEN[1], 300)), np.array(radial(OPEN[2], 330))
    side_win = np.array([t1 + (p1 - t1) * 0.12 + [25, 0], t2 + (p2 - t2) * 0.15 + [-18, 0],
                         t2 + (p2 - t2) * 0.78 + [-12, 0], t1 + (p1 - t1) * 0.78 + [25, 0]])
    ax.fill(side_win[:, 0], side_win[:, 1], color=WINDOW, zorder=4.5, lw=0)
    w0, w1 = t2 + 0.10 * (nose - t2), t2 + 0.80 * (nose - t2)
    screen = np.array([w0 + [8, -16], w1 + [0, -16],
                       [w1[0] - 25, rim_z(w1[0] - 25) + 22], [w0[0] + 25, rim_z(w0[0] + 25) + 22]])
    ax.fill(screen[:, 0], screen[:, 1], color=WINDOW, zorder=4.5, lw=0)
    hub(ax); kid(ax)
    kw = dict(fontsize=9, arrowprops=dict(arrowstyle='-', color='0.35', lw=0.8), zorder=13)
    ax.annotate('fixed hoop', tops[0], xytext=(-95, 900), **kw)
    ax.annotate('hood / apron zip', tops[2], xytext=(650, 740), **kw)
    ax.annotate('arms pivot on a printed hub\non the back-link bolt', PIVOT, xytext=(150, 205), **kw)
    ax.annotate('apron press-studs to\nthe outside of the panel', (820, rim_z(820) - 15),
                xytext=(690, 110), **kw)
    ax.set_title('Hood up, apron on', fontsize=12)

    ax = axes[1]
    panel(ax)
    bund = np.array([radial(FOLDED[0], GEOM[0][0] - 10), radial(FOLDED[2], GEOM[2][0] - 10),
                     radial(FOLDED[2], 190), radial(FOLDED[0], 120)])
    ax.fill(bund[:, 0], bund[:, 1], color=GREEN, zorder=5, lw=0)
    hoops_side(ax, FOLDED, z0=6)
    hub(ax); kid(ax)
    ax.set_title('Hood folded, apron off', fontsize=12)

    for ax in axes:
        ax.set_aspect('equal'); ax.set_xlim(-110, 1060); ax.set_ylim(0, 980)
        ax.grid(alpha=.25); ax.set_xlabel('mm from the back of the cargo bay')
    plt.tight_layout(); plt.savefig(os.path.join(out, 'canopy-side.png'), dpi=110)
    plt.close(fig)


# ----------------------------------------------------------- front elevation
def draw_front(out):
    fig, ax = plt.subplots(figsize=(7.6, 7.6))
    ax.add_patch(plt.Rectangle((-PANEL_OUT, FLOOR_Z), 2 * PANEL_OUT, rim_z(30) - FLOOR_Z,
                               color=PLYC, ec=PLYD, lw=1.4, zorder=1))
    for i in (2, 1, 0):
        th = math.radians(FOLDED[i])
        r = bow_ring(i)
        ax.fill(r[:, 0], PIVOT[1] + r[:, 1] * math.cos(th), color=HOOPC[i], ec='0.2', lw=0.6,
                zorder=3 + 2 - i)
        for s in (-1, 1):
            y0, y1 = arm_y(i)
            ztop = PIVOT[1] + (ARM_LENS[i] + ARM_W / 2) * math.cos(th)
            ax.add_patch(plt.Rectangle((s * y0 if s > 0 else -y1, PIVOT[1] - ARM_W / 2), PLY,
                                       ztop - PIVOT[1] + ARM_W / 2, color=HOOPC[i], ec='0.2',
                                       lw=0.6, zorder=6))
            ez = PIVOT[1] + (ARM_LENS[i] + 10) * math.cos(th)
            ax.add_patch(plt.Rectangle((s * (y1 + 3) if s > 0 else -y1 - 3 - 0, ez - 22),
                                       -s * (BOW_W + 8) if s > 0 else BOW_W + 8, 44,
                                       color=HUBC, alpha=0.9, zorder=7))
    for s in (-1, 1):
        x0 = PANEL_OUT if s > 0 else -PANEL_OUT - 3 * ARM_PITCH - HUB_FLANGE - 5
        ax.add_patch(plt.Rectangle((x0, PIVOT[1] - 30), 3 * ARM_PITCH + HUB_FLANGE + 5, 60, color=HUBC, zorder=8))
    kw = dict(fontsize=9, arrowprops=dict(arrowstyle='-', color='0.35', lw=0.8), zorder=13)
    ax.annotate('printed elbow', (bow_half(2) + 6, PIVOT[1] + ARM_LENS[2]), xytext=(255, 690), **kw)
    ax.annotate('ply arms,\n3 per side', (bow_half(2) - 5, 450), xytext=(255, 430), **kw)
    ax.annotate('printed hub', (PANEL_OUT + 40, PIVOT[1]), xytext=(255, 230), **kw)
    w = 2 * (arm_y(2)[1] + 5)
    ax.annotate('', (-w / 2, 960), (w / 2, 960), arrowprops=dict(arrowstyle='<->', lw=0.8))
    ax.text(0, 970, f'{w:.0f} mm over the hubs (box: {2 * PANEL_OUT:.0f})', ha='center', fontsize=9)
    ax.set_aspect('equal'); ax.set_xlim(-330, 400); ax.set_ylim(0, 1010)
    ax.set_title('Folded, from behind', fontsize=11)
    ax.grid(alpha=.25); ax.set_xlabel('mm across the bike')
    plt.tight_layout(); plt.savefig(os.path.join(out, 'canopy-front.png'), dpi=110)
    plt.close(fig)


# --------------------------------------------------------------------- 3D view
LIGHT = np.array([0.35, -0.55, 0.75]); LIGHT /= np.linalg.norm(LIGHT)


def shade(polys, cols):
    out = []
    for p, c in zip(polys, cols):
        p = np.asarray(p)
        n = np.cross(p[1] - p[0], p[-1] - p[0])
        if np.linalg.norm(n) < 1e-9 and len(p) > 3:
            n = np.cross(p[2] - p[0], p[-1] - p[1])
        n = n / (np.linalg.norm(n) + 1e-12)
        k = 0.58 + 0.42 * abs(float(n @ LIGHT))
        rgb = np.array(matplotlib.colors.to_rgb(c)) * k
        out.append(np.clip(rgb, 0, 1))
    return out


def box_polys():
    polys, cols = [], []
    pr = PROF[::2]
    for y in (-PANEL_OUT, PANEL_OUT - PLY):
        for yy in (y, y + PLY):
            polys.append(np.c_[pr[:, 0], np.full(len(pr), yy), pr[:, 1]]); cols.append(PLYC)
        for a, b in zip(pr[:-1], pr[1:]):          # end grain along the rim
            polys.append(np.array([[a[0], y, a[1]], [b[0], y, b[1]],
                                   [b[0], y + PLY, b[1]], [a[0], y + PLY, a[1]]]))
            cols.append('#b48a55')
    # floor and end panels, approximated (Vermoot's front/back DXFs are not in this repo)
    polys.append(np.array([[20, -197, FLOOR_Z + 10], [960, -197, FLOOR_Z + 10],
                           [960, 197, FLOOR_Z + 10], [20, 197, FLOOR_Z + 10]])); cols.append('#c8a576')
    polys.append(np.array([[17, -197, 50], [17, 197, 50], [15, 197, 350], [15, -197, 350]]))
    cols.append('#cfae80')
    polys.append(np.array([[966, -197, 100], [966, 197, 100], [996, 197, 215], [996, -197, 215]]))
    cols.append('#cfae80')
    return polys, cols


def lap(p):
    """Keep fabric outside the box: near the panels it may not dip below the rim lap."""
    floor = rim_z(np.clip(p[:, 0], 0, 975)) - FABRIC_DROP
    p[:, 2] = np.maximum(p[:, 2], np.where(np.abs(p[:, 1]) > PANEL_OUT - 5, floor, floor + 25))
    return p


def hood_surface(n_u=64, steps=10):
    quads, cols = [], []
    rings = [place(resample(bow_outline(i) + [0, 4], n_u), a, dx=0) for i, a in enumerate(OPEN)]
    for r in rings:                      # bow legs continue down the arms to the rim
        for j in (0, -1):
            r[j, 2] = rim_z(r[j, 0]) - FABRIC_DROP
    nose = rings[-1].copy()
    nose[:, 0] = NOSE[0] + 6
    nose[:, 1] = np.clip(nose[:, 1], -PANEL_OUT - 3, PANEL_OUT + 3)
    nose[:, 2] = NOSE[1] + 2
    for name, a, b in (('roof', rings[0], rings[1]), ('hood', rings[1], rings[2]),
                       ('apron', rings[2], nose)):
        prev = lap(a.copy())
        for k in range(1, steps + 1):
            f = k / steps
            cur = lap(a + (b - a) * f)
            for j in range(n_u - 1):
                u = abs(a[j, 1]) / PANEL_OUT
                win = (name == 'apron' and 0.2 < f <= 0.8 and u < 0.7) or \
                      (name == 'hood' and 0.2 < f <= 0.8 and 0.88 < u and
                       (prev[j, 2] - rim_z(prev[j, 0])) > 50 and
                       (j < 12 or j > n_u - 14))
                quads.append(np.array([prev[j], prev[j + 1], cur[j + 1], cur[j]]))
                cols.append(WINDOW if win else GREEN)
            prev = cur
    # back: clear rear window inside the fixed hoop, so the rider can see in
    back = place(resample(bow_outline(0, BOW_W), 40), OPEN[0], dx=-6)
    back[:, 2] = np.maximum(back[:, 2], rim_z(20))
    c = back.mean(axis=0); c[2] = rim_z(20)
    for j in range(len(back) - 1):
        quads.append(np.array([c, back[j], back[j + 1]])); cols.append('#a9c6d3')
    return quads, cols


def hoop_solids(angles, with_bows=True):
    """Arms, and bows and elbows unless the fabric is covering them."""
    polys, cols = [], []
    for i, th in enumerate(angles):
        t = math.radians(th)
        if with_bows:
            r = resample(bow_outline(i), 70); k = resample(bow_outline(i, BOW_W), 70)
            for dx in (-PLY / 2, PLY / 2):
                po, pi = place(r, th, dx), place(k, th, dx)
                for j in range(69):
                    polys.append(np.array([po[j], po[j + 1], pi[j + 1], pi[j]])); cols.append(HOOPC[i])
            po = place(r, th, -PLY / 2); po2 = place(r, th, PLY / 2)
            for j in range(69):
                polys.append(np.array([po[j], po[j + 1], po2[j + 1], po2[j]])); cols.append(HOOPC[i])
        a = arm_outline(i)
        for s in (-1, 1):
            y0, y1 = arm_y(i)
            for y in (y0, y1):
                xs = PIVOT[0] + a[:, 0] * math.sin(t) + a[:, 1] * math.cos(t)
                zs = PIVOT[1] + a[:, 0] * math.cos(t) - a[:, 1] * math.sin(t)
                polys.append(np.c_[xs, np.full(len(a), s * y), zs]); cols.append(HOOPC[i])
            if not with_bows:
                continue
            ex, ez = radial(th, ARM_LENS[i] + 10)
            cube = [[ex - 22, s * (y1 + 2), ez - 22], [ex + 22, s * (y1 + 2), ez - 22],
                    [ex + 22, s * (y1 + 2), ez + 22], [ex - 22, s * (y1 + 2), ez + 22]]
            polys.append(np.array(cube)); cols.append(HUBC)
    return polys, cols


def hub_polys():
    polys = []
    t = np.linspace(0, 2 * np.pi, 32)
    for s in (-1, 1):
        y = PANEL_OUT + HUB_FLANGE + 3 * ARM_PITCH + 3
        polys.append(np.c_[PIVOT[0] + 30 * np.cos(t), np.full(32, s * y), PIVOT[1] + 30 * np.sin(t)])
    return polys, [HUBC] * len(polys)


def draw_3d(out):
    fig = plt.figure(figsize=(16, 7.6))
    views = (('Hood up, apron on', 'fabric', OPEN), ('Hood folded, apron off', 'hoops', FOLDED))
    for n, (title, mode, angles) in enumerate(views):
        ax = fig.add_subplot(1, 2, n + 1, projection='3d')
        polys, cols = box_polys()
        if mode == 'fabric':
            q, c = hoop_solids(angles, with_bows=False); polys += q; cols += c
            q, c = hood_surface(); polys += q; cols += c
        else:
            q, c = hoop_solids(angles); polys += q; cols += c
        q, c = hub_polys(); polys += q; cols += c
        fc = shade(polys, cols)
        pc = Poly3DCollection(polys, facecolors=fc, linewidths=0.25)
        ax.add_collection3d(pc, autolim=False)
        pc.set_edgecolor(fc)
        ax.set_xlim(-60, 1040); ax.set_ylim(-550, 550); ax.set_zlim(-120, 980)
        ax.set_box_aspect((1100, 1100, 1100))
        ax.view_init(elev=17, azim=-58)
        ax.set_axis_off(); ax.set_title(title, fontsize=13)
    plt.subplots_adjust(left=0, right=1, top=0.95, bottom=0, wspace=0)
    plt.savefig(os.path.join(out, 'canopy-3d.png'), dpi=110)
    plt.close(fig)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0] if args else 'preview'
    os.makedirs(out, exist_ok=True)
    draw_side(out); draw_front(out); draw_3d(out)

    for i, (L, a) in enumerate(GEOM):
        print(f'hoop {i}: bow {2 * bow_half(i):.0f} wide, top {L:.0f} from pivot, '
              f'opens to {a:.1f} deg, folds to {FOLDED[i]:.1f}')
    print('wrote', out)
