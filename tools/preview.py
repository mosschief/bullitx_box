#!/usr/bin/env python3
"""Render a dimensioned preview of the Bullitt X panels next to the Vermoots originals."""
import sys, os, numpy as np, ezdxf
from ezdxf.path import make_path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

def load(path):
    msp = ezdxf.readfile(path).modelspace()
    polys, circles = [], []
    for e in msp:
        if e.dxftype() == 'LWPOLYLINE':
            polys.append(np.array([(p.x, p.y) for p in make_path(e).flattening(0.05)]))
        elif e.dxftype() == 'CIRCLE':
            circles.append((e.dxf.center.x, e.dxf.center.y, e.dxf.radius))
    return polys, circles

def draw(ax, path, colour, lw, label=None, holes=True, dash=None):
    polys, circles = load(path)
    for i, a in enumerate(polys):
        ax.plot(a[:, 0], a[:, 1], ls=dash or '-', color=colour, lw=lw,
                label=label if i == 0 else None)
    if holes:
        for cx, cy, r in circles:
            ax.add_patch(plt.Circle((cx, cy), max(r, 6), color=colour, fill=False, lw=lw))
    xs = np.concatenate([a[:, 0] for a in polys]); ys = np.concatenate([a[:, 1] for a in polys])
    return xs.min(), xs.max(), ys.min(), ys.max(), circles

def main(src, out):
    fig, axes = plt.subplots(2, 1, figsize=(15, 9))

    ax = axes[0]
    draw(ax, f'{src}/vermoots/Side panel.dxf', '0.65', 1.2, 'original (Bullitt)', holes=False, dash='--')
    x0, x1, y0, y1, ci = draw(ax, f'{src}/out/Side panel X.dxf', 'tab:blue', 2.0, 'Bullitt X (+220 mm)')
    for cx, cy, r in ci:
        ax.annotate(f'{cx:.1f}, {cy:.1f}', (cx, cy), fontsize=7, color='tab:blue',
                    xytext=(0, 14), textcoords='offset points', ha='center')
    ax.set_title(f'Side panel  —  {x1-x0:.1f} x {y1-y0:.1f} mm  (was 764.8 x 326.4)', fontsize=11)
    ax.legend(fontsize=9, loc='lower left')

    ax = axes[1]
    draw(ax, f'{src}/vermoots/fond.dxf', '0.65', 1.2, 'original (Bullitt)', holes=False, dash='--')
    x0, x1, y0, y1, ci = draw(ax, f'{src}/out/fond X.dxf', 'tab:blue', 2.0, 'Bullitt X (+220 mm)')
    for cx, cy, r in sorted(ci):
        if cy > 100:
            ax.annotate(f'x={cx:.1f}', (cx, cy), fontsize=7, color='tab:blue',
                        xytext=(0, 12), textcoords='offset points', ha='center')
    ax.set_title(f'Floor (fond)  —  {x1-x0:.1f} x {y1-y0:.1f} mm  (was 828.4 x 394.0)', fontsize=11)
    ax.legend(fontsize=9, loc='center left')

    for ax in axes:
        ax.set_aspect('equal'); ax.grid(alpha=.3)
        ax.set_xlabel('mm from the back of the cargo bay')
    plt.tight_layout(); plt.savefig(out, dpi=110)
    print('wrote', out)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
