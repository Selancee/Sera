# Sera brand-asset provenance

## Canonical mark

`assets/branding/sera-icon-master.png` is the canonical Sera application mark. It was
generated specifically for this repository on 3 September 2026 with OpenAI's built-in
image-generation tool. No third-party image, logo or other visual reference was supplied.

The mark depicts an abstract `S` made from score-staff ribbons joined by a square patch
node. It intentionally avoids the Electron atom, OpenAI/Codex knot, GitHub Octocat and
literal music-note silhouettes.

The generated raster is used under the project owner's direction as Sera branding. This
provenance record is not a trademark clearance; a formal similarity search remains the
owner's decision before broader commercial registration.

## Derived assets

Run the following command when the master changes:

```powershell
.\.venv\Scripts\python.exe scripts\generate_sera_brand_assets.py
```

The script requires Pillow and produces the committed PNG/ICO application assets plus
`assets/branding/sera-github-social-preview.png`. The Electron executable, runtime window,
frontend favicon, README and legacy PyInstaller launcher all resolve to these derivatives.

Canonical SHA-256 values at introduction:

- Master PNG: `822b6d8e13b132c2eafd19d4a99de0b1f399a50b6c2792ce8d3982309f554cb5`
- Multi-size ICO: `686948f584b0fa2c0e5c8bf01a854df56f05d420a1b19df892a6966173c1fad2`
- GitHub social preview: `88a73cbea1f3a2247137f560485ae118f7c3829d354b493b7518e11692a65e6c`

## Generation prompt summary

- Distinctive Sera mark for reliable MusicXML editing through structured score patches.
- Abstract `S` made from flowing staff ribbons with a central patch node.
- Midnight indigo, cyan/teal and warm coral palette.
- No text, watermark, Electron atom, OpenAI/Codex form, Octocat or stock music-note mark.
