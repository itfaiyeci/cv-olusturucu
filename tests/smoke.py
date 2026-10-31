# -*- coding: utf-8 -*-
"""MobilCV otomatik islev testi (GitHub Actions ve yerel).
Kullanim: python3 tests/smoke.py http://localhost:8000/
Kontroller:
  - 11 dil x (telefon, bilgisayar): sayfa aciliyor, JavaScript hatasi yok, dil dogru, sablon secici var
  - TR / EN / AR / JA: 4 sablonun her biriyle ornek CV doldurulup PDF gercekten uretiliyor
  - Japonca: bos referans telefonu PDF'e ornek numara olarak gitmiyor (gecmis hata)
  - US Letter: kagit secenegiyle PDF 215.9 x 279.4 mm uretiliyor
  - CV'lerim kopya olusturuyor; Ilana gore kontrol SAP/SGK gibi eksikleri buluyor
  - Yedegi Yukle: yedekte bos olan alan formdaki eski metni siliyor
  - Word (.docx): gecerli dosya, icerik ve A4/Letter sayfa boyutu
  - On yazi: CV'den taslak, Word ve PDF (A4/Letter)
Hata varsa cikis kodu 1. Ozet GITHUB_STEP_SUMMARY'ye yazilir."""
import json, os, sys, time
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/").rstrip("/") + "/"
LANGS = ["", "en", "de", "fr", "es", "it", "pt", "ru", "ar", "zh", "ja"]
TEMPLATES = ["", "tpl-classic", "tpl-top", "tpl-rirekisho"]
SAMPLE = {
    "personalInfo": {"fullname": "Test Kişi", "profession": "Test Uzmanı", "phone": "5321234567",
                     "email": "test@example.com", "address": "İstanbul"},
    "about": "Otomatik test için örnek metin.",
    "experience": [{"title": "Uzman", "company": "Örnek Şirket", "duration": "2019 - Halen", "description": "Örnek görev."}],
    "education": [{"institution": "Örnek Üniversite", "date": "2015-2019"}],
    "skills": ["Excel", "İletişim"],
    "languages": [{"name": "Türkçe", "level": "Ana dil"}],
}
INIT = "try{localStorage.setItem('popupShown','true');localStorage.setItem('mobilcv_consent','denied')}catch(e){}"
fails, rows = [], []


LOCAL_LIBS = os.environ.get("LOCAL_LIBS")  # yalnizca yerel calistirma: CDN kutuphaneleri diskten


def block_tracking(route):
    u = route.request.url
    if LOCAL_LIBS and not u.startswith(BASE[:16]):
        for k, v in (("jspdf.umd.min.js", "jspdf/dist/jspdf.umd.min.js"), ("html2canvas.min.js", "html2canvas/dist/html2canvas.min.js")):
            if u.endswith(k):
                return route.fulfill(path=os.path.join(LOCAL_LIBS, v), content_type="application/javascript")
        return route.abort()
    if any(x in u for x in ("googletagmanager.com", "google-analytics.com", "doubleclick.net")):
        return route.abort()
    return route.continue_()


def new_page(browser, mobile):
    vp = {"width": 390, "height": 844} if mobile else {"width": 1280, "height": 900}
    ctx = browser.new_context(viewport=vp, is_mobile=mobile, has_touch=mobile)
    ctx.add_init_script(INIT)
    ctx.route("**/*", block_tracking)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    return ctx, pg, errs


def check(name, ok, detail=""):
    rows.append(("✅" if ok else "❌", name, detail))
    if not ok:
        fails.append(f"{name}: {detail}")


