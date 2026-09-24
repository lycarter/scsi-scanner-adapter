# Sources

Where everything in `reference/` came from, so the folder can be rebuilt on a fresh clone.
`reference/` itself stays out of git (see `decisions.md`). What each item contains, and
which leads it holds, is in `reference-inventory.md`.

When you add a file to `reference/`, add a row here in the same commit.

## Howtek material: no public source

The files under `reference/HOWTEK/` came from obscure corners of the Internet and old
community archives. We have no stable link to any of them, so a fresh clone can't
re-download them. The rule is:

- **Anything we rely on gets written into our own notes**, with a citation to the file and
  section it came from. D4000 facts go in `scanner-facts.md`. Phase-specific findings go in
  that phase's `NOTES.md`. Firmware analysis output goes under `2-reverse-engineering/`.
- Assume a reader of the repo doesn't have the originals. A citation says where a fact came
  from; the note has to carry the fact itself.
- The firmware archives are listed below by SHA-256 so that a copy found later can be
  checked against ours. Everything else is listed by path only.

| Path (under `reference/HOWTEK/`) | SHA-256 |
|---|---|
| `D4000_4500/Firmware/4000/R535.exe` (D4000 FLASH R535) | `bd806368d27b2e5828b1507a0f9340a67c96adae6e2ac67992db2790c46da772` |
| `D4000_4500/Firmware/4500/R813.exe` (4500 FLASH R813) | `f47cb95f17494ce4ff863d4b4a9f64e86057e2b38e8c51f7c046644b0c8731dc` |
| `7500/Firmware_R014/R014.exe` (7500 flash) | `56df6c3ce37a813ae0230e7d65c76c3be522551754c47ed3dd3a73ed12549009` |
| `7500/Firmware_R014/scsi22.sea.hqx` (Howtek Mac SCSI driver 2.2) | `890fc2d900b85274e616295de739b7b3134ebe6419f4b890256fa6831020c479` |
| `7500/Firmware_R014/Trident4.0r46Drum.hqx` (Aztek Trident 4) | `ada975aec0c3fa4a70a343fbc84ae2031943717c290275b9f157db4fb1bb5fd1` |

Path only:

- `D4000_4500/Scanmaster 4500 Service Guide/`: scanned PDFs, no OCR.
- `D4000_4500/Field_Service_Tests_D4000_4500/`: DOS FST v3.2, ZDebug HEX files.
- `D4000_4500/Howtek Utilities for Mac/` (and `HowtekStuff.zip`, which keeps the resource
  forks): MacUtil 3.7 / 4.0 / 4.0.1, `HSI.INI`.
- `D4000_4500/MISC/`: native-resolution table, aperture study, battery note, sample scans.
- `7500/ScanMaster7500-ServiceGuide.pdf`, `7500/7500 Native Res.pdf`.
- `8000/`: HR8000 FST, firmware updater, native-resolution table.
- `MISC/`, `Howtek shipping instructions.txt`, `Alignment-Tools.zip`: operational notes.
- `HTSAI10.DLL`: 0 bytes, a placeholder.
- `aspi_471a2.exe`: Adaptec ASPI 4.71. It's generic and widely mirrored, but it came in the
  same bundle, so it has no link recorded.

## Public sources: re-downloadable

SHA-256 values are for the copies we have. Vendor URLs that serve "the latest version" may
return a newer file, so a mismatch means a new revision, not a bad download.

