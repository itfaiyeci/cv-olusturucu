# -*- coding: utf-8 -*-
"""PDF'in gorunmez metin katmani icin Japonca ve Cince "yalnizca olcu" yazi tipleri uretir.

Neden: PDF'in gorunmez metin katmani (ATS'lerin ve "metni sec/kopyala"nin okudugu kisim) gomulu bir
yazi tipi ister. Tam CJK yazi tipini gommek PDF'i birkac MB buyutur. Oysa katman GORUNMEZ: harf
cizimlerine gerek yok. Bu betik her karakter icin bos (cizimsiz) bir glif, dogru karakter eslemesi
(cmap) ve gercek genislikler (hmtx) iceren kucuk bir TrueType dosyasi uretir.
Bu yazi tipleri GORUNUR metin icin KULLANILMAZ.

Kapsam (yalnizca BMP, jsPDF cmap format 4 okur):
  jp.ttf = Noto Sans JP (fonts/jp, @fontsource/noto-sans-jp 5.3.0) + pdf-font-latin.js'deki karakterler
  zh.ttf = Noto Sans SC (@fontsource/noto-sans-sc 5.3.1, 400) + pdf-font-latin.js'deki karakterler
Lisans: SIL Open Font License 1.1 (degistirilmis surum, ayri adla).

Kullanim: python3 pdf_cjk_fontlari.py <@fontsource/noto-sans-sc paket klasoru>
Gerekenler: pip install fonttools brotli
"""
import base64
import io
import re
import sys
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).parent
OUT = ROOT / "fonts" / "pdf-cjk"
UPM = 1000


def genislikler(f, sonuc):
    """f yazi tipindeki her BMP karakterinin genisligini (1000 birime olcekli) sonuc'a ekler."""
    olcek = UPM / f["head"].unitsPerEm
    hmtx = f["hmtx"].metrics
    for cp, gad in f.getBestCmap().items():
        if cp > 0xFFFF or cp in sonuc:
            continue
        sonuc[cp] = max(0, round(hmtx[gad][0] * olcek))


def latin_font():
    s = (ROOT / "pdf-font-latin.js").read_text(encoding="utf-8")
    b = base64.b64decode(re.search(r"['\"]([A-Za-z0-9+/=]{1000,})['\"]", s).group(1))
    return TTFont(io.BytesIO(b))


def uret(ad, woff2_dosyalari, aile):
    w = {}
    for p in sorted(woff2_dosyalari):
        genislikler(TTFont(str(p)), w)
    genislikler(latin_font(), w)  # CJK yazi tipinde olmayan Turkce/Latin/Kiril harfler
    cps = sorted(c for c in w if c >= 0x20)
    gliflar = [".notdef"] + ["u%04X" % c for c in cps]
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(gliflar)
    fb.setupCharacterMap({c: "u%04X" % c for c in cps})
    bos = TTGlyphPen(None).glyph()
    fb.setupGlyf({g: bos for g in gliflar})
    metr = {".notdef": (500, 0)}
    metr.update({"u%04X" % c: (w[c], 0) for c in cps})
    fb.setupHorizontalMetrics(metr)
    fb.setupHorizontalHeader(ascent=880, descent=-120)
    ps = aile.replace(" ", "") + "-Regular"
    # jsPDF ad tablosunda tam ad (4), PostScript adi (6) gibi kayitlari bekliyor
    fb.setupNameTable({"familyName": aile, "styleName": "Regular", "fullName": aile + " Regular",
                       "psName": ps, "uniqueFontIdentifier": ps + ";1.000", "version": "Version 1.000"})
    fb.setupOS2(sTypoAscender=880, sTypoDescender=-120, usWinAscent=880, usWinDescent=120)
    fb.setupPost(keepGlyphNames=False)  # glif adlari gereksiz; dosyayi kucultur
    OUT.mkdir(parents=True, exist_ok=True)
    hedef = OUT / f"{ad}.ttf"
    fb.save(str(hedef))
    print(f"{ad}.ttf: {len(cps)} karakter, {hedef.stat().st_size // 1024} KB")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sc = Path(sys.argv[1])
    uret("jp", (ROOT / "fonts" / "jp").glob("*-400-normal.woff2"), "MobilCV PDF JP")
    uret("zh", (sc / "files").glob("noto-sans-sc-*-400-normal.woff2"), "MobilCV PDF ZH")
    lic = sc / "LICENSE"
    if lic.exists():
        (OUT / "OFL-LICENSE.txt").write_text(
            "Bu klasordeki jp.ttf ve zh.ttf, asagidaki lisansli Noto Sans JP / Noto Sans SC yazi tiplerinden "
            "uretilmis, cizimleri bosaltilmis (yalnizca olcu) degistirilmis surumlerdir.\n\n" + lic.read_text(encoding="utf-8"),
            encoding="utf-8")