with sync_playwright() as pw:
    b = pw.chromium.launch()
    # 1) Sayfalar
    for lang in LANGS:
        for mobile in (False, True):
            ctx, pg, errs = new_page(b, mobile)
            name = f"{lang or 'tr'} {'telefon' if mobile else 'bilgisayar'}"
            try:
                r = pg.goto(BASE + (lang + "/" if lang else ""), wait_until="load", timeout=60000)
                time.sleep(1.5)
                info = pg.evaluate("""() => ({lang: document.documentElement.lang,
                    sel: !!document.getElementById('template-select'),
                    title: document.title.length,
                    wide: document.documentElement.scrollWidth})""")
                ok = r.status == 200 and not errs and info["sel"] and info["title"] > 0 and info["lang"].startswith(lang or "tr")
                check("Sayfa " + name, ok, f"HTTP {r.status}, dil={info['lang']}, hata={errs[:2]}")
            except Exception as ex:
                check("Sayfa " + name, False, str(ex)[:200])
            ctx.close()
    # 2) PDF uretimi
    for lang in ("", "en", "ar", "ja"):
        for tpl in TEMPLATES:
            ctx, pg, errs = new_page(b, False)
            name = f"PDF {lang or 'tr'} / {tpl or 'modern'}"
            try:
                pg.goto(BASE + (lang + "/" if lang else ""), wait_until="load", timeout=60000)
                time.sleep(1.2)
                pg.evaluate("d => autoSaveManager.applyData(d)", SAMPLE)
                time.sleep(0.5)
                pg.evaluate("t => window.applyCvTemplate && window.applyCvTemplate(t)", tpl)
                time.sleep(0.6)
                res = pg.evaluate("""() => generateCvPdf().then(d => ({pages: d.getNumberOfPages(),
                    size: d.output('arraybuffer').byteLength}))""")
                ok = res["pages"] >= 1 and res["size"] > 10000 and not errs
                check(name, ok, f"{res['pages']} sayfa, {res['size'] // 1024} KB, hata={errs[:2]}")
            except Exception as ex:
                check(name, False, str(ex)[:200])
            ctx.close()
    # 2b) US Letter kagit secenegi: PDF 215.9 x 279.4 mm, metin katmani var
    for lang in ("", "en"):
        for tpl in ("", "tpl-classic"):
            ctx, pg, errs = new_page(b, False)
            name = f"PDF Letter {lang or 'tr'} / {tpl or 'modern'}"
            try:
                pg.goto(BASE + (lang + "/" if lang else ""), wait_until="load", timeout=60000)
                time.sleep(1.2)
                pg.evaluate("d => autoSaveManager.applyData(d)", SAMPLE)
                time.sleep(0.5)
                pg.evaluate("t => window.applyCvTemplate && window.applyCvTemplate(t)", tpl)
                pg.click("#paper-btn-letter")
                time.sleep(0.6)
                res = pg.evaluate("""() => generateCvPdf().then(d => ({pages: d.getNumberOfPages(),
                    w: d.internal.pageSize.getWidth(), h: d.internal.pageSize.getHeight(),
                    size: d.output('arraybuffer').byteLength}))""")
                ok = abs(res["w"] - 215.9) < 0.5 and abs(res["h"] - 279.4) < 0.5 and res["size"] > 10000 and not errs
                check(name, ok, f"{res['w']:.1f}x{res['h']:.1f} mm, {res['pages']} sayfa, {res['size'] // 1024} KB, hata={errs[:2]}")
            except Exception as ex:
                check(name, False, str(ex)[:200])
            ctx.close()
    # 2c) CV'lerim (kopya) ve Ilana gore kontrol
    ctx, pg, errs = new_page(b, False)
    try:
        pg.goto(BASE, wait_until="load", timeout=60000); time.sleep(1.2)
        pg.evaluate("d => autoSaveManager.applyData(d)", SAMPLE); time.sleep(0.5)
        pg.click("#mcv-cvlerim-btn"); time.sleep(0.3); pg.click("#mcv-kopyala"); time.sleep(0.3)
        n = pg.evaluate("JSON.parse(localStorage.getItem('mobilcv_surumler')||'{\"liste\":[]}').liste.length")
        check("CV'lerim: kopya oluşturma", n == 2 and not errs, f"{n} CV, hata={errs[:2]}")
        r = pg.evaluate("""() => mcvIlanAnaliz('Muhasebe uzmanı aranıyor. SAP ve Excel bilen, SGK ve bordro işlemlerine hakim, ' +
            'e-fatura süreçlerini bilen, raporlama yetkinliği yüksek, İngilizce bilen adaylar tercih edilecektir. SAP bilgisi tercih sebebidir.')""")
        eksik = [x["asil"] for x in r.get("eksik", [])]
        check("İlana göre kontrol", r["durum"] == "tamam" and "SAP" in eksik and "SGK" in eksik and "Excel" not in eksik and not errs, f"{eksik[:8]}")
    except Exception as ex:
        check("CV'lerim / ilan kontrolü", False, str(ex)[:200])
    ctx.close()
    # 2d) Yedegi Yukle: yedekte bos olan alan formdaki eski degeri silmeli (gecmis hata)
    ctx, pg, errs = new_page(b, False)
    try:
        import tempfile
        pg.goto(BASE, wait_until="load", timeout=60000); time.sleep(1.2)
        pg.evaluate("d => autoSaveManager.applyData(d)", SAMPLE); time.sleep(0.5)
        yedek = dict(SAMPLE); yedek["about"] = ""; yedek["personalInfo"] = dict(SAMPLE["personalInfo"], fullname="Yedek Kişi")
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8"); json.dump(yedek, f, ensure_ascii=False); f.close()
        with pg.expect_navigation(timeout=15000):
            pg.set_input_files("#import-data-input", f.name)
        pg.wait_for_load_state("load"); time.sleep(1.5)
        d = pg.evaluate("autoSaveManager.collectData()")
        ok = d["personalInfo"].get("fullname") == "Yedek Kişi" and not (d.get("about") or "").strip() and not errs
        check("Yedeği Yükle: boş alan eski metni silir", ok, f"ad={d['personalInfo'].get('fullname')}, hakkımda={d.get('about')!r}, hata={errs[:2]}")
    except Exception as ex:
        check("Yedeği Yükle", False, str(ex)[:200])
    ctx.close()
    # 2e) Word (.docx) ciktisi: gecerli ZIP, icerik ve A4/Letter sayfa boyutu
    import io, zipfile, re as _re
    for kagit, gen in (("a4", "11906"), ("letter", "12240")):
        ctx, pg, errs = new_page(b, False)
        try:
            pg.goto(BASE, wait_until="load", timeout=60000); time.sleep(1.2)
            pg.evaluate("d => autoSaveManager.applyData(d)", SAMPLE); time.sleep(0.5)
            pg.evaluate("p => applyCvPaper(p, false)", kagit)
            z = zipfile.ZipFile(io.BytesIO(bytes(pg.evaluate("() => Array.from(mcvDocx())"))))
            belge = z.read("word/document.xml").decode("utf-8")
            ok = z.testzip() is None and "Test Kişi" in belge and "Örnek Şirket" in belge and f'w:w="{gen}"' in belge and not errs
            check(f"Word (.docx) {kagit}", ok, f"{len(z.namelist())} parça, hata={errs[:2]}")
        except Exception as ex:
            check(f"Word (.docx) {kagit}", False, str(ex)[:200])
        ctx.close()
    # 2f) On yazi: CV'den taslak, Word ve PDF
    for lang, kagit in (("", "a4"), ("en", "letter")):
        ctx, pg, errs = new_page(b, False)
        try:
            pg.goto(BASE + (lang + "/" if lang else ""), wait_until="load", timeout=60000); time.sleep(1.2)
            pg.evaluate("d => autoSaveManager.applyData(d)", SAMPLE); time.sleep(0.5)
            pg.evaluate("p => applyCvPaper(p, false)", kagit)
            pg.click("#mcv-onyazi-btn"); time.sleep(0.3)
            pg.fill("#mcv-oy-sirket", "Deneme Holding"); pg.fill("#mcv-oy-pozisyon", "Analist")
            pg.click("#mcv-oy-taslak"); time.sleep(0.6)
            metin = pg.input_value("#mcv-oy-metin")
            z = zipfile.ZipFile(io.BytesIO(bytes(pg.evaluate("() => Array.from(mcvOnYazi.docx())"))))
            belge = z.read("word/document.xml").decode("utf-8")
            res = pg.evaluate("() => mcvOnYazi.pdf().then(d => ({pages: d.getNumberOfPages(), w: d.internal.pageSize.getWidth(), size: d.output('arraybuffer').byteLength}))")
            gen = 215.9 if kagit == "letter" else 210.0
            ok = ("Deneme Holding" in metin and "Örnek Şirket" in metin and "Test Kişi" in belge and "Deneme Holding" in belge
                  and abs(res["w"] - gen) < 0.5 and res["pages"] == 1 and res["size"] > 10000 and not errs)
            check(f"Ön yazı {lang or 'tr'} {kagit}", ok, f"PDF {res['w']:.1f} mm, {res['pages']} sayfa, {res['size'] // 1024} KB, hata={errs[:2]}")
        except Exception as ex:
            check(f"Ön yazı {lang or 'tr'} {kagit}", False, str(ex)[:200])
        ctx.close()
    # 3) Gecmis hata: Japoncada ornek referans telefonu
    ctx, pg, errs = new_page(b, False)
    try:
        pg.goto(BASE, wait_until="load"); time.sleep(1)
        pg.select_option("#language-select", "ja"); time.sleep(0.8)
        st = pg.evaluate("""() => { const e = document.querySelector('#references-section .reference-phone');
            return e ? [e.textContent.trim(), e.classList.contains('empty-field')] : ['', true]; }""")
        check("Japonca boş referans telefonu", st[1], f"metin={st[0]!r}")
    except Exception as ex:
        check("Japonca boş referans telefonu", False, str(ex)[:200])
    ctx.close()
    b.close()

summary = ["## MobilCV işlev testi", "", f"Toplam {len(rows)} kontrol, **{len(fails)} hata**", "",
           "| | Kontrol | Ayrıntı |", "|---|---|---|"] + [f"| {a} | {n} | {d} |" for a, n, d in rows]
text = "\n".join(summary)
print(text)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
        f.write(text + "\n")
sys.exit(1 if fails else 0)
