# -*- coding: utf-8 -*-
"""
MobilCV - Dil sayfalari (SEO) olusturucu
-----------------------------------------
mobilcv.com deposunun KOK klasorunde calistirin:
    python seo_dil_sayfalari.py

Yaptiklari:
 1) index.html'i duzeltir (once index.html.yedek olarak yedek alir):
    - Kok sayfa her zaman Turkce acilir (Google'in robotu Ingilizce tarayici
      dilinde gezdigi icin kok sayfa Ingilizceye donup canonical'i ?lang=en
      yapiyordu -> Turkce sayfa indeksten dusebilirdi).
    - Eski ?lang=de gibi linkler otomatik /de/ sayfasina yonlenir.
    - JS artik canonical'i ve sayfa basligini (title) bozmaz.
    - hreflang etiketleri yeni /en/, /de/ ... adreslerine guncellenir.
 2) en, de, fr, es, it, pt, ru, ar, zh klasorlerini olusturur; her birinde
    kendi dilinde title / description / canonical olan index.html bulunur.
 3) Dil adreslerini iceren sitemap dosyasi yazar.

index.html'i ileride degistirirseniz bu scripti tekrar calistirmaniz yeterli.
"""
import re
import shutil
import sys
from pathlib import Path

SITE = "https://www.mobilcv.com"

LANGS = {
    "en": dict(locale="en_US",
        title="Free CV Maker – No Sign-Up, Download as PDF | MobilCV",
        desc="Create a professional CV for free on your phone – no sign-up, no ads. Your data stays in your browser. Download your CV as PDF in minutes.",
        kw="free cv maker, cv builder, resume builder, create cv online, cv template, pdf cv, no sign up"),
    "de": dict(locale="de_DE",
        title="Lebenslauf kostenlos erstellen – ohne Anmeldung, als PDF | MobilCV",
        desc="Erstellen Sie Ihren Lebenslauf kostenlos am Handy – ohne Anmeldung und ohne Werbung. Ihre Daten bleiben im Browser. In wenigen Minuten als PDF herunterladen.",
        kw="lebenslauf erstellen kostenlos, lebenslauf vorlage, lebenslauf pdf, lebenslauf ohne anmeldung, cv erstellen"),
    "fr": dict(locale="fr_FR",
        title="Créer un CV gratuit – sans inscription, en PDF | MobilCV",
        desc="Créez votre CV gratuitement sur votre téléphone, sans inscription ni publicité. Vos données restent dans votre navigateur. Téléchargez-le en PDF en quelques minutes.",
        kw="créer un cv gratuit, cv en ligne, modèle de cv, cv pdf, cv sans inscription"),
    "es": dict(locale="es_ES",
        title="Crear currículum gratis – sin registro, en PDF | MobilCV",
        desc="Crea tu currículum gratis desde el móvil, sin registro y sin anuncios. Tus datos se quedan en tu navegador. Descárgalo en PDF en pocos minutos.",
        kw="crear curriculum gratis, hacer cv online, plantilla de curriculum, cv pdf, curriculum sin registro"),
    "it": dict(locale="it_IT",
        title="Creare un CV gratis – senza registrazione, in PDF | MobilCV",
        desc="Crea il tuo CV gratis dal telefono, senza registrazione e senza pubblicità. I tuoi dati restano nel browser. Scaricalo in PDF in pochi minuti.",
        kw="creare cv gratis, curriculum online, modello cv, cv pdf, cv senza registrazione"),
    "pt": dict(locale="pt_BR",
        title="Criar currículo grátis – sem cadastro, em PDF | MobilCV",
        desc="Crie seu currículo grátis pelo celular, sem cadastro e sem anúncios. Seus dados ficam no seu navegador. Baixe em PDF em poucos minutos.",
        kw="criar curriculo gratis, curriculo online, modelo de curriculo, curriculo pdf, curriculo sem cadastro"),
    "ru": dict(locale="ru_RU",
        title="Создать резюме бесплатно – без регистрации, в PDF | MobilCV",
        desc="Создайте резюме бесплатно прямо с телефона – без регистрации и рекламы. Ваши данные остаются в браузере. Скачайте резюме в PDF за несколько минут.",
        kw="создать резюме бесплатно, конструктор резюме, шаблон резюме, резюме pdf, резюме без регистрации"),
    "ar": dict(locale="ar_AR",
        title="إنشاء سيرة ذاتية مجانًا – بدون تسجيل، بصيغة PDF | MobilCV",
        desc="أنشئ سيرتك الذاتية مجانًا من هاتفك، بدون تسجيل وبدون إعلانات. تبقى بياناتك في متصفحك. حمّلها بصيغة PDF خلال دقائق.",
        kw="إنشاء سيرة ذاتية مجانا, سيرة ذاتية اونلاين, نموذج سيرة ذاتية, سيرة ذاتية pdf"),
    "zh": dict(locale="zh_CN",
        title="免费在线制作简历 – 无需注册，下载PDF | MobilCV",
        desc="用手机免费制作专业简历，无需注册，无广告。您的数据只保存在浏览器中。几分钟即可下载PDF简历。",
        kw="免费制作简历, 在线简历制作, 简历模板, PDF简历, 无需注册"),
}
ALL = ["tr"] + list(LANGS)