| Local path (under `reference/`) | Source | Retrieved | SHA-256 |
|---|---|---|---|
| `standards/SCSI-2_X3T9.2-375R_rev10L.pdf` | https://www.t10.org/ftp/x3t9.2/drafts/s2/s2-r10l.pdf | 2026-09-23 | `5bcb198e919c0c73a326a0649e0a176d1b24c8099ff56b564ede4fe3cef2af51` |
| `standards/SCSI-2_X3T9.2-375R_rev10L.txt` | https://stuff.mit.edu/afs/sipb/contrib/doc/specs/protocol/scsi-2/s2-r10l.txt (MIT SIPB mirror) | 2026-09-23 | `7e8a7280725b1abe1b029e893086b24f3b82c78bdad51cb117edb927c3d39174` |
| `datasheets/rp2350-datasheet.pdf` | https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf | 2026-09-24 | `2877d0f270fb6d6a57943bee58aaad536aa027bea1e5b1c4ce2541a3230d4be8` |
| `datasheets/hardware-design-with-rp2350.pdf` | https://datasheets.raspberrypi.com/rp2350/hardware-design-with-rp2350.pdf | 2026-09-24 | `cef88bc7d87e67b4262ee15f2b94b03566667143f4e8daf6931828bef6408059` |
| `datasheets/DS_FT232H.pdf` (v2.0) | https://raw.githubusercontent.com/standardsemiconductor/VELDT-info/master/DS_FT232H.pdf (mirror). FTDI's own v2.3 is at https://ftdichip.com/wp-content/uploads/2025/11/DS_FT232H.pdf, but it needs a browser | 2026-09-24 | `c836d6482386903b8f0886b0b8f709327f20d688285573a335d060994a46cfc0` |
| `datasheets/AN_167_FT1248-Parallel-Serial-Interface-Basics.pdf` (v1.1) | https://ftdichip.com/wp-content/uploads/2020/08/AN_167_FT1248-Parallel-Serial-Interface-Basics.pdf (browser only; scripts get 403) | 2026-09-24 | `f8b52784ef48739982e4a3ff05271db394278a484b0e60f423e51a0cbfe46721` |
| `datasheets/tca9535.pdf` | https://www.ti.com/lit/ds/symlink/tca9535.pdf | 2026-09-24 | `cdaa29e68dbf21d55819621aae81544ce85c898a48dbd202b3067d18c87b0ab8` |
| `datasheets/tca9555.pdf` (SCPS200E, rev. 2019-04) | https://www.ti.com/lit/ds/symlink/tca9555.pdf | 2026-09-24 | `9706a3ccbf0bc915387949ab82bc0020a1a5bfdd67d8f51c4605a8d4b16bb231` |
| `datasheets/tca6416a.pdf` (SCPS194F, rev. 2023-01) | https://www.ti.com/lit/ds/symlink/tca6416a.pdf | 2026-09-24 | `a7deab846f35a9f1377c260b3e517fbac90683416bab1aa28028b45e53fc292b` |
| `datasheets/mcp23017.pdf` (DS20001952D) | https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23017-Data-Sheet-DS20001952.pdf | 2026-09-24 | `63cb5f2bec44434cdeeada1790d0316c9dc06b33febb489ad87bb0e2d540496a` |
| `datasheets/tusb321.pdf` (SLLSEO6C, rev. 2018-08) | https://www.ti.com/lit/ds/symlink/tusb321.pdf | 2026-09-24 | `ef1cea96d1e85a985410e1316a6b52381cf50a482681dbb91da9a9920025305e` |
| `datasheets/lm66100.pdf` (SLVSEZ8A, rev. 2019-06) | https://www.ti.com/lit/ds/symlink/lm66100.pdf | 2026-09-24 | `83c17370a97b85ecebe20605da0b955d4ff6f9a474e9692b611a6685d7ad0f00` |
| `datasheets/lm66200.pdf` (SLVSG04, 2021-11) | https://www.ti.com/lit/ds/symlink/lm66200.pdf | 2026-09-24 | `0a70747e607286b215b82b35244d60eca9eba0a50728d83a96cbbc7fade75d85` |
| `datasheets/tps737.pdf` (SBVS067W, rev. 2025-08) | https://www.ti.com/lit/ds/symlink/tps737.pdf | 2026-09-24 | `f706914950efed0b60423e9035b67c6dffbacd28091c452f24b7c0927bb3c851` |
| `datasheets/CH334DS1_en.pdf` (WCH CH334/CH335, **English, V2.5**; older than the Chinese V2.91) | https://cdn-learn.adafruit.com/assets/assets/000/131/435/original/CH334DS1.PDF (Adafruit mirror; the official page https://www.wch-ic.com/downloads/CH334DS1_PDF.html needs a browser) | 2026-09-24 | `c078817182e320e7bc1c2f5d28b361a55246bac70d4a07b05cb0e997dedea586` |
| `datasheets/CH334.pdf` (WCH CH334/CH335, Chinese, V2.91) | https://datasheet.lcsc.com/datasheet/pdf/77721fceaa29165ba79c58173b46c67f.pdf (LCSC mirror) | 2026-09-24 | `a5d941fc69a6fa731e135e64e5096ef291b45f43260a98abd9c014b38d427f1c` |
| `datasheets/FE1.1s.pdf` (Terminus FE1.1s) | https://datasheet.lcsc.com/datasheet/pdf/13d3e118f5bbcdd185acaf8c9498f8e5.pdf (LCSC mirror) | 2026-09-24 | `5677873747ef908e0ed07a3334254eeaaec7ac1974b4c6e777be11ec72e21b9c` |
| `third-party/BlueSCSI-v2/` | `git clone --depth 1 https://github.com/BlueSCSI/BlueSCSI-v2.git`, then check out commit `92db68f2d9b480cbb3b369a471ec55a9758da818` (2026-08-22) | 2026-09-23 | (git commit) |
| `third-party/BlueSCSI-v2_Desktop_50_Pin_schematic.pdf` | Exported with `kicad-cli` 9.0 from `BlueSCSI-v2/hardware/Desktop_50_Pin/Desktop_50_Pin_TopConn.kicad_sch` | 2026-09-23 | `98bc04a64ad0944f4c85e3314ac969880a09e087265211b7946312993a7ecec2` |
| `third-party/BlueSCSI-v2_Desktop_50_Pin_netlist.xml` | Same project, `kicad-cli sch export netlist --format kicadxml` | 2026-09-23 | `a22813fe386856b3b9b3dc83dcea3fe25af64c029ce38b0244121be22e006f16` |

The two BlueSCSI exports are derived files, so rerunning `kicad-cli` (e.g.
`kicad-cli sch export pdf -o <out>.pdf <file>.kicad_sch`) recreates them. Their hashes
will differ between KiCad versions. The exact export flags weren't recorded, so the commands
above are a reconstruction.
