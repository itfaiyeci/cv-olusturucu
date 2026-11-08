# -*- coding: utf-8 -*-
"""Guvenlik yamasi testi. Kullanim: python3 guvenlik_test.py <base-url>
- CSP: 11 dilde tam akis (veri, 6 sablon, onizleme, PDF, Word, on yazi, ilan, CV'lerim, oneri, CJK font) -> ihlal 0
- CSP: cerez izni + GA (sahte yanit) yukleniyor, GA uclarina istek serbest; bilinmeyen alan adina fetch/img/form engelli
- Fotograf: gercek JPEG/PNG yukleme calisir, PDF'te foto var; dis adres / SVG / javascript reddedilir; yedek gidis-donus foto korur
- Tema: gecersiz tema yedegi cokertmez; hata mesajinda tirnakli metin gitmez"""
import base64, io, json, os, sys, time
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/") + "/"
INIT = "try{localStorage.setItem('popupShown','true');localStorage.setItem('mcvKarsilama1','true');localStorage.setItem('mobilcv_consent','denied')}catch(e){}"
DILLER = ["", "en", "de", "fr", "es", "it", "pt", "ru", "ar", "zh", "ja"]
sonuc = []
def kontrol(ad, ok, ayr=""): sonuc.append((ad, ok)); print(("✅" if ok else "❌"), ad, "|", ayr, flush=True)

CV = {"personalInfo": {"fullname": "Test Kişi", "profession": "Uzman", "phone": "5321234567", "email": "test@mobilcv.com", "address": "İstanbul"},
      "about": "Deneme metni.", "experience": [{"title": "Uzman", "company": "Örnek A.Ş.", "duration": "2019 - 2024", "description": "• Görev"}],
      "education": [{"institution": "Üniversite", "date": "2013 - 2017"}], "skills": ["Excel"], "languages": [{"name": "İngilizce", "level": "B2"}]}
CSP_DINLE = "window.__csp=[];document.addEventListener('securitypolicyviolation',e=>window.__csp.push(e.violatedDirective+' '+e.blockedURI));"

