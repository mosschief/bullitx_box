# Cutting the Bullitt X box on a Shapeoko 5 Pro from 1/2" ply

![cut sheets](../preview/cnc-sheets.png)

## It takes a half sheet plus a smaller piece

The floor and both side panels fill a 4 x 4 ft half sheet. The front and back
panels do not fit in what is left: the floor (394 mm) and the two side panels
(329 mm each) already use about 1075 mm of the 1219 mm, even nested tightly, and
the smallest side of the front panel is 271 mm. So:

| Sheet | Parts | Stock |
|---|---|---|
| **A** | floor, right side panel, left side panel | 4 x 4 ft half sheet |
| **B** | front panel, back panel | any piece at least **720 x 470 mm** (28.5 x 18.5 in); a 2 x 4 ft piece is plenty |

## Measure the ply, then pick the files

"1/2 inch" ply is usually 11.9 mm (15/32") or 12 mm (Baltic birch), sometimes a true
12.7 mm. Measure it with calipers in a few places and use the matching G-code:

| Measured thickness | Use |
|---|---|
| 11.7 to 12.3 mm | `gcode/*_12mm-stock.nc` (cuts 12.5 mm deep) |
| 12.4 to 13.0 mm | `gcode/*_12.7mm-stock.nc` (cuts 13.2 mm deep) |

Both cut about 0.5 mm into the spoilboard and leave 3 mm tabs.

## Machine setup

- **Tool:** 1/4" (6.35 mm) two-flute flat end mill. An upcut (Carbide 3D #201) works;
  a compression bit gives cleaner faces on both sides of the ply.
- **Spindle:** 18,000 rpm. On the Carbide router, set the dial by hand; the file sends `S18000`.
- **Feeds:** 1500 mm/min (59 ipm) cutting, 400 mm/min plunge, 800 mm/min in the holes,
  2.5 mm per lap. Deliberately conservative for a first run. Turn the feed override up
  if it sounds happy.
- **Zero:** X0 Y0 at the **front-left corner of the stock**, Z0 on the **top of the stock**.
  The BitZero corner probe does all three at once.
- **Safe height:** 15 mm above the stock. Keep clamps below that or out of the way of
  the parts.
- **Workholding:** every part stays attached by tabs (10 mm long, 3 mm thick; 9 on the
  floor, 7 per side panel, 4 each on the front and back). Screw the sheet down around the
  edge. Sheet A has at least 65 mm of clear margin all the way round. Put a few screws in
  the middle strips too if the sheet bows.

Each file cuts all its holes first, then each part outline. The outline is cut by
spiralling down 2.5 mm per lap with no plunges, followed by one clean-up lap at full
depth. Holes are helically bored with the same 1/4" bit (8 mm and 10 mm holes).

Rough run times at 100% feed: sheet A about 40 min, sheet B about 15 min.

## Run order

**Sheet A** (half sheet)
1. `sheet-A_floor-and-sides_front-link-holes-optional_<t>.nc`: **only if you want the
   front-link holes cut by the machine** (see below). Leave zero where it is.
2. `sheet-A_floor-and-sides_<t>.nc`

**Sheet B** (front/back piece)
1. `sheet-B_front-and-back_<t>.nc`

Cut the tabs with a flush-trim saw or chisel and sand them flush.

### The optional front-link holes

The side panel's front-link hole is the one dimension the previous check could not
pin down. The frame model puts that mount about 9 mm off where a clean 220 mm stretch
predicts. So it is in a separate file:

- Measure your bike first: the front link mount should be about 981 mm from the back
  of the cargo bay (the datum the main README uses). If it matches, run the optional file.
- If you're not sure, skip it, fit the panels, and drill the 8 mm hole through the bracket
  on the bike.

They are the purple holes in the picture above, and on their own layer
(`HOLES_front_link_optional`) in the DXF.

## Which side is which

Everything is cut with the **good face up**, so the face on top becomes the **outside**
of the box. The middle panel on sheet A is the **right** side panel (as Vermoot drew it)
and the top one is the **left** (mirrored). The floor, front and back panels are symmetric,
so either face can go up.

## What changed for 1/2" ply

The design was drawn for 10 mm ply. I thickened each panel in Vermoot's 3D assembly
(`Plateformes Bullitt Vermoot.step`) on the side it is free to grow and checked every
clash. Everything here is set for 12 mm. A true 12.7 mm sheet is only 0.7 mm off,
which the bolt holes and gaps absorb.

| Part | What happens with thicker ply | Change made |
|---|---|---|
| Side panels | Links bolt to the inside face, so they grow outward. The nearest frame tube is 7.8 mm away. | None to the outline |
| Front and back panels | Bolted to the frame by the outside face, so they grow into the box. The front and back links bolt to that inside face. | The front and back link bolt holes in the **side panel** move with the link: front one 1.9 mm back and 0.5 mm up (the front panel leans 15°), back one 2.0 mm forward |
| Floor | Sits on the cross beams and grows upward, eating Vermoot's 3 mm gap under the front and back panels (down to 0.2 mm at 12.7 mm). | **Bottom edge of the front and back panels trimmed 2 mm** to put the gap back |
| Bottom links | Peg into the frame and bolt to the side panel's inside face | None |
| Printed links | None of them change | Print as before: 2 front, 2 back, 4 bottom |

Other effects to know about:

- **Every bolt through the ply needs to be about 2 mm longer** (3 mm for 12.7 mm ply).
- The box is 4 mm wider outside (sides grow outward). Inside, it is 4 mm shorter and 2 mm shallower.
- The panels weigh about 20% more.

## Which plywood

1/2" is a good choice for the Bullitt X. It is 1.7 times as stiff as Vermoot's 10 mm,
and the stretched side panels now span 472 mm along the bottom edge between the
bottom link and the front link. The cost is weight: about 9.5 kg of panels in birch,
against 8 kg at 10 mm.

**What to ask for:** 12 mm Baltic birch with **exterior (WBP / phenolic) glue**, often
sold as "exterior" or "FSF" grade. Plain Baltic birch is often made with interior glue,
which delaminates once water gets into the edges.

| Plywood | Verdict |
|---|---|
| Exterior-glue Baltic birch, 12 mm | **Best all-round.** Void-free, machines cleanly, and the edges look good sealed. |
| Marine ply (BS 1088 okoume), 12 mm | Very weatherproof and about 25% lighter than birch. It costs more, and the soft face dents. |
| Interior Baltic birch or hardwood ply | Fine only if the bike lives indoors and gets sealed well. |
| CDX / sheathing | Avoid. It has voids, splinters on the CNC, and the edges soak up water. |

Baltic birch usually comes in 5 x 5 ft sheets. Sheet A needs a 4 x 4 piece; the
leftover strip is too narrow for the back panel (354 mm), so sheet B still needs a
second piece unless the files are re-nested for a 5 x 5 sheet.

**Weatherproofing.** The edges are what fail, so seal them before anything else, and
do the faces and holes after that:

1. Round the edges over (1 to 2 mm) and sand to 180 grit.
2. Seal everything, edges and bolt holes included. Use either a penetrating epoxy sealer
   followed by 2 or 3 coats of exterior spar varnish, or an exterior primer followed by
   2 coats of exterior paint. Epoxy gives the best protection, and paint is the cheapest
   and easiest to touch up.
3. Leave the 3 mm gaps under the front and back panels open so water can drain.

## Shopping list

Vermoot's files don't list hardware, so these sizes come from his 3D assembly. Every
bolt was traced through the parts it clamps, then 2 mm was added for the thicker ply.
The 8 mm holes (side panels and printed links) take **M6**. The 10 mm holes (floor,
front and back panels) take **M8**.

**Check one thing before you buy.** The model shows the frame's mounting points as plain
10 mm holes, so this list assumes bolts go all the way through with a nyloc nut behind.
Try an M6 and an M8 bolt in one of the floor mounting points and one of the rear frame
tabs on your bike. If they thread in, you don't need the nuts and the frame bolts can be
much shorter.

### Bolts
Use stainless A2 (A4 if you ride near salt), in button-head hex or hex-head style.

| Bolt | Qty | Where it goes | What it clamps |
|---|---|---|---|
| M6 x 30 | 8 | Side panels to the 8 printed links, 4 per side | 12 mm ply + 4 mm link |
| M6 x 35 | 2 | Back links through the back panel into the rear frame tabs | 4.5 mm link + 12 mm ply + 4 mm tab |
| M6 x 50 | 2 | Front links through the front panel and the front frame | 4.5 mm link + 12 mm ply + 20 mm tube |
| M8 x 35 | 2 | Back panel, lower corners, to the rear frame tabs | 12 mm ply + 4 mm tab |
| M8 x 50 | 13 | Floor to the 4 cross beams (12), front panel centre to the front frame (1) | 12 mm ply + 20 mm tube |
| M8 x 65 | 2 | Floor tongue to the rear cross brace | 12 mm ply + 35 mm brace |

### Nuts and washers

| Part | Qty |
|---|---|
| M6 nyloc nut | 12 |
| M8 nyloc nut | 17 |
| M6 washer, large OD ("fender", about 18 mm) for the wood side | 8 |
| M6 washer, standard, for the link or frame side | 16 |
| M8 washer, large OD (about 24 mm) for the wood side | 17 |
| M8 washer, standard, for the frame side | 17 |

Buy a few spares of each.

### Printed links

| Part | Qty |
|---|---|
| `bottom link.stl` | 4 |
| `front link.stl` | 2 |
| `back link.stl` | 2 |

Every link is symmetric, so the same file works on both sides and nothing needs
mirroring. All eight together are about 120 cm³ of plastic, or roughly 160 g of PETG
printed solid, so **one 1 kg spool** is plenty.

Use **PETG or ASA, not PLA**. PLA creeps under load and goes soft on a bike parked in
the sun. For strength, print with 5 walls and 40% or more infill.

### Wood and finish

- 1 x 4 x 4 ft sheet of 12 mm exterior Baltic birch (sheet A)
- 1 x piece at least 720 x 470 mm of the same (sheet B); a 2 x 4 ft piece covers it
- Penetrating epoxy sealer plus exterior spar varnish, or exterior primer plus paint:
  about 1 litre (1 quart) of each is enough for both sides and every edge
- 180-grit sandpaper
- 1/4" two-flute end mill (see Machine setup)

## Files

| File | What it is |
|---|---|
| `sheet-A_floor-and-sides.dxf` / `.svg` | Nested sheet A in mm, for Carbide Create or anything else |
| `sheet-B_front-and-back.dxf` / `.svg` | Nested sheet B |
| `gcode/*.nc` | Ready-to-run G-code as above |
| `parts/*.dxf` | Each part on its own, adjusted for 12 mm ply |

The DXFs and SVGs include the stock outline (layer `STOCK_OUTLINE_do_not_cut` or the grey
rectangle). Use it to line the drawing up with your stock, then delete it.

### Doing it in Carbide Create instead

Import the sheet SVG (it is sized in mm). Check the floor reads 1048.4 mm long. Set the
stock to the sheet size and measured thickness, with zero at the lower-left and on top. Then:

- **Contour, inside**, on the holes
- **Contour, outside**, on the parts, with tabs

Use the same tool and feeds as above.

## Checking or regenerating

```
pip install ezdxf shapely matplotlib
python3 tools/make_cnc.py <folder with Vermoot's DXFs>            # writes cnc/ and preview/cnc-sheets.png
python3 tools/backplot.py out.png cnc/sheet-A_floor-and-sides.dxf cnc/gcode/sheet-A_*12mm-stock.nc
```

`make_cnc.py` takes `--thickness` for the geometry and `--gcode-stock` for the depths,
plus the tool, feeds, tab and spacing settings. `backplot.py` reads the G-code back and
checks it against the nested DXF. Each file here passed with no gouges, nothing outside
the stock, every hole and outline cut through, and tabs only where intended.
`preview/backplot-sheet-A.png` shows the result for sheet A.
