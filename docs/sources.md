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
  that phase's `NOTES.md`. Firmware analysis output goes under `design_docs/2-reverse-engineering/`.
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
| `datasheets/tps25947.pdf` (SLVSFC9C, rev. 2026-05) | https://www.ti.com/lit/ds/symlink/tps25947.pdf | 2026-09-24 | `8f96de389903091650d4f462dcfad3210071c3ae7093623a7978f34baf8a65b4` |
| `datasheets/CH334DS1_en.pdf` (WCH CH334/CH335, **English, V2.5**; older than the Chinese V2.91) | https://cdn-learn.adafruit.com/assets/assets/000/131/435/original/CH334DS1.PDF (Adafruit mirror; the official page https://www.wch-ic.com/downloads/CH334DS1_PDF.html needs a browser) | 2026-09-24 | `c078817182e320e7bc1c2f5d28b361a55246bac70d4a07b05cb0e997dedea586` |
| `datasheets/CH334.pdf` (WCH CH334/CH335, Chinese, V2.91) | https://datasheet.lcsc.com/datasheet/pdf/77721fceaa29165ba79c58173b46c67f.pdf (LCSC mirror) | 2026-09-24 | `a5d941fc69a6fa731e135e64e5096ef291b45f43260a98abd9c014b38d427f1c` |
| `datasheets/FE1.1s.pdf` (Terminus FE1.1s) | https://datasheet.lcsc.com/datasheet/pdf/13d3e118f5bbcdd185acaf8c9498f8e5.pdf (LCSC mirror) | 2026-09-24 | `5677873747ef908e0ed07a3334254eeaaec7ac1974b4c6e777be11ec72e21b9c` |
| `datasheets/fdv301n.pdf` (onsemi FDV301N) | https://datasheet.lcsc.com/datasheet/pdf/93a935c137014f7189ca430583afc519.pdf (LCSC mirror; onsemi's site blocks scripts) | 2026-09-26 | `61444360dd8a9c01d48f428b40aa9f186082b723bdef7c63619894496ef44e3c` |
| `datasheets/74LVC1G17.pdf` (Nexperia 74LVC1G17) | https://assets.nexperia.com/documents/data-sheet/74LVC1G17.pdf | 2026-09-26 | `cff7c8e80360d22a9df013821325e4d1ddd03022ea0aa1e4ebd296434604c5e9` |
| `datasheets/74LVC14A.pdf` (Nexperia 74LVC14A) | https://assets.nexperia.com/documents/data-sheet/74LVC14A.pdf | 2026-09-26 | `b324cd3540deacdc7926b2b24f150eefefe3ebe9d3a4acd28aad6578df882169` |
| `datasheets/lm393-ti.pdf` (TI LM393 family) | https://www.ti.com/lit/ds/symlink/lm393.pdf | 2026-09-26 | `dd9f3d029261a161685e9fab49a6cf081924cd5a4d1a8cb0205a062147698f08` |
| `datasheets/lm393-onsemi.pdf` (onsemi LM393 (our part, LM393DR2G)) | https://datasheet.lcsc.com/datasheet/pdf/0a7f69005bd54ef2bf3e8b1a5a2f8965.pdf (LCSC mirror) | 2026-09-26 | `b2ecbd1776d1e664f2882b801c75ca83da0f938948f23590d78dfe9b26e64126` |
| `datasheets/sn74lvth245a.pdf` (TI SN74LVTH245A) | https://www.ti.com/lit/ds/symlink/sn74lvth245a.pdf | 2026-09-26 | `ac32cafddfb9974bee906208b0a84a0182b1947acf14ce538701adb9b5bcdeb7` |
| `datasheets/sn74lvth125.pdf` (TI SN74LVTH125) | https://www.ti.com/lit/ds/symlink/sn74lvth125.pdf | 2026-09-26 | `a5c5f2e086fba87e20ddf10892cf76b2230d590ae94eed911dc8302dee48acdb` |
| `datasheets/tl431.pdf` (TI TL431 (reference for the CJ431 clone)) | https://www.ti.com/lit/ds/symlink/tl431.pdf | 2026-09-26 | `ed2e90697de4e2c553195514adf1ee59cda42863716b6ef702b8304a5b921d22` |
| `datasheets/cj431.pdf` (CJ CJ431) | https://datasheet.lcsc.com/datasheet/pdf/dca1b312f3e4467c9202db2f691d7926.pdf (LCSC mirror) | 2026-09-26 | `68a405075950c4b542a7dc4f2cb27583350ab013c1abafbace4b4f0e143b7c88` |
| `datasheets/ABM8-272-T3.pdf` (Abracon ABM8-272-T3) | https://abracon.com/datasheets/ABM8-272-T3.pdf | 2026-09-26 | `aead22b6bd9d6f8ad4472352f70fce3ade633e90b9772ba80fabe8fd0856ae91` |
| `datasheets/aota-b201610.pdf` (Abracon AOTA-B201610) | https://datasheet.lcsc.com/datasheet/pdf/0ca6a1bbc70fd13a89f7695ff7dd8558.pdf (LCSC mirror) | 2026-09-26 | `b15dcb32224c50ddf5c7643358bdef49177b451d72933d7fbb02f3756aca7827` |
| `datasheets/w25q128jv.pdf` (Winbond W25Q128JV) | https://www.winbond.com/resource-files/w25q128jv%20revf%2003272018%20plus.pdf | 2026-09-26 | `809f066e62bcde10b12c2202daf05f4776929ad7dc5f9d3b5131cdcc84502bc1` |
| `datasheets/aps6404l.pdf` (AP Memory APS6404L-3SQR) | https://datasheet.lcsc.com/datasheet/pdf/e8190d37d866392254d3573489478495.pdf (LCSC mirror) | 2026-09-26 | `3ab2622938f523db159480bede7f64276ad06914fe6cd2f28a141134f7a0df45` |
| `datasheets/93LC56B.pdf` (Microchip 93LC56B) | https://datasheet.lcsc.com/datasheet/pdf/b260944fcfd7439cbd9e7114bfac5025.pdf (LCSC mirror) | 2026-09-26 | `f9a7698e3531a357602a7ab0baebf1ab157771c9b15fa84c9248e6a6b87acf3f` |
| `datasheets/h5vud5bb.pdf` (hongjiacheng H5VUD5BB) | https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2404031005_hongjiacheng-H5VUD5BB_C20615820.pdf (LCSC) | 2026-09-26 | `bce8e438bf2efbd292764750df2184d7aee628bbb9603bedbc5a31eb7fadf5ac` |
| `datasheets/h7vl10b.pdf` (hongjiacheng H7VL10B) | https://datasheet.lcsc.com/datasheet/pdf/86bcb93e853072ca73af9066873e195f.pdf (LCSC mirror) | 2026-09-26 | `5399776ba9984cc7efc3d6f3f771da4db3cc36ca5af49c85e03f38e5ae2ab281` |
| `datasheets/smf6.0a.pdf` (SMF6.0A (C19077499)) | https://datasheet.lcsc.com/datasheet/pdf/fa41ee376507916bceb7512729759974.pdf (LCSC mirror) | 2026-09-26 | `c8f137df222c1c36b0356096e10d601434b420c2f65407c222229dbd725df74a` |
| `datasheets/2n7002-cj.pdf` (2N7002 (C8545)) | https://datasheet.lcsc.com/datasheet/pdf/a141b8bd86b14475955ac8c4d3eea0a8.pdf (LCSC mirror) | 2026-09-26 | `7941fb423af7c6c6c8979063a7e8819bb19217ece275efcce18948950a41d9f6` |
| `datasheets/tps2116.pdf` (TI TPS2116, SLVSFG1A, rev. 2021-05) | https://www.ti.com/lit/ds/symlink/tps2116.pdf | 2026-09-26 | `5babd88afb84e2e65c9c0da23b75f85758c0c730e34102a0fb746ac9573ed1d5` |
| `datasheets/tps2121.pdf` (TI TPS2120/TPS2121 (rejected alternative)) | https://www.ti.com/lit/ds/symlink/tps2121.pdf | 2026-09-26 | `b2f5950f596dc2c4ca33e4ebac27fd35e4dcc68ea63e173466123e1118e91a06` |
| `datasheets/digital_discovery_pin_headers.pdf` (Digilent 250-096 2×16 fly-wire assembly drawing (Digital Discovery DIN cable)) | https://digilent.com/reference/_media/reference/test-and-measurement/digital-discovery/250-096_sn-1050323-1.pdf | 2026-09-26 | `f4f848b8428fcebf0aac322d4308b61e42d6cbe4731974d628f70f9344f5b1d7` |
| `datasheets/digital_discovery_pin_headers_2.pdf` (Digilent 250-097 2×6 fly-wire assembly drawing (Digital Discovery DIO cable)) | https://digilent.com/reference/_media/reference/test-and-measurement/digital-discovery/250-097_s-n160718-1.pdf | 2026-09-26 | `f8e59dc71f5d6944ff22c793992d30e85194f28b4ef3279fb484502c7db66965` |
| `datasheets/digital_discovery_rm_web.pdf` (Digilent Digital Discovery reference manual (DIN connector pinout: Fig. 8)) | https://media.digikey.com/pdf/data%20sheets/digilent%20pdfs/digital_discovery_rm_web.pdf (DigiKey mirror; digilent.com blocks scripts) | 2026-09-26 | `50529682a9bda933e4bd9acc91daf5dc1eada3d3690b66e944e9b916088345c0` |
| `datasheets/240-127_Web.pdf` (Digilent Digital Discovery datasheet) | https://media.digikey.com/pdf/Data%20Sheets/Digilent%20PDFs/240-127_Web.pdf (DigiKey mirror) | 2026-09-26 | `66633290097d886b01feee8a5cf9b827a870155f0c7807d372bd33e57d89839c` |
| `third-party/BlueSCSI-v2/` | `git clone --depth 1 https://github.com/BlueSCSI/BlueSCSI-v2.git`, then check out commit `92db68f2d9b480cbb3b369a471ec55a9758da818` (2026-08-22) | 2026-09-23 | (git commit) |
| `third-party/BlueSCSI-v2_Desktop_50_Pin_schematic.pdf` | Exported with `kicad-cli` 9.0 from `BlueSCSI-v2/hardware/Desktop_50_Pin/Desktop_50_Pin_TopConn.kicad_sch` | 2026-09-23 | `98bc04a64ad0944f4c85e3314ac969880a09e087265211b7946312993a7ecec2` |
| `third-party/BlueSCSI-v2_Desktop_50_Pin_netlist.xml` | Same project, `kicad-cli sch export netlist --format kicadxml` | 2026-09-23 | `a22813fe386856b3b9b3dc83dcea3fe25af64c029ce38b0244121be22e006f16` |

The two BlueSCSI exports are derived files, so rerunning `kicad-cli` (e.g.
`kicad-cli sch export pdf -o <out>.pdf <file>.kicad_sch`) recreates them. Their hashes
will differ between KiCad versions. The exact export flags weren't recorded, so the commands
above are a reconstruction.
