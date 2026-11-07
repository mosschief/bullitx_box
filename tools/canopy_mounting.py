#!/usr/bin/env python3
"""
Where the rain hood meets the box: what goes on the side panel, and a section
through the pivot.

    python3 tools/canopy_mounting.py canopy/canopy-mounting.png
"""
import os, sys, math, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canopy_concept as C

ANTI = (C.PIVOT[0] + 45.0, C.PIVOT[1])     # anti-rotation bolt, 45 mm ahead of the pivot
STUD_BELOW_RIM = 15.0
STUD_FROM, STUD_TO, STUD_PITCH = 235.0, 950.0, 102.0   # forward of arm 2 when the hood is up


def studs():
    xs = np.arange(STUD_FROM, STUD_TO + 1, STUD_PITCH)
    return [(x, float(C.rim_z(x)) - STUD_BELOW_RIM) for x in xs]


def hub_outline():
    r1, r2, d = 32.0, 14.0, 45.0
    a = math.acos((r1 - r2) / d)
    t1 = np.linspace(a, 2 * math.pi - a, 60); t2 = np.linspace(-a, a, 30)
    pts = np.r_[np.c_[r1 * np.cos(t1), r1 * np.sin(t1)], np.c_[d + r2 * np.cos(t2), r2 * np.sin(t2)]]
    return pts + C.PIVOT


def side(ax):
    ax.fill(C.PROF[:, 0], C.PROF[:, 1], color=C.PLYC, ec=C.PLYD, lw=1.4, zorder=1)
    for hx, hz in C.HOLES:
        ax.add_patch(Circle((hx, hz), 4, color=C.PLYD, zorder=2))
    # arms, hood up and folded, as ghosts
    for angles, ls in ((C.OPEN, '-'), (C.FOLDED, ':')):
        for i, a in enumerate(angles):
            x1, z1 = C.radial(a, C.ARM_LENS[i] + C.ARM_W / 2)
            ax.plot([C.PIVOT[0], x1], [C.PIVOT[1], z1], ls=ls, color=C.HOOPC[i], lw=3, alpha=.7, zorder=3)
    ax.fill(*hub_outline().T, color=C.HUBC, alpha=.85, zorder=4)
    ax.add_patch(Circle(C.PIVOT, 4.25, color='#ffd34d', ec='k', lw=0.8, zorder=5))
    ax.add_patch(Circle(ANTI, 3.25, color='#e8553e', ec='k', lw=0.8, zorder=5))
    for x, z in studs():
        ax.add_patch(Circle((x, z), 5, color='#2f5d50', zorder=5))
    xs = np.linspace(20, 975, 200)
    ax.plot(xs, C.rim_z(xs) - C.FABRIC_DROP, ls='--', color='#2f5d50', lw=1, zorder=2)
    kw = dict(fontsize=9, arrowprops=dict(arrowstyle='-', color='0.3', lw=0.8), zorder=10)
    ax.annotate(f'existing back-link hole ({C.PIVOT[0]:.1f}, {C.PIVOT[1]:.0f}), 8 mm\nbecomes the hood pivot: longer M6',
                C.PIVOT, xytext=(120, 150), **kw)
    ax.annotate(f'NEW 6.5 mm hole ({ANTI[0]:.1f}, {ANTI[1]:.0f})\nstops the hub turning', ANTI,
                xytext=(250, 225), **kw)
    s = studs()
    ax.annotate(f'apron press studs, {len(s)} per side,\n{STUD_BELOW_RIM:.0f} mm below the rim, '
                f'x = {s[0][0]:.0f} to {s[-1][0]:.0f}', s[3], xytext=(420, 170), **kw)
    ax.annotate('fabric lap line', (700, float(C.rim_z(700)) - C.FABRIC_DROP), xytext=(640, 410), **kw)
    ax.text(70, 455, 'arms: solid = hood up,\ndotted = folded', fontsize=8, color='0.3')
    ax.set_aspect('equal'); ax.set_xlim(-30, 1020); ax.set_ylim(30, 520)
    ax.grid(alpha=.25); ax.set_xlabel('mm from the back of the cargo bay (side panel DXF coordinates)')
    ax.set_title('Outside face of each side panel: everything the hood touches', fontsize=11)


