# -*- coding: utf-8 -*-
"""IndexNow bildirimi (17.11, kurucu karari): siteye yeni surum yayinlaninca degisen sayfalari Bing'e (ve IndexNow'u
kullanan diger arama motorlarina) hemen bildirir. ChatGPT aramasi Bing dizinini de kullaniyor.

Kullanim (GitHub Actions):  python3 .github/indexnow.py <site_adresi> <onceki_sha> <yeni_sha> [--deneme]
  - Yalniz site haritasinda (sitemap*.xml) bulunan adresler bildirilir; 404, test ve onizleme sayfalari gitmez.
  - Anahtar: kokteki 32 karakterlik <anahtar>.txt dosyasi (icinde ayni anahtar).
  - --deneme: istek gonderilmez, yalniz adres listesi yazilir.
  - --tum: degisenlere bakmadan site haritasindaki TUM adresler gonderilir (ilk kurulumda bir kez, elle).
Cikis: 200/202 basari; 400/403/422 ayar hatasi (cikis 1, GitHub e-posta gonderir); 429/5xx uyari (cikis 0)."""
import glob, json, os, re, subprocess, sys, urllib.request

site = sys.argv[1].rstrip("/") + "/"
onceki, yeni = sys.argv[2], sys.argv[3]
deneme = "--deneme" in sys.argv
tum = "--tum" in sys.argv

anahtarlar = [f[:-4] for f in os.listdir(".") if re.fullmatch(r"[0-9a-f]{32}\.txt", f)]
if len(anahtarlar) != 1:
    print(f"Anahtar dosyasi bulunamadi ya da birden fazla: {anahtarlar}"); sys.exit(1)
anahtar = anahtarlar[0]
if open(anahtar + ".txt", encoding="utf-8").read().strip() != anahtar:
    print("Anahtar dosyasinin icerigi adiyla ayni degil"); sys.exit(1)

harita = set()
for f in glob.glob("sitemap*.xml"):
    harita |= set(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", open(f, encoding="utf-8").read()))

try:
    degisen = subprocess.check_output(["git", "diff", "--name-only", onceki, yeni], text=True).split()
except subprocess.CalledProcessError:
    degisen = []  # ilk commit ya da gecmis yok: hicbir sey gonderme
adresler = []
for d in degisen:
    if not d.endswith(".html"):
        continue
    yol = d[:-len("index.html")] if d.endswith("index.html") else d
    u = site + yol
    if u in harita and u not in adresler:
        adresler.append(u)

if tum:
    adresler = sorted(harita)
print(f"Degisen dosya: {len(degisen)}, bildirilecek adres: {len(adresler)}")
for u in adresler[:50]:
    print("  ", u)
if not adresler or deneme:
    sys.exit(0)

host = re.sub(r"^https?://", "", site).rstrip("/")
govde = json.dumps({"host": host, "key": anahtar, "keyLocation": f"{site}{anahtar}.txt", "urlList": adresler[:10000]}).encode()
def gonder():
    istek = urllib.request.Request("https://api.indexnow.org/indexnow", data=govde,
                                   headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urllib.request.urlopen(istek, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        print(f"Uyari: IndexNow'a ulasilamadi: {e}"); sys.exit(0)

kod = gonder()
if kod == 403:  # 17.11: yeni anahtar ilk denemede 403 verdi, 2 dk sonra 200 -> bir kez bekleyip yeniden dene
    import time; print("403: anahtar dogrulamasi gecikmis olabilir, 120 sn sonra yeniden deneniyor"); time.sleep(120); kod = gonder()
print(f"IndexNow yaniti: {kod}")
if kod in (400, 403, 422):
    sys.exit(1)
sys.exit(0)
