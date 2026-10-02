#!/usr/bin/env python3
"""Собирает одну страницу с двумя вкладками (рулетка и гайды) из index.html и guides.html.

Результат: dist/artifact.html (для публикации) и dist/app.html (для проверки), все данные (icons.js, guides.js, heroes.js) вшиты внутрь.
Запуск: python3 build.py
"""
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


def split_css(css):
    """Делит CSS на правила верхнего уровня: [(селектор, тело)]. Комментарии сохраняются как ('', текст)."""
    out, i, n = [], 0, len(css)
    while i < n:
        if css[i].isspace():
            i += 1
            continue
        if css.startswith("/*", i):
            j = css.index("*/", i) + 2
            out.append(("", css[i:j]))
            i = j
            continue
        j = css.index("{", i)
        sel = css[i:j].strip()
        depth, k = 1, j + 1
        while depth:
            if css.startswith("/*", k):
                k = css.index("*/", k) + 2
                continue
            c = css[k]
            depth += c == "{"
            depth -= c == "}"
            k += 1
        out.append((sel, css[j + 1:k - 1]))
        i = k
    return out


GLOBAL_SELECTORS = {":root", "*", "html", "body", "html, body"}


def scope_css(css, container, keep_global):
    """Правила :root, *, html, body остаются глобальными, остальное вкладывается в #container (CSS nesting)."""
    glob, scoped = [], []
    for sel, body in split_css(css):
        if sel == "":
            continue
        if sel in GLOBAL_SELECTORS:
            if keep_global:
                glob.append(f"{sel} {{{body}}}")
            continue
        scoped.append(f"{sel} {{{body}}}")
    return "\n".join(glob), f"#{container} {{\n" + "\n".join(scoped) + "\n}"


def between(text, start, end):
    a = text.index(start) + len(start)
    return text[a:text.index(end, a)]


def last_inline_script(text):
    scripts = re.findall(r"<script>\n(.*?)</script>", text, re.S)
    return scripts[-1]


