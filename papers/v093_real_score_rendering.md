# V0.93 Real Score Rendering

V0.93 treats plan-based preview as invalid for final score display. `plan.measures` may appear in Agent Plan panels, but final score preview must use backend-rendered MusicXML, ScoreDocument rendering, real MusicXML text, or an explicit unavailable state.

The backend preview service tries MuseScore CLI first and Verovio for SVG when available. If neither renderer is installed, it returns a structured unavailable response with warnings and errors. This is intentionally preferable to drawing a fake staff from planning data.

The frontend exposes Score Source badges for `backend_svg`, `backend_png`, `ScoreDocument`, `MusicXML text`, and `Unavailable`. A Render Source Debug panel records run id, score id, backend URL, and preview-render status for reproducible screenshots.