def section(ax):
    """Cut across the bike through the pivot, looking forward; right side shown."""
    z0 = C.PIVOT[1]
    y_pan = C.PANEL_OUT - C.PLY
    f = C.PANEL_OUT
    def box(y0, y1, z_lo, z_hi, c, **k):
        ax.add_patch(Rectangle((y0, z_lo), y1 - y0, z_hi - z_lo, color=c, **k))
    # inside: Vermoot's back link (schematic: shape not in this repo)
    box(y_pan - 4.5, y_pan, z0 - 26, z0 + 26, '#9aa3ab', alpha=.6, ls='--', ec='0.3', zorder=1)
    ax.annotate("Vermoot's back link,\n4.5 mm flange\n(outline schematic)", (y_pan - 2, z0 + 20),
                xytext=(130, z0 + 120), fontsize=8, arrowprops=dict(arrowstyle='-', color='0.3', lw=0.8))
    box(y_pan, f, z0 - 90, z0 + 70, C.PLYC, ec=C.PLYD, zorder=1)
    ax.text(y_pan + 5, z0 - 104, 'side\npanel', ha='center', fontsize=8)
    # hub flange (with captive jam nut) and sleeve
    box(f, f + C.HUB_FLANGE, z0 - 32, z0 + 32, C.HUBC, zorder=2)
    box(f + C.HUB_FLANGE, f + C.HUB_FLANGE + 3 * C.PLY + 2 * (C.ARM_PITCH - C.PLY) - 0.6, z0 - 12, z0 + 12, C.HUBC, zorder=2)
    box(f + C.HUB_FLANGE - 4.2, f + C.HUB_FLANGE, z0 - 7.5, z0 + 7.5, '#c9d1d6', zorder=4)
    # arms (folded: running up) and washers
    for i in range(3):
        a0, a1 = C.arm_y(i)
        box(a0, a1, z0 - 22, z0 + 150, C.HOOPC[i], ec='0.25', lw=.6, zorder=3)
        box(a0, a1, z0 - 12.25, z0 + 12.25, 'w', zorder=3.5)
        ax.text((a0 + a1) / 2, z0 + 156, str(i), ha='center', fontsize=8, va='bottom')
        if i < 2:
            box(a1, a1 + 2, z0 - 20, z0 + 20, '#4a5a66', zorder=3)
    top = C.arm_y(2)[1]
    ax.text(C.arm_y(1)[1], z0 + 176, 'arms', ha='center', fontsize=8)
    box(top, top + 5, z0 - 20, z0 + 20, C.HUBC, zorder=3)                     # cap
    box(top + 5, top + 19, z0 - 22, z0 + 22, '#4a5a66', zorder=3)             # knob
    box(top + 12, top + 19, z0 - 7.5, z0 + 7.5, '#c9d1d6', zorder=4)          # its nut
    # the bolt, head inside the box
    box(y_pan - 4.5, top + 19, z0 - 3, z0 + 3, '#ffd34d', ec='k', lw=.6, zorder=5)
    box(y_pan - 8.5, y_pan - 4.5, z0 - 5, z0 + 5, '#ffd34d', ec='k', lw=.6, zorder=5)
    kw = dict(fontsize=8.5, arrowprops=dict(arrowstyle='-', color='0.3', lw=0.8), zorder=10)
    ax.annotate('M6 head inside the box', (y_pan - 6.5, z0 - 5), xytext=(130, z0 - 70), **kw)
    ax.annotate('captive jam nut: holds the\nhub to the panel for good', (f + 5, z0 - 7),
                xytext=(212, z0 - 125), **kw)
    ax.annotate('hub flange + sleeve', (f + 3, z0 + 30), xytext=(130, z0 + 200), **kw)
    ax.annotate('2 mm washers', (C.arm_y(0)[1] + 1, z0 - 20), xytext=(250, z0 - 80), **kw)
    ax.annotate('cap', (top + 2.5, z0 + 20), xytext=(272, z0 + 60), **kw)
    ax.annotate('star knob, captive nut:\ntighten = hood holds,\nloosen = folds', (top + 19, z0),
                xytext=(272, z0 - 10), **kw)
    ax.set_aspect('equal'); ax.set_xlim(125, 345); ax.set_ylim(z0 - 140, z0 + 250)
    ax.set_xlabel('mm across the bike from the centre line (right side)')
    ax.set_yticks([]); ax.grid(alpha=.2)
    ax.set_title('Section through the pivot, folded', fontsize=11)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'canopy/canopy-mounting.png'
    fig = plt.figure(figsize=(17, 6.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[2.35, 1])
    side(fig.add_subplot(gs[0])); section(fig.add_subplot(gs[1]))
    plt.tight_layout(); plt.savefig(out, dpi=110)
    print('studs at', [round(x) for x, _ in studs()]); print('wrote', out)