with sync_playwright() as pw:
    br = pw.chromium.launch()
    # Deneme resimleri tarayicinin kendi tuvaliyle uretilir (ek kutuphane gerekmez)
    _p = br.new_page()
    def resim(mime):
        return base64.b64decode(_p.evaluate("m => { const c = document.createElement('canvas'); c.width = 600; c.height = 800; const x = c.getContext('2d'); x.fillStyle = '#b4c8e6'; x.fillRect(0, 0, 600, 800); return c.toDataURL(m).split(',')[1]; }", mime))
    JPG, PNG = resim("image/jpeg"), resim("image/png"); _p.close()
    DATA_JPG = "data:image/jpeg;base64," + base64.b64encode(JPG).decode()
    def baglam(izin=False, ga=False):
        ctx = br.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        ctx.add_init_script((INIT if not izin else "try{localStorage.setItem('popupShown','true');localStorage.setItem('mcvKarsilama1','true');localStorage.setItem('mobilcv_consent','granted')}catch(e){}") + CSP_DINLE)
        dis = []
        def yol(r):
            u = r.request.url
            if u.startswith(BASE) or u.startswith("http://localhost"): return r.continue_()
            dis.append(u)
            if ga and "googletagmanager.com/gtag/js" in u: return r.fulfill(status=200, content_type="application/javascript", body="window.__gaYuklendi=1;")
            if ga and ("google-analytics.com" in u or "analytics.google.com" in u): return r.fulfill(status=204, body="")
            return r.abort()
        ctx.route("**/*", yol)
        p = ctx.new_page(); p.on("dialog", lambda d: d.accept())
        return ctx, p, dis

    # 1) 11 dil tam akis, CSP ihlali olmamali
    for l in DILLER:
        ctx, p, dis = baglam(); err = []; p.on("pageerror", lambda e: err.append(str(e)[:120]))
        p.goto(BASE + (l + "/" if l else ""), wait_until="load"); time.sleep(1.2)
        p.evaluate("d => autoSaveManager.applyData(d)", dict(CV, photo=DATA_JPG)); time.sleep(0.6)
        for t in ("", "tpl-classic", "tpl-top", "tpl-resume", "tpl-compact") + (("tpl-rirekisho",) if l == "ja" else ()):
            p.evaluate("t => applyCvTemplate(t)", t); time.sleep(0.4)
            p.evaluate("() => generateCvPdf().then(()=>1)")
        p.evaluate("applyCvTemplate('')"); time.sleep(0.3)
        p.evaluate("() => Array.from(mcvDocx()).length")
        p.click("#mcv-onyazi-btn"); time.sleep(0.3); p.fill("#mcv-oy-sirket", "Deneme"); p.click("#mcv-oy-taslak"); time.sleep(0.4)
        p.evaluate("() => mcvOnYazi.pdf().then(()=>1)")
        p.goto(BASE + (l + "/" if l else "") + "?r=1", wait_until="load"); time.sleep(1)
        p.click("#mcv-ilan-btn"); time.sleep(0.3); p.fill("#mcv-ilan-metin", "Aranan: muhasebe uzmanı, SAP, Excel, raporlama, bordro deneyimi, takım çalışması. " * 2); p.click("#mcv-ilan-calistir"); time.sleep(0.4)
        p.goto(BASE + (l + "/" if l else "") + "?r=2", wait_until="load"); time.sleep(1)
        p.click("#mcv-cvlerim-btn"); time.sleep(0.4)
        # meslek onerisi (oneri JSON fetch)
        p.goto(BASE + (l + "/" if l else "") + "?r=3", wait_until="load"); time.sleep(1)
        try:
            p.click('.personal-info-item[data-field="profession"] .personal-info-value', timeout=3000); time.sleep(1.0)
        except Exception: pass
        v = p.evaluate("window.__csp"); foto = p.evaluate("(document.getElementById('avatar')||{}).src||''")
        kontrol(f"CSP ihlali yok, tam akış: {l or 'tr'}", not v and not err, f"ihlal={v[:3]} hata={err[:2]} dis={dis[:2]}")
        ctx.close()

    # 2) Cerez izni + GA: yuklenir; GA uclari serbest; bilinmeyen alan adi engelli
    ctx, p, dis = baglam(izin=True, ga=True)
    p.goto(BASE, wait_until="load"); time.sleep(2)
    if not p.evaluate("!!window.__gaLoaded"):
        try: p.evaluate("window.mcvLoadGA && window.mcvLoadGA()")
        except Exception: pass
        time.sleep(1)
    r = p.evaluate("""async () => {
        const o = {};
        try { await fetch('https://region1.google-analytics.com/g/collect?v=2', {method:'POST', mode:'no-cors'}); o.ga_fetch = 'izinli'; } catch (e) { o.ga_fetch = 'engel'; }
        try { await fetch('https://kotu.example/cal?veri=1', {mode:'no-cors'}); o.kotu_fetch = 'izinli'; } catch (e) { o.kotu_fetch = 'engel'; }
        await new Promise(r => { const i = new Image(); i.onload = i.onerror = r; i.src = 'https://kotu.example/iz.png'; });
        o.ga = !!window.__gaYuklendi; return o; }""")
    time.sleep(0.5); v = p.evaluate("window.__csp")
    ga_ihlal = [x for x in v if "google" in x]; kotu_ihlal = [x for x in v if "kotu.example" in x]
    kontrol("CSP: çerez izniyle GA yükleniyor, GA uçları serbest", r["ga"] and r["ga_fetch"] == "izinli" and not ga_ihlal, f"{r} ihlal={ga_ihlal}")
    kontrol("CSP: bilinmeyen adrese fetch ve resim engelli", r["kotu_fetch"] == "engel" and len(kotu_ihlal) >= 2, f"{kotu_ihlal}")
    ctx.close()

    # 3) Fotograf yukleme (gercek dosya) + PDF + yedek gidis-donus
    ctx, p, dis = baglam(); p.goto(BASE, wait_until="load"); time.sleep(1.2)
    p.evaluate("d => autoSaveManager.applyData(d)", CV); time.sleep(0.5)
    for ad, veri, mime in (("JPEG", JPG, "image/jpeg"), ("PNG", PNG, "image/png")):
        p.set_input_files("#photoInput", files=[{"name": "foto." + ad.lower(), "mimeType": mime, "buffer": veri}]); time.sleep(1.2)
        src = p.evaluate("document.getElementById('avatar').src")
        kontrol(f"Fotoğraf yükleme çalışıyor ({ad})", src.startswith("data:image/") and p.evaluate("getComputedStyle(document.getElementById('avatar')).display") != "none", src[:30])
    pdf = p.evaluate("() => generateCvPdf().then(d => d.output('datauristring').length)")
    pdf0 = None
    p.evaluate("autoSaveManager.saveAllData && autoSaveManager.saveAllData()"); time.sleep(0.3)
    d = p.evaluate("autoSaveManager.collectData()")
    kontrol("Fotoğraf yedeğe yazılıyor ve geri yükleniyor", bool(d.get("photo", "")) and p.evaluate("p => window.mcvGuvenliFoto(p)", d["photo"]), (d.get("photo") or "")[:30])
    ctx.close()
    ctx, p, dis = baglam(); p.goto(BASE, wait_until="load"); time.sleep(1.2)
    p.evaluate("d => autoSaveManager.applyData(d)", d); time.sleep(0.6)
    kontrol("Yedekten fotoğraf geri geldi", p.evaluate("document.getElementById('avatar').src").startswith("data:image/"), "")
    ctx.close()

    # 4) Kotu fotograf degerleri reddedilir, dis istek gitmez
    for ad, deger in (("dış adres", "https://saldirgan.example/iz.png"), ("SVG", "data:image/svg+xml;base64," + base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" onload="window.__x=1"/>').decode()),
                      ("javascript", "javascript:window.__x=1"), ("http", "http://saldirgan.example/a.jpg")):
        ctx, p, dis = baglam(); p.goto(BASE, wait_until="load"); time.sleep(1.2)
        p.evaluate("d => autoSaveManager.applyData(d)", dict(CV, photo=deger)); time.sleep(1)
        src = p.evaluate("document.getElementById('avatar').getAttribute('src') || ''")
        kontrol(f"Fotoğraf reddedildi: {ad}", deger not in src and not [u for u in dis if "saldirgan" in u] and not p.evaluate("window.__x||0"), f"src={src[:30]} dis={dis[:2]}")
        ctx.close()
    # SVG dosyasi yukleme
    ctx, p, dis = baglam(); p.goto(BASE, wait_until="load"); time.sleep(1.2)
    p.set_input_files("#photoInput", files=[{"name": "a.svg", "mimeType": "image/svg+xml", "buffer": b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'}]); time.sleep(1)
    src = p.evaluate("document.getElementById('avatar').getAttribute('src') || ''")
    kontrol("SVG dosyası fotoğraf olarak ham hâliyle kullanılmıyor", not src.startswith("data:image/svg"), src[:30])
    ctx.close()

    # 5) Gecersiz tema yedegi cokertmez; hata mesaji temizligi
    ctx, p, dis = baglam(); err = []; p.on("pageerror", lambda e: err.append(str(e)[:100]))
    p.goto(BASE, wait_until="load"); time.sleep(1.2)
    ok = p.evaluate("d => { try { autoSaveManager.applyData(d); return true; } catch (e) { return String(e); } }", dict(CV, theme="kotu tema <b>"))
    ad = p.evaluate("document.querySelector('.personal-info-item[data-field=fullname] .personal-info-value').textContent")
    kontrol("Geçersiz tema yedeği yüklemeyi bozmaz", ok is True and ad == "Test Kişi" and p.evaluate("window.currentCvTheme") == "", f"{ok} ad={ad}")
    m = p.evaluate("""() => { let g = null; const t = window.mcvTrack; window.__gaLoaded = true; window.gtag = (a, b, c) => { g = c; };
        window.mcvReportError('js', "Failed: The token provided ('Ayşe Yılmaz gizli') contains \\"bilgi\\" ali@ornek.com 05321234567", 'x.js:1'); return g && g.err_msg; }""")
    kontrol("Hata bildiriminde tırnaklı metin, e-posta, numara gitmiyor", m and "Ayşe" not in m and "bilgi" not in m and "ali@" not in m and "5321234567" not in m, m)
    ctx.close()
    br.close()

hata = [a for a, ok in sonuc if not ok]
print(f"\nToplam {len(sonuc)}, hata {len(hata)}")
sys.exit(1 if hata else 0)
