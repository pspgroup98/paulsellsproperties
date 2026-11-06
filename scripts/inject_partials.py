#!/usr/bin/env python3
"""
inject_partials.py
Stamps _partials/nav.html and _partials/footer.html into all site HTML pages.
Also migrates inline nav JS to <script src="nav.js"> references (one-time).

Usage:
  python3 scripts/inject_partials.py            # apply changes
  python3 scripts/inject_partials.py --dry-run  # preview without writing
"""

import re
import sys
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DRY_RUN = '--dry-run' in sys.argv

NAV_PARTIAL    = (ROOT / '_partials/nav.html').read_text(encoding='utf-8')
FOOTER_PARTIAL = (ROOT / '_partials/footer.html').read_text(encoding='utf-8')

# Pages to skip by filename (prototypes/previews without standard nav/footer)
SKIP_NAMES = {'nhd-carousel-prototype.html', 'phase-1.html'}

# Root index.html has a unique multi-section structure (IntersectionObserver, carousels, etc.)
# and is managed via direct edits rather than this script.
SKIP_PATHS = {ROOT / 'index.html'}

# ── Helpers ───────────────────────────────────────────────────────────────────

def depth_prefix(path: Path) -> str:
    """'assets/' for root pages, '../assets/' for one subdirectory deep."""
    rel = path.relative_to(ROOT)
    depth = len(rel.parts) - 1
    return ('../' * depth + 'assets/') if depth > 0 else 'assets/'


def find_div_end(html: str, start: int) -> int:
    """Return index just after the closing </div> for the div starting at start."""
    depth = 0
    i = start
    while i < len(html):
        if html[i:i+4] == '<div':
            depth += 1
        elif html[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                return i + 6
        i += 1
    return -1


# ── Helper: find start of block, including all preceding comment lines ────────

def block_start_with_comment(html: str, tag_pos: int) -> int:
    """Walk backwards through consecutive comment lines before tag_pos."""
    pos = tag_pos
    while True:
        line_start = html.rfind('\n', 0, pos)
        # Ensure the element at pos is at the start of its line
        if line_start == -1 or html[line_start + 1:pos].strip():
            break
        prev_line_end   = line_start
        prev_line_start = html.rfind('\n', 0, prev_line_end)
        prev_line       = html[prev_line_start + 1:prev_line_end]
        if re.match(r'\s*<!--.*?-->\s*$', prev_line):
            pos = prev_line_start + 1   # include this comment and keep walking
        else:
            break
    return pos


# ── Nav block injection ───────────────────────────────────────────────────────

def inject_nav(html: str) -> tuple:
    header_pos = html.find('<header class="psp-nav"')
    if header_pos == -1:
        return html, False

    block_start = block_start_with_comment(html, header_pos)

    # Find the mobile-menu div and its closing tag
    mobile_start = html.find('<div class="psp-mobile-menu"', header_pos)
    if mobile_start == -1:
        return html, False
    mobile_end = find_div_end(html, mobile_start)
    if mobile_end == -1:
        return html, False

    # Consume one trailing newline so replacement slots in cleanly
    block_end = mobile_end
    if block_end < len(html) and html[block_end] == '\n':
        block_end += 1

    existing  = html[block_start:block_end]
    canonical = '<!-- NAV -->\n' + NAV_PARTIAL.rstrip('\n') + '\n'

    if existing == canonical:
        return html, False
    return html[:block_start] + canonical + html[block_end:], True


# ── Footer block injection ────────────────────────────────────────────────────

def inject_footer(html: str) -> tuple:
    footer_pos = html.find('<footer class="footer">')
    if footer_pos == -1:
        return html, False

    block_start = block_start_with_comment(html, footer_pos)

    footer_end = html.find('</footer>', footer_pos)
    if footer_end == -1:
        return html, False
    block_end = footer_end + len('</footer>')
    if block_end < len(html) and html[block_end] == '\n':
        block_end += 1

    existing  = html[block_start:block_end]
    canonical = '<!-- FOOTER -->\n' + FOOTER_PARTIAL.rstrip('\n') + '\n'

    if existing == canonical:
        return html, False
    return html[:block_start] + canonical + html[block_end:], True


# ── Nav JS migration ──────────────────────────────────────────────────────────

# Inner page: <script> block with the combined nav+mobile IIFE
INNER_NAV_SCRIPT_RE = re.compile(
    r'<script>\n//[^\n]*Nav[^\n]*mobile menu[^\n]*\n.*?</script>',
    re.DOTALL
)

# index.html: separate mobile-menu <script> block after the main scripts
INDEX_MOBILE_SCRIPT_RE = re.compile(
    r'<!-- Mobile menu.*?-->\n<script>\n.*?</script>',
    re.DOTALL
)


def inject_nav_js(html: str, path: Path) -> tuple:
    # Already migrated to nav.js — nothing to do
    if 'nav.js' in html:
        return html, False

    prefix = depth_prefix(path)
    tag    = f'<script src="{prefix}js/nav.js" defer></script>\n'

    if path == ROOT / 'index.html':
        m = INDEX_MOBILE_SCRIPT_RE.search(html)
        if m:
            return html[:m.start()] + tag + html[m.end():], True
        return html, False

    m = INNER_NAV_SCRIPT_RE.search(html)
    if m:
        return html[:m.start()] + tag + html[m.end():], True

    # Page has nav HTML but no inline nav IIFE — inject tag before </body>
    if '<header class="psp-nav"' in html:
        body_end = html.rfind('</body>')
        if body_end != -1:
            return html[:body_end] + tag + html[body_end:], True

    return html, False


# ── Process one file ──────────────────────────────────────────────────────────

def process_file(path: Path) -> None:
    html    = path.read_text(encoding='utf-8')
    changed = False
    parts   = []

    html, c = inject_nav(html)
    if c:
        changed = True
        parts.append('nav')

    html, c = inject_footer(html)
    if c:
        changed = True
        parts.append('footer')

    html, c = inject_nav_js(html, path)
    if c:
        changed = True
        parts.append('nav.js')

    rel = path.relative_to(ROOT)
    if changed:
        tag = 'DRY-RUN' if DRY_RUN else 'UPDATED'
        print(f'  {tag}  {rel}  [{", ".join(parts)}]')
        if not DRY_RUN:
            path.write_text(html, encoding='utf-8')
    else:
        print(f'  OK       {rel}')


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    pages = sorted(
        p for p in ROOT.rglob('*.html')
        if '.git'            not in p.parts
        and 'node_modules'   not in p.parts
        and 'design-references' not in p.parts
        and '_partials'      not in p.parts
        and p.name           not in SKIP_NAMES
        and p                not in SKIP_PATHS
    )

    mode = 'DRY-RUN — ' if DRY_RUN else ''
    print(f'{mode}Injecting partials into {len(pages)} HTML files...\n')
    for p in pages:
        process_file(p)
    print('\nDone.')


if __name__ == '__main__':
    main()