def main():
    index, guides, rnd, cnt, cmb = read("src/roulette.html"), read("src/guides.html"), read("src/random.html"), read("src/counters.html"), read("src/combos.html")
    icons, gjs, heroes, mu, syn = read("icons.js"), read("guides.js"), read("heroes.js"), read("matchups.js"), read("synergy.js")

    # --- стили ---
    css_r = between(index, "<style>", "</style>")
    css_g = between(guides, "<style>", "</style>")
    glob_r, scoped_r = scope_css(css_r, "viewRoulette", True)
    _, scoped_g = scope_css(css_g, "viewGuides, #viewRandom, #viewCounters, #viewCombos", False)  # гайд на вкладке рандома оформляется теми же стилями
    css_x = between(rnd, "<style>", "</style>")
    _, scoped_x = scope_css(css_x, "viewRandom", False)
    html_x = between(rnd, "</style>\n", "<script>")
    js_x = between(rnd, "<script>\n", "</script>")
    _, scoped_c = scope_css(between(cnt, "<style>", "</style>"), "viewCounters", False)
    html_c = between(cnt, "</style>\n", "<script>")
    js_c = between(cnt, "<script>\n", "</script>")
    _, scoped_k = scope_css(between(cmb, "<style>", "</style>"), "viewCombos", False)
    html_k = between(cmb, "</style>\n", "<script>")
    js_k = between(cmb, "<script>\n", "</script>")
    extra = """
.topnav { position: sticky; top: env(safe-area-inset-top, 0px); z-index: 20; background: var(--bg); margin-inline: -16px; padding: 10px 16px; border-bottom: 1px solid var(--line); display: flex; gap: 8px; flex-wrap: wrap; }
.nav-tab { font: inherit; cursor: pointer; background: var(--panel-2); color: var(--muted); border: 1px solid var(--line); border-radius: 4px; padding: 8px 16px; font-weight: 700; }
.nav-tab[aria-pressed="true"] { background: var(--gold); border-color: var(--gold); color: var(--on-gold); }
.nav-tab:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
#viewRoulette, #viewGuides, #viewRandom, #viewCounters, #viewCombos { padding-top: 20px; }
.linkbtn { background: none; border: 0; padding: 0; color: var(--gold); text-decoration: underline; cursor: pointer; font: inherit; text-align: left; }
"""
    # --- разметка ---
    html_r = between(index, "<body>\n", '<script src="icons.js"></script>')
    html_g = between(guides, "<body>\n", '<script src="heroes.js"></script>')
    html_r = re.sub(r'\s*<a class="btn-link" href="https://claude\.ai/artifact/[^"]*"[^>]*>Гайды героев</a>', "", html_r)
    html_g = re.sub(r'\s*<a class="btn-link" id="back"[^>]*>[^<]*</a>', "", html_g)

    # --- скрипты ---
    js_r, js_g = last_inline_script(index), last_inline_script(guides)
    old_link = re.search(r'      const a = mk\("a", "", `Показан основной билд.*?a\.className = "g-note";\n', js_r, re.S)
    assert old_link, "блок ссылки на гайды не найден"
    js_r = js_r.replace(old_link.group(0), '''      const a = mk("button", "linkbtn", `Показан основной билд, всего вариантов: ${gp.vn}. Все варианты в гайдах героев.`);
      a.type = "button";
      a.addEventListener("click", () => window.openGuideByName && window.openGuideByName(p.hero[0]));
''')
    assert "document.body.appendChild(d)" in js_r
    js_r = js_r.replace("document.body.appendChild(d)", 'document.getElementById("viewRoulette").appendChild(d)')
    assert 'history.replaceState(null, "", "#" + k)' in js_g
    js_g = js_g.replace('history.replaceState(null, "", "#" + k)', 'history.replaceState(null, "", "#g-" + k)')
    js_g = js_g.replace('const fromHash = (location.hash || "").slice(1);', 'const fromHash = (location.hash || "").startsWith("#g-") ? location.hash.slice(3) : "";')
    js_g = js_g.replace('  document.getElementById("rand").addEventListener', '  window.__selectGuide = name => { const h = heroes.find(x => x.n === name); if (h) select(h.k, true); };\n  window.__selectGuideKey = k => { if (byKey[k]) select(k, false); };\n  window.__renderGuideInto = (h, target, pi, vi) => renderGuide(h, target, pi, vi);\n  document.getElementById("rand").addEventListener')
    assert "__selectGuide" in js_g
    nav_js = '''(() => {
  const views = { roulette: document.getElementById("viewRoulette"), guides: document.getElementById("viewGuides"), random: document.getElementById("viewRandom"), counters: document.getElementById("viewCounters"), combos: document.getElementById("viewCombos") };
  const tabs = document.querySelectorAll(".nav-tab");
  function showView(v, top) {
    Object.entries(views).forEach(([k, el]) => { el.hidden = k !== v; });
    tabs.forEach(t => t.setAttribute("aria-pressed", String(t.dataset.view === v)));
    if (top) window.scrollTo(0, 0);
    if (v === "random" && window.__rollHeroFirst) window.__rollHeroFirst();
    if (v === "combos" && window.__combosInit) window.__combosInit();
    try { if (v === "roulette") history.replaceState(null, "", "#roulette"); else if (v === "random") history.replaceState(null, "", "#random"); else if (v === "combos") history.replaceState(null, "", "#combos"); else if (v === "counters") { if (!location.hash.startsWith("#c-")) history.replaceState(null, "", "#counters"); } else if (!location.hash.startsWith("#g-")) history.replaceState(null, "", "#guides"); } catch {}
  }
  tabs.forEach(t => t.addEventListener("click", () => showView(t.dataset.view, true)));
  window.openGuideByName = name => { showView("guides", false); if (window.__selectGuide) window.__selectGuide(name); window.scrollTo(0, 0); };
  window.addEventListener("hashchange", () => {
    if (location.hash.startsWith("#g-")) { showView("guides", false); if (window.__selectGuideKey) window.__selectGuideKey(location.hash.slice(3)); }
    else if (location.hash === "#guides") showView("guides", false);
    else if (location.hash === "#roulette") showView("roulette", false);
    else if (location.hash === "#random") showView("random", false);
    else if (location.hash.startsWith("#c-")) { showView("counters", false); if (window.__selectCounterKey) window.__selectCounterKey(location.hash.slice(3)); }
    else if (location.hash === "#counters") showView("counters", false);
    else if (location.hash === "#combos") showView("combos", false);
  });
  showView(/^#(g-|guides)/.test(location.hash) ? "guides" : location.hash === "#random" ? "random" : /^#(c-|counters)/.test(location.hash) ? "counters" : location.hash === "#combos" ? "combos" : "roulette", false);
})();'''
    def compose(inline):
        data = (f'<script>\n{icons}</script>\n<script>\n{gjs}</script>\n<script>\n{heroes}</script>\n<script>\n{mu}</script>\n<script>\n{syn}</script>\n' if inline
                else '<script src="icons.js"></script>\n<script src="guides.js"></script>\n<script src="heroes.js"></script>\n<script src="matchups.js"></script>\n<script src="synergy.js"></script>\n')
        return f'''<title>Дота Рулетка</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Forum&family=Fira+Sans:wght@400;500;700&display=swap">
<style>
{glob_r}
{extra}
{scoped_r}
{scoped_g}
{scoped_x}
{scoped_c}
{scoped_k}
</style>
<nav class="topnav" aria-label="Разделы">
  <button type="button" class="nav-tab" data-view="roulette" aria-pressed="true">Рулетка героев</button>
  <button type="button" class="nav-tab" data-view="guides" aria-pressed="false">Гайды героев</button>
  <button type="button" class="nav-tab" data-view="random" aria-pressed="false">Рандом героя</button>
  <button type="button" class="nav-tab" data-view="counters" aria-pressed="false">Контрпики</button>
  <button type="button" class="nav-tab" data-view="combos" aria-pressed="false">Связки</button>
</nav>
<div id="viewRoulette">
{html_r}</div>
<div id="viewGuides" hidden>
{html_g}</div>
<div id="viewRandom" hidden>
{html_x}</div>
<div id="viewCounters" hidden>
{html_c}</div>
<div id="viewCombos" hidden>
{html_k}</div>
{data}<script>
{js_r}</script>
<script>
{js_g}</script>
<script>
{js_x}</script>
<script>
{js_c}</script>
<script>
{js_k}</script>
<script>
{nav_js}
</script>
'''
    def wrap(page, full):
        if not full:
            return page  # фрагмент: служебную обёртку добавляет сервис публикации
        i = page.index('<nav class="topnav"')
        return ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + page[:i] + '</head>\n<body>\n' + page[i:] + '</body>\n</html>\n')

    index_html = wrap(compose(False), True)
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    artifact = wrap(compose(True), False)
    with open(os.path.join(ROOT, "dist", "artifact.html"), "w", encoding="utf-8") as f:
        f.write(artifact)
    print("index.html", len(index_html) // 1024, "KB;", "dist/artifact.html", len(artifact) // 1024, "KB")


if __name__ == "__main__":
    main()
