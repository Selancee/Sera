# V0.91 Layout Readability

V0.91 addresses a practical Workbench issue: generated scores could be legal but visually cramped or tiny. The default layout mode is now `fit_width`, with explicit layout modes for page, continuous, compact, and large-print use.

The fallback SVG renderer keeps deterministic hit mapping, while the canvas container now preserves readable measure width and scrolls horizontally for longer scores instead of compressing all measures into the first viewport. The toolbar provides fixed zoom presets, Reset View, Re-render Score, and MusicXML Text Preview.

Render recovery is treated as part of usability. If OSMD fails or renders blank output, the app reports the fallback reason and continues with the deterministic renderer. The StatusBar exposes renderer mode, render state, render time, layout mode, and zoom so the user can understand whether a view problem is rendering, scaling, or score data.
