# Via standardization and DRC cleanup, 2026-10-04

Only `scsi-adapter.kicad_pcb` changed. Nothing is committed; `git diff` shows it all and
`git checkout pcb/scsi-adapter.kicad_pcb` undoes it. Most of the diff's line count is zone refill.

DRC (`kicad-cli pcb drc --schematic-parity --severity-all`, KiCad 9.0.9):

| | Before | After |
|---|---|---|
| Errors | 4 | 1 |
| Non-silkscreen warnings | 7 | 0 |
| Silkscreen warnings | 311 | 311 |
| Unconnected items | 0 | 0 |
| Schematic parity issues | 0 | 0 |

## 1. Vias

Standard is the Default net class size, 0.6 mm pad / 0.3 mm drill (434 of 455 vias already).

| Change | Net | Location (x, y mm) |
|---|---|---|
| 0.8/0.4 → 0.6/0.3 (15 vias) | VTERMINATOR | y = 72.5 at x = 162.6, 163.9, 165.2, 178.7, 180, 181.3, 182.6, 192.9, 194.3, 195.6, 196.9; y = 75.1 at x = 168.2, 183.196, 197.7; (168.2, 71.7) |
| 0.8/0.4 → 0.6/0.3 | GND | (194.7, 50.1) |
| 0.5/0.3 → 0.6/0.3 | GND | (160.1, 72.0) |
| **left at 0.5/0.3** (2 vias) | GND | (146.861, 62.394), (146.436, 62.818) |
| **left at 0.5/0.3** (2 vias) | /rp2350/DVDD_1V1 | (147.957, 64.692), (148.381, 64.268) |

- **VTERMINATOR group: please check.** All 15 sat in tidy rows under U301–U303, so they may have
  been deliberately larger. The other two VTERMINATOR vias and every +3V3 / TERMPWR via were
  already 0.6/0.3, so I standardized them. To restore: select them, Properties, pick the 0.8/0.4 preset.
- **The four left at 0.5/0.3** are two pairs by the RP2350 regulator at 0.6 mm pitch. At 0.6 mm the
  pads are exactly tangent, which gave four new "copper connection too narrow" warnings (0.079 mm)
  on B.Cu, In1.Cu and In2.Cu. I tried it, then put them back. Making them standard needs the pairs
  spread to about 0.75 mm pitch or more, which is a layout change.

## 2. DRC fixes

| # | Violation | Fix |
|---|---|---|
| 1 | Clearance 0.0005 mm and hole clearance 0.15 mm: GND via (200.3, 62.0) vs L3 +3V3 plane | Refilled all zones. The fill was stale; nothing moved. |
| 2 | Zones intersect: two "L3 +5V_SYS west-edge power-entry pour" zones on In2.Cu, both priority 1, sharing the edge at x = 112 | Merged into one L-shaped zone (kept UUID ccc15412, deleted 2267c869). Outline: (99.95, 29.95) (220.05, 29.95) (220.05, 34.15) (112, 34.15) (112, 120.05) (99.95, 120.05). Same settings. The old top strip had slightly skewed corners, (220, 30) and (112, 34.1); these are now square. |
| 3 | Co-located holes: two +3V3 vias at (187.4, 58.2) | Deleted one (b918f0d4). |
| 4 | Dangling track /ACK_RX, F.Cu, 0.0007 mm at (181.2018, 85.0605) | Deleted stub. |
| 5 | Dangling track /DB1_RX, F.Cu, 0.014 mm at (144.725, 89.455) | Deleted stub. |
| 6 | Dangling track /rp2350/QSPI_SD3, F.Cu, 0.246 mm, (146.684, 70.632) → (146.858, 70.458) | Deleted stub. |
| 7 | Dangling track /rp2350/QSPI_SS_INVERTED, F.Cu, 0.222 mm, (151.649, 65.949) → (151.492, 66.106) | Deleted stub. |
| 8 | Dangling track /scsi/TERMINATOR_OUT_MSG, B.Cu, 0.045 mm at (196.279, 81.5) | Deleted stub. |
| 9 | Dangling track /scsi/TERMINATOR_EN_INVERTED, In2.Cu | **Please check.** Removed an 8.9 mm dead-end tail: the In2 track along y = 77 ran past the via at (198.375, 77) to (200.075, 77), then up to (200.075, 72.917), (199.4, 72.242), and stopped at (199.4, 69.0) with nothing there. Trimmed the y = 77 track to end at the via and deleted the three segments beyond it. All six pads on the net (U301/U302/U303 pin 19, R341, SW301) are still connected. If that tail was heading for something not placed yet, it needs rerouting. |

Zones were refilled after each round of edits.

## 3. Not fixed

- **Courtyard overlap, D607 / C602 (error).** They overlap by about 0.05 mm at (112.4, 73–74.4).
  The column is packed: D601 above D607 and C601 below C602 have about 0.03 mm of slack in total,
  so no nudge clears it. One of the parts has to move sideways and be rerouted. The pads
  themselves are about 0.39 mm apart.
- **Silkscreen, 311 warnings, untouched.** Reference designators have not been placed yet:
  - 103 "clipped by solder mask": a reference sits on a pad.
  - 199 "overlap": a reference over another part's outline or reference.
  - 9 "clipped by board edge": the J101, J302, J501, J601 outlines overhang the edge (normal for
    edge connectors), and the H1 / H2 references sit at y = 29.85, just off the board.
