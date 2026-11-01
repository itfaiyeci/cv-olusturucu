# -*- coding: utf-8 -*-
"""Guvenlik kontrolu (CI). Hata bulursa cikis kodu 1 -> GitHub e-posta gonderir.

  python3 tests/guvenlik_kontrol.py statik   # her degisiklikte: izinsiz dis kod/adres var mi?
  python3 tests/guvenlik_kontrol.py canli    # gece: yayindaki sayfalar depodakiyle birebir ayni mi?
"""
import base64, hashlib, os, re, sys, urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DILLER = ["", "en", "de", "fr", "es", "it", "pt", "ru", "ar", "zh", "ja"]
SAYFALAR = [(l + "/" if l else "") + "index.html" for l in DILLER]
CSP = ("default-src 'self'; "
       "script-src 'self' 'unsafe-inline' https://*.googletagmanager.com; "
       "style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob: https://*.google-analytics.com https://*.googletagmanager.com; "
       "font-src 'self' data:; "
       "connect-src 'self' https://formspree.io https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com; "
       "form-action 'self' https://formspree.io; "
       "base-uri 'self'; object-src 'none'; frame-src 'none'; worker-src 'self' blob:; manifest-src 'self'")
# Kod tarafinda (script/fetch/form/img kaynagi) izin verilen dis alan adlari
IZINLI = {"www.googletagmanager.com", "formspree.io"}
# Sayfa metninde yalnizca baglanti olarak gecebilen adresler (kaynak olarak yuklenmez)
BAGLANTI = {"www.mobilcv.com", "mobilcv.net", "x.com", "www.tiktok.com", "www.threads.com", "www.instagram.com", "schema.org",
            "linkedin.com", "www.linkedin.com", "github.com", "wa.me", "www.w3.org", "purl.org", "schemas.openxmlformats.org",
            "schemas.microsoft.com", "www.googletagmanager.com", "formspree.io"}

hatalar = []
def hata(m): hatalar.append(m); print("❌", m)

def statik():
    for s in SAYFALAR:
        t = open(os.path.join(KOK, s), encoding="utf-8").read()
        # 1) CSP yerinde ve degismemis
        m = re.findall(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', t)
        if m != [CSP]: hata(f"{s}: CSP eksik ya da değişmiş ({len(m)} adet)")
        # 2) Harici script dosyasi: yalnizca /lib + integrity
        for tag in re.findall(r"<script\b[^>]*\bsrc=[^>]*>", t):
            src = re.search(r'src="([^"]+)"', tag).group(1)
            if not src.startswith("/lib/") or "integrity=" not in tag: hata(f"{s}: izinsiz script dosyası: {tag[:120]}")
        # 3) Kaynak olarak yuklenen dis adresler (src=, href= stylesheet, action=, fetch/sendBeacon/WebSocket/import)
        for kalip in (r'\bsrc\s*=\s*["\']https?://([^/"\']+)', r'\baction\s*=\s*["\']https?://([^/"\']+)',
                      r'(?:fetch|sendBeacon|WebSocket|importScripts|import)\s*\(\s*["\'`](?:wss?|https?)://([^/"\'`]+)',
                      r'<link[^>]+rel="(?:stylesheet|preload|modulepreload|prefetch)"[^>]+href="https?://([^/"]+)',
                      r'\.src\s*=\s*["\'`]https?://([^/"\'`]+)'):
            for h in re.findall(kalip, t):
                if h not in IZINLI: hata(f"{s}: izinsiz dış kaynak: {h}")
        # 4) Sayfadaki tum dis alan adlari bilinen listede mi (yeni bir adres eklenince insan gozuyle bakilsin)
        for h in sorted(set(re.findall(r"https?://([a-zA-Z0-9.-]+)", t))):
            if h not in BAGLANTI and h not in ("localhost",): hata(f"{s}: listede olmayan alan adı: {h}")
        # 5) Tehlikeli yapilar
        for kalip, ad in ((r"<iframe", "iframe"), (r"\beval\s*\(", "eval"), (r"new Function\s*\(", "new Function"), (r"document\.write\s*\(", "document.write")):
            if re.search(kalip, t): hata(f"{s}: {ad} kullanımı")
        # 6) Fotograf guvenlik kontrolu yerinde
        if "window.mcvGuvenliFoto(photoData)" not in t: hata(f"{s}: fotoğraf güvenlik kontrolü yok")
    # 7) /lib dosyalarinin SRI ozeti dosyayla ayni
    t = open(os.path.join(KOK, "index.html"), encoding="utf-8").read()
    for src, sri in re.findall(r'<script[^>]*src="(/lib/[^"]+)"[^>]*integrity="(sha384-[^"]+)"', t):
        oz = "sha384-" + base64.b64encode(hashlib.sha384(open(os.path.join(KOK, src.lstrip("/")), "rb").read()).digest()).decode()
        if oz != sri: hata(f"{src}: SRI özeti dosyayla uyuşmuyor")

def canli():
    dosyalar = SAYFALAR + ["lib/jspdf.umd.min.js", "lib/html2canvas.min.js", "pdf-font-latin.js", "pdf-font-arabic.js"]
    for s in dosyalar:
        url = "https://www.mobilcv.com/" + (s[:-10] if s.endswith("index.html") else s)
        try:
            req = urllib.request.Request(url + ("?b=" + hashlib.md5(os.urandom(8)).hexdigest()[:8]), headers={"User-Agent": "MobilCV-butunluk", "Cache-Control": "no-cache"})
            canli_b = urllib.request.urlopen(req, timeout=30).read()
        except Exception as e:
            hata(f"{url}: indirilemedi ({e})"); continue
        yerel = open(os.path.join(KOK, s), "rb").read()
        if hashlib.sha256(canli_b).hexdigest() != hashlib.sha256(yerel).hexdigest():
            hata(f"{url}: yayındaki dosya depodakinden FARKLI (canlı {hashlib.sha256(canli_b).hexdigest()[:12]}, depo {hashlib.sha256(yerel).hexdigest()[:12]})")
        else:
            print("✅", url)

if __name__ == "__main__":
    {"statik": statik, "canli": canli}[sys.argv[1] if len(sys.argv) > 1 else "statik"]()
    print(f"\nGüvenlik kontrolü ({sys.argv[1] if len(sys.argv) > 1 else 'statik'}): {len(hatalar)} sorun")
    sys.exit(1 if hatalar else 0)