PRIVACY = {
    "tr": ("https://mobilcv.net/gizlilik-politikasi.html", "Gizlilik Politikası"),
    "en": ("https://mobilcv.net/en/privacy-policy.html", "Privacy Policy"),
    "de": ("https://mobilcv.net/de/privacy-policy.html", "Datenschutzerklärung"),
    "fr": ("https://mobilcv.net/fr/privacy-policy.html", "Politique de confidentialité"),
    "es": ("https://mobilcv.net/es/privacy-policy.html", "Política de privacidad"),
    "it": ("https://mobilcv.net/it/privacy-policy.html", "Informativa sulla privacy"),
    "pt": ("https://mobilcv.net/pt/privacy-policy.html", "Política de privacidade"),
    "ru": ("https://mobilcv.net/ru/privacy-policy.html", "Политика конфиденциальности"),
    "ar": ("https://mobilcv.net/ar/privacy-policy.html", "سياسة الخصوصية"),
    "zh": ("https://mobilcv.net/zh/privacy-policy.html", "隐私政策"),
}


def privacy_anchor(code):
    url, label = PRIVACY[code]
    return (f'<a href="{url}" data-privacy-link target="_blank" rel="noopener" '
            f'style="display:inline-block;margin-top:8px;font-size:12px;">{label}</a>')


def add_privacy_link(src):
    """Kök sayfanın alt kısmına (blog linkinin altına) gizlilik politikası linki ekler (bir kez)."""
    if "data-privacy-link" in src:
        return src
    m = re.search(r'<footer class="site-footer-link">[\s\S]*?</footer>', src)
    if not m:
        sys.exit("HATA: site-footer-link bulunamadi.")
    block = m.group(0)
    new_block = block.replace("</footer>", "    <br>" + privacy_anchor("tr") + "\n        </footer>")
    return src[:m.start()] + new_block + src[m.end():]


def url_of(code):
    return SITE + "/" if code == "tr" else f"{SITE}/{code}/"


def page_lang_script(code):
    return ("<script>window.MOBILCV_PAGE_LANG='" + code + "';"
            "(function(){var m=location.search.match(/[?&]lang=(en|de|fr|es|it|pt|ru|ar|zh)\\b/);"
            "if(m&&window.MOBILCV_PAGE_LANG==='tr'){location.replace('/'+m[1]+'/');}})();</script>")


HREFLANG = "\n".join(
    [f'    <link rel="alternate" hreflang="{c}" href="{url_of(c)}">' for c in ALL]
    + [f'    <link rel="alternate" hreflang="x-default" href="{url_of("tr")}">']
) + "\n"


def sub_once(pattern, repl, text, name, flags=0):
    new, n = re.subn(pattern, lambda m: repl, text, count=1, flags=flags)
    if n != 1:
        sys.exit(f"HATA: '{name}' bulunamadi. index.html beklenenden farkli; script durduruldu, hicbir dosya degismedi.")
    return new


def patch_root(src):
    if "MOBILCV_PAGE_LANG" in src:
        print("index.html zaten duzeltilmis, sadece dil sayfalari yeniden olusturuluyor.")
        return src
    s = src
    # 1) sayfa dili + eski ?lang yonlendirmesi
    s = sub_once(r"<head>", "<head>\n    " + page_lang_script("tr"), s, "<head>")
    # 2) hreflang blogu
    s = sub_once(r'(?:[ \t]*<link rel="alternate" hreflang="[^"]+" href="[^"]*">\s*\n)+', HREFLANG, s, "hreflang etiketleri")
    # 3) og:locale
    s = sub_once(r'(<meta property="og:site_name" content="MobilCV">)',
                 '<meta property="og:site_name" content="MobilCV">\n    <meta property="og:locale" content="tr_TR">', s, "og:site_name")
    # 4) dil algilama: sayfanin kendi dili
    s = sub_once(re.escape("const detectedLang = getLangFromUrl() || detectBrowserLanguage();"),
                 "const detectedLang = window.MOBILCV_PAGE_LANG || 'tr';", s, "detectedLang")
    # 5) title'i bozmasin
    s = sub_once(re.escape("document.title = translation.pageTitle;"),
                 "window.__seoTitle = window.__seoTitle || document.title;\n"
                 "\t\t\t\tdocument.title = (lang === (window.MOBILCV_PAGE_LANG || 'tr')) ? window.__seoTitle : translation.pageTitle;",
                 s, "document.title")
    # 6) URL'e ?lang ekleme ve canonical degistirme kaldirildi
    s = sub_once(r"const url = new URL\(window\.location\.href\);[\s\S]*?\?lang=\$\{lang\}`\);\s*\}",
                 "// SEO: canonical artik her sayfada sabit (statik HTML), JS degistirmiyor.",
                 s, "canonical/URL blogu")
    # 7) kayitli veri sadece kok sayfada dili degistirsin
    s = sub_once(re.escape("if (data.language && document.getElementById('language-select')) {"),
                 "if (data.language && document.getElementById('language-select') && (window.MOBILCV_PAGE_LANG || 'tr') === 'tr') {",
                 s, "applyData dil")
    return s


