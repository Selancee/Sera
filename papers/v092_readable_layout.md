# V0.92 Readable Layout

V0.92 replaces the long single-row fallback score layout with wrapped systems. The default generated-score and Workbench layout uses four measures per system for ordinary 8/16/32-measure piano scores.

The shared layout configuration controls measure width, page padding, staff spacing, grand staff spacing, system spacing, measure numbers, harmony labels, section labels, and fit-width behavior. Fit Width now fits wrapped systems instead of shrinking an entire score into one unreadable row.

The same wrapped geometry feeds fallback rendering, Beat Grid points, enlarged hit areas, Staff Lane highlighting, and Score Cursor overlay positions. This makes visual layout and editing hit maps use the same coordinate contract.

## V0.93 Regression Guard

V0.93 adds hard layout regression checks so a 16-measure score cannot be treated as one compressed row. The evaluation reports wrapped layout success, maximum measures-per-system compliance, first-system readability, and score visibility success. Fit-width is interpreted as fitting each system/page, not shrinking an entire piece into one unreadable line.
