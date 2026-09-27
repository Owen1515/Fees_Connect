# FeesConnect brand implementation

| Role | Colour | Usage |
| --- | --- | --- |
| Emerald | `#0DA35A` | F / Fees identity and brand accents |
| Lime | `#9ACB47` | C / Connect identity, highlighted headings and calls to action |
| Evergreen | `#063D2E` | Hero panels, dark surfaces and text on lime |
| Accessible action green | `#087343` | Primary buttons, form links and controls on light surfaces |

The generated logo contains slight pixel-level tonal variation. These solid interface colours are sampled representative shades. Original artwork is at `feesconnect/public/assets/feesconnect-logo.png`, with an identical copy in `travold/assets/`. The logo is an approved raster PNG, not an editable vector master. The favicon SVG embeds the original PNG and selects the symbol area; it does not recreate the mark.

The logo's Fees and Connect lettering retain their approved colours. Other interface text uses darker shades where necessary for readable contrast. White on action green is 5.93:1; evergreen on lime is 6.42:1; white on evergreen is 12.25:1. These checked pairs exceed 4.5:1 for normal-sized text; this is not a claim of a complete accessibility audit.

Preserve the lockup proportions. CSS displays the supplied artwork through an overflow window to remove excess visual padding without editing its pixels. Small-screen header navigation wraps below the logo. Avoid applying filters, stretching, recolouring or recreating the FC symbol.