def make_lang_page(root, code, d):
    s = root
    u = url_of(code)
    s = sub_once(r"window\.MOBILCV_PAGE_LANG='tr';", f"window.MOBILCV_PAGE_LANG='{code}';", s, "sayfa dili")
    s = sub_once(r'<html lang="tr">', f'<html lang="{code}">', s, "html lang")
    s = sub_once(r"<title>[^<]*</title>", f"<title>{d['title']}</title>", s, "title")
    s = sub_once(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{d["desc"]}">', s, "description")
    s = sub_once(r'<meta name="keywords" content="[^"]*">', f'<meta name="keywords" content="{d["kw"]}">', s, "keywords")
    for prop, val in [("og:url", u), ("og:title", d["title"]), ("og:description", d["desc"]), ("og:locale", d["locale"])]:
        s = sub_once(rf'<meta property="{prop}" content="[^"]*">', f'<meta property="{prop}" content="{val}">', s, prop)
    for prop, val in [("twitter:url", u), ("twitter:title", d["title"]), ("twitter:description", d["desc"])]:
        s = sub_once(rf'<meta name="{prop}" content="[^"]*">', f'<meta name="{prop}" content="{val}">', s, prop)
    s = sub_once(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{u}">', s, "canonical")
    s = re.sub(r'<a href="[^"]*" data-privacy-link[^>]*>[^<]*</a>', lambda m: privacy_anchor(code), s)
    # Sayfa altındaki blog linki o dilin bloguna gitsin (ör. https://mobilcv.net/de/)
    s = re.sub(r'href="https://mobilcv\.net/?"', f'href="https://mobilcv.net/{code}/"', s)
    name = "MobilCV – " + d["title"].split(" | ")[0]
    s = sub_once(r'"name": "MobilCV - Ücretsiz Online CV Oluşturucu"', f'"name": "{name}"', s, "JSON-LD name")
    s = sub_once(r'"description": "10 dil desteği ile[^"]*"', f'"description": "{d["desc"]}"', s, "JSON-LD description")
    s = sub_once(r'"url": "https://www\.mobilcv\.com",', f'"url": "{u}",', s, "JSON-LD url")
    # Turkce SSS (FAQ) yapilandirilmis verisi diger dillerde kaldirilir
    s = sub_once(r'\s*<script type="application/ld\+json">\s*\{\s*"@context": "https://schema\.org",\s*"@type": "FAQPage"[\s\S]*?</script>',
                 "", s, "FAQ JSON-LD")
    return s


def sitemap():
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{c}" href="{url_of(c)}"/>' for c in ALL)
    alts += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{url_of("tr")}"/>'
    for c in ALL:
        lines.append(f"  <url>\n    <loc>{url_of(c)}</loc>{alts}\n  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main():
    p = Path("index.html")
    if not p.exists():
        sys.exit("HATA: index.html bulunamadi. Scripti mobilcv.com deposunun kok klasorunde calistirin.")
    src = p.read_text(encoding="utf-8")
    root = add_privacy_link(patch_root(src))
    pages = {c: make_lang_page(root, c, d) for c, d in LANGS.items()}  # once hepsini hazirla, hata varsa hicbir sey yazilmaz

    if root != src:
        shutil.copy(p, "index.html.yedek")
        p.write_text(root, encoding="utf-8")
        print("index.html duzeltildi (yedek: index.html.yedek)")
    for c, html in pages.items():
        Path(c).mkdir(exist_ok=True)
        (Path(c) / "index.html").write_text(html, encoding="utf-8")
        print(f"{c}/index.html olusturuldu  ->  {url_of(c)}")

    target = Path("sitemap.xml")
    if target.exists():
        target = Path("sitemap-diller.xml")
    target.write_text(sitemap(), encoding="utf-8")
    print(f"{target} yazildi.")
    print("\nTAMAM. Simdi degisiklikleri GitHub'a gonderin (commit + push).")


if __name__ == "__main__":
    main()
