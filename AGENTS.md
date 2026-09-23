# AGENTS.md

Guidance for AI agents (Claude Code and others) working in this repo.

## Project in one paragraph

Custom hardware and software to drive a **Howtek Scanmaster D4000** drum scanner
(narrow single-ended SCSI-2, 1995-era) from a modern computer over USB-C. A Power Mac
G4 / OS 9 / SilverFast setup works today and is our reference for observing the
protocol. See `README.md` for the four phases.

## How to work with the owner

- **Partner, not delegate.** Work in small steps and check in at decision points. Don't try to
  do a whole phase in one go.
- **Teach.** The owner wants to learn. For each decision, give the reasoning, the
  alternatives you considered, and why you rejected them. Say how confident you are, and
  mark unverified claims as unverified.
- **Ask questions** when a choice is the owner's to make (budget, physical setup,
  preferences) or when a wrong guess would be expensive (a PCB spin, a part order).
- Tooling: KiCad for EDA; JLCPCB for fab/assembly; LCSC for parts. Prefer parts that
  JLC can assemble (check LCSC stock and whether the part is "basic" or "extended").

## Context hygiene: phases are separate

Each phase folder has a `NOTES.md` that holds that phase's requirements, decisions, open
questions, and log. **Read only the phase you're working on**, plus these shared docs:

- `docs/scanner-facts.md`: verified facts about the D4000 (hardware, SCSI, firmware layout).
- `docs/decisions.md`: short cross-phase decision log (details stay in the phase notes).
- `docs/reference-inventory.md`: what's in `reference/` and which leads to follow up. Read it
  only when you need the reference material.

When you learn something durable, update the matching file. Put facts in
`scanner-facts.md`, and a decision in the phase `NOTES.md` with a one-line entry in
`decisions.md`. Keep `README.md` barebones.

## The `reference/` folder

- It holds vendor manuals, firmware, and utilities. It is **not tracked in git** (size and
  copyright), so don't assume a fresh clone has it.
- Classic Mac apps in it (e.g. `MacUtil 4.0.1`) keep their code in the **resource fork**,
  stored as xattrs (`file/..namedfork/rsrc`). The data fork is 0 bytes. Copying or zipping
  with ordinary tools, or committing to git, silently strips these forks.
- Scanned PDFs need page rendering. PyMuPDF (`pip install pymupdf`) or poppler works.
- Treat firmware as read-only. Put analysis output under `2-reverse-engineering/`, never in
  `reference/`.

## Safety notes

- The scanner has PMT high voltage (up to 1 kV) and mains supplies inside. Before anyone
  opens it or probes inside, remind them to power it off and let it sit.
- SCSI: never hot-plug. TERMPWR is a fused power rail and pin shorts can damage cards.
  Every bus needs exactly two terminators, one at each physical end.
