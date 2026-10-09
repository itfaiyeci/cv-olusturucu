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
 4) Ana sayfa SEO: her dilde aranan kelimeleri iceren ana baslik (H1),
    aracin altinda gorunen "3 adimda CV / Neden MobilCV / SSS" bolumu ve
    ayni SSS'den uretilen FAQ yapilandirilmis verisi.
 5) Hiz: PDF fontlari (yaklasik 310 KB) sayfadan cikarilip ayri dosyalara
    (pdf-font-latin.js, pdf-font-arabic.js) tasinir; sayfa acildiktan sonra,
    yalnizca gerektiginde yuklenir.

index.html'i ileride degistirirseniz bu scripti tekrar calistirmaniz yeterli.
"""
import html
import json
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


INSTAGRAM = "https://www.instagram.com/mobilcvcom/"
THREADS = "https://www.threads.com/@mobilcvcom"
SOCIAL_LINKS = (' · <a href="' + INSTAGRAM + '" data-social-link target="_blank" rel="noopener me" style="font-size:12px;">Instagram</a>'
                ' · <a href="' + THREADS + '" target="_blank" rel="noopener me" style="font-size:12px;">Threads</a>')


def add_social(src):
    """Alt kisma Instagram/Threads linki ve JSON-LD'ye sameAs (hesabin siteye ait oldugu bilgisi) ekler."""
    s = src
    if "data-social-link" not in s:
        s = sub_once(r'(<a href="[^"]*" data-privacy-link[^>]*>[^<]*</a>)', None, s, "gizlilik linki (sosyal)",
                     func=lambda m: m.group(1) + SOCIAL_LINKS)
    if '"sameAs"' not in s:
        s = sub_once(r'("author": \{\s*"@type": "Organization",\s*"name": "MobilCV",\s*"url": "https://www\.mobilcv\.com")(\s*\})',
                     None, s, "JSON-LD author",
                     func=lambda m: m.group(1) + ',\n            "sameAs": ["' + INSTAGRAM + '", "' + THREADS + '"]' + m.group(2))
    return s


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


# ===================== ANA SAYFA SEO ICERIGI =====================
C = {
"tr": dict(
    h1="Ücretsiz CV Hazırla – Üye Olmadan",
    sub="Telefondan 10 dilde profesyonel CV oluşturun, PDF olarak indirin",
    steps_t="3 adımda CV hazırlayın",
    steps=["Bilgilerinizi forma yazın: iletişim, deneyim, eğitim, yetenekler. İsterseniz fotoğraf ekleyin.",
           "Renk temasını ve CV dilini seçin; değişiklikleri önizlemede anında görün.",
           "<b>PDF İndir</b> düğmesine basın. CV'niz başvuruya hazır."],
    why_t="Neden MobilCV?",
    why=["<b>Tamamen ücretsiz:</b> Gizli ücret, deneme süresi veya filigran yok.",
         "<b>Üyelik yok:</b> E-posta, şifre veya hesap gerekmez.",
         "<b>Bilgileriniz sizde kalır:</b> CV'niz yalnızca kendi tarayıcınızda tutulur, sunucuya gönderilmez.",
         "<b>Telefon için tasarlandı:</b> Bilgisayar olmadan, birkaç dakikada CV hazırlayabilirsiniz.",
         "<b>10 dil:</b> Türkçe, İngilizce, Almanca, Fransızca, İspanyolca, İtalyanca, Portekizce, Rusça, Arapça ve Çince."],
    faq_t="Sıkça Sorulan Sorular",
    faq=[("MobilCV gerçekten ücretsiz mi?", "Evet. CV oluşturmak ve PDF olarak indirmek tamamen ücretsizdir; gizli ücret veya filigran yoktur."),
         ("CV hazırlamak için üye olmam gerekiyor mu?", "Hayır. Üyelik, e-posta veya şifre gerekmez; sayfayı açıp hemen başlayabilirsiniz."),
         ("Bilgilerim nereye kaydediliyor?", "Bilgileriniz yalnızca kendi cihazınızda, tarayıcınızın yerel depolama alanında tutulur ve sunucularımıza gönderilmez. Silmek için Tümünü Temizle düğmesini kullanabilirsiniz."),
         ("Telefondan CV hazırlayabilir miyim?", "Evet. MobilCV telefonda kullanılmak üzere tasarlandı; bilgisayarda da çalışır."),
         ("CV'me fotoğraf ekleyebilir miyim?", "Evet. Fotoğraf eklemek isteğe bağlıdır; fotoğraf alanına dokunarak ekleyebilirsiniz."),
         ("CV'mi hangi dillerde hazırlayabilirim?", "Türkçe, İngilizce, Almanca, Fransızca, İspanyolca, İtalyanca, Portekizce, Rusça, Arapça ve Çince olmak üzere 10 dilde hazırlayabilirsiniz."),
         ("CV'mi nasıl indiririm?", "Formu doldurduktan sonra PDF İndir düğmesine basın. CV'niz PDF dosyası olarak cihazınıza kaydedilir.")],
    more="Meslek bazlı CV örnekleri ve CV yazma rehberleri için",
    more_link=("https://mobilcv.net/cv-ornekleri.html", "CV örneklerine göz atın"),
),
"en": dict(
    h1="Free CV Maker – No Sign-Up",
    sub="Create a professional CV on your phone in 10 languages and download it as PDF",
    steps_t="Create your CV in 3 steps",
    steps=["Fill in your details: contact info, experience, education and skills. Add a photo if you like.",
           "Choose a colour theme and the CV language; see every change instantly in the preview.",
           "Tap <b>Download PDF</b>. Your CV is ready to send."],
    why_t="Why MobilCV?",
    why=["<b>Completely free:</b> no hidden fees, no trial period, no watermark.",
         "<b>No sign-up:</b> no email, password or account needed.",
         "<b>Your data stays with you:</b> your CV is kept only in your own browser and is never sent to a server.",
         "<b>Built for phones:</b> make a CV in minutes without a computer.",
         "<b>10 languages:</b> English, Turkish, German, French, Spanish, Italian, Portuguese, Russian, Arabic and Chinese."],
    faq_t="Frequently Asked Questions",
    faq=[("Is MobilCV really free?", "Yes. Creating your CV and downloading it as PDF is completely free, with no hidden fees or watermark."),
         ("Do I need to sign up?", "No. There is no account, email or password; just open the page and start."),
         ("Where is my information stored?", "Only on your own device, in your browser's local storage. It is never sent to our servers. Use the Clear All button to delete it."),
         ("Can I make a CV on my phone?", "Yes. MobilCV is designed for phones and also works on computers."),
         ("Can I add a photo to my CV?", "Yes. Adding a photo is optional; tap the photo area to add one."),
         ("Which languages can I create my CV in?", "10 languages: English, Turkish, German, French, Spanish, Italian, Portuguese, Russian, Arabic and Chinese."),
         ("How do I download my CV?", "When you have filled in the form, tap Download PDF. Your CV is saved to your device as a PDF file.")],
    more="For CV examples by profession and writing tips,",
    more_link=("https://mobilcv.net/en/", "visit our career blog"),
),
"de": dict(
    h1="Lebenslauf kostenlos erstellen – ohne Anmeldung",
    sub="Professionellen Lebenslauf am Handy in 10 Sprachen erstellen und als PDF herunterladen",
    steps_t="In 3 Schritten zum Lebenslauf",
    steps=["Tragen Sie Ihre Angaben ein: Kontakt, Berufserfahrung, Ausbildung und Kenntnisse. Auf Wunsch mit Bewerbungsfoto.",
           "Wählen Sie Farbschema und Sprache des Lebenslaufs; jede Änderung sehen Sie sofort in der Vorschau.",
           "Tippen Sie auf <b>PDF herunterladen</b>. Ihr Lebenslauf ist bereit für die Bewerbung."],
    why_t="Warum MobilCV?",
    why=["<b>Komplett kostenlos:</b> keine versteckten Kosten, kein Testzeitraum, kein Wasserzeichen.",
         "<b>Ohne Anmeldung:</b> keine E-Mail, kein Passwort, kein Konto.",
         "<b>Ihre Daten bleiben bei Ihnen:</b> Der Lebenslauf wird nur in Ihrem Browser gespeichert und nicht an einen Server gesendet.",
         "<b>Fürs Handy gemacht:</b> Lebenslauf in wenigen Minuten erstellen, ganz ohne Computer.",
         "<b>10 Sprachen:</b> Deutsch, Englisch, Türkisch, Französisch, Spanisch, Italienisch, Portugiesisch, Russisch, Arabisch und Chinesisch."],
    faq_t="Häufige Fragen",
    faq=[("Ist MobilCV wirklich kostenlos?", "Ja. Lebenslauf erstellen und als PDF herunterladen ist komplett kostenlos, ohne versteckte Kosten oder Wasserzeichen."),
         ("Muss ich mich anmelden?", "Nein. Sie brauchen kein Konto, keine E-Mail und kein Passwort; einfach Seite öffnen und loslegen."),
         ("Wo werden meine Daten gespeichert?", "Nur auf Ihrem eigenen Gerät im lokalen Speicher Ihres Browsers. Sie werden nicht an unsere Server übertragen. Mit Alles löschen entfernen Sie sie."),
         ("Kann ich den Lebenslauf am Handy erstellen?", "Ja. MobilCV ist für Smartphones gemacht und funktioniert auch am Computer."),
         ("Kann ich ein Bewerbungsfoto einfügen?", "Ja. Das Foto ist optional; tippen Sie auf das Fotofeld, um eines hinzuzufügen."),
         ("In welchen Sprachen kann ich den Lebenslauf erstellen?", "In 10 Sprachen: Deutsch, Englisch, Türkisch, Französisch, Spanisch, Italienisch, Portugiesisch, Russisch, Arabisch und Chinesisch."),
         ("Wie lade ich meinen Lebenslauf herunter?", "Tippen Sie nach dem Ausfüllen auf PDF herunterladen. Der Lebenslauf wird als PDF-Datei auf Ihrem Gerät gespeichert.")],
    more="Tipps zu Lebenslauf und Bewerbung finden Sie",
    more_link=("https://mobilcv.net/de/", "in unserem Karriere-Blog"),
),
"fr": dict(
    h1="Créer un CV gratuit – sans inscription",
    sub="Créez un CV professionnel sur votre téléphone en 10 langues et téléchargez-le en PDF",
    steps_t="Votre CV en 3 étapes",
    steps=["Saisissez vos informations : coordonnées, expérience, formation et compétences. Ajoutez une photo si vous le souhaitez.",
           "Choisissez un thème de couleur et la langue du CV ; chaque modification s'affiche aussitôt dans l'aperçu.",
           "Appuyez sur <b>Télécharger PDF</b>. Votre CV est prêt à être envoyé."],
    why_t="Pourquoi MobilCV ?",
    why=["<b>Entièrement gratuit :</b> aucun frais caché, aucune période d'essai, aucun filigrane.",
         "<b>Sans inscription :</b> ni e-mail, ni mot de passe, ni compte.",
         "<b>Vos données restent chez vous :</b> votre CV est conservé uniquement dans votre navigateur, jamais envoyé à un serveur.",
         "<b>Pensé pour le téléphone :</b> créez un CV en quelques minutes, sans ordinateur.",
         "<b>10 langues :</b> français, anglais, turc, allemand, espagnol, italien, portugais, russe, arabe et chinois."],
    faq_t="Questions fréquentes",
    faq=[("MobilCV est-il vraiment gratuit ?", "Oui. Créer votre CV et le télécharger en PDF est entièrement gratuit, sans frais cachés ni filigrane."),
         ("Dois-je m'inscrire ?", "Non. Aucun compte, e-mail ou mot de passe n'est nécessaire : ouvrez la page et commencez."),
         ("Où sont enregistrées mes informations ?", "Uniquement sur votre appareil, dans le stockage local de votre navigateur. Elles ne sont jamais envoyées à nos serveurs. Le bouton Tout effacer les supprime."),
         ("Puis-je créer mon CV sur mon téléphone ?", "Oui. MobilCV est conçu pour le téléphone et fonctionne aussi sur ordinateur."),
         ("Puis-je ajouter une photo à mon CV ?", "Oui. La photo est facultative ; touchez la zone photo pour en ajouter une."),
         ("Dans quelles langues puis-je créer mon CV ?", "En 10 langues : français, anglais, turc, allemand, espagnol, italien, portugais, russe, arabe et chinois."),
         ("Comment télécharger mon CV ?", "Une fois le formulaire rempli, appuyez sur Télécharger PDF. Votre CV est enregistré sur votre appareil au format PDF.")],
    more="Pour des conseils CV et entretien,",
    more_link=("https://mobilcv.net/fr/", "consultez notre blog carrière"),
),
"es": dict(
    h1="Crear currículum gratis – sin registro",
    sub="Crea un currículum profesional desde el móvil en 10 idiomas y descárgalo en PDF",
    steps_t="Tu currículum en 3 pasos",
    steps=["Escribe tus datos: contacto, experiencia, formación y habilidades. Añade una foto si quieres.",
           "Elige un tema de color y el idioma del currículum; verás cada cambio al instante en la vista previa.",
           "Pulsa <b>Descargar PDF</b>. Tu currículum está listo para enviar."],
    why_t="¿Por qué MobilCV?",
    why=["<b>Totalmente gratis:</b> sin cargos ocultos, sin periodo de prueba y sin marca de agua.",
         "<b>Sin registro:</b> no necesitas correo, contraseña ni cuenta.",
         "<b>Tus datos son tuyos:</b> el currículum se guarda solo en tu navegador y nunca se envía a un servidor.",
         "<b>Pensado para el móvil:</b> crea tu currículum en minutos, sin ordenador.",
         "<b>10 idiomas:</b> español, inglés, turco, alemán, francés, italiano, portugués, ruso, árabe y chino."],
    faq_t="Preguntas frecuentes",
    faq=[("¿MobilCV es realmente gratis?", "Sí. Crear tu currículum y descargarlo en PDF es totalmente gratis, sin cargos ocultos ni marca de agua."),
         ("¿Tengo que registrarme?", "No. No necesitas cuenta, correo ni contraseña: abre la página y empieza."),
         ("¿Dónde se guardan mis datos?", "Solo en tu propio dispositivo, en el almacenamiento local del navegador. Nunca se envían a nuestros servidores. Con Limpiar todo puedes borrarlos."),
         ("¿Puedo hacer el currículum desde el móvil?", "Sí. MobilCV está pensado para el móvil y también funciona en el ordenador."),
         ("¿Puedo añadir una foto?", "Sí. La foto es opcional; toca el área de la foto para añadirla."),
         ("¿En qué idiomas puedo crear mi currículum?", "En 10 idiomas: español, inglés, turco, alemán, francés, italiano, portugués, ruso, árabe y chino."),
         ("¿Cómo descargo mi currículum?", "Cuando completes el formulario, pulsa Descargar PDF. El currículum se guarda en tu dispositivo como archivo PDF.")],
    more="Para consejos sobre currículum y entrevistas,",
    more_link=("https://mobilcv.net/es/", "visita nuestro blog de carrera"),
),
"it": dict(
    h1="Crea il tuo CV gratis – senza registrazione",
    sub="Crea un CV professionale dal telefono in 10 lingue e scaricalo in PDF",
    steps_t="Il tuo CV in 3 passaggi",
    steps=["Inserisci i tuoi dati: contatti, esperienze, formazione e competenze. Se vuoi, aggiungi una foto.",
           "Scegli il tema colore e la lingua del CV; ogni modifica appare subito nell'anteprima.",
           "Tocca <b>Scarica PDF</b>. Il tuo CV è pronto da inviare."],
    why_t="Perché MobilCV?",
    why=["<b>Completamente gratis:</b> nessun costo nascosto, nessuna prova, nessuna filigrana.",
         "<b>Senza registrazione:</b> niente e-mail, password o account.",
         "<b>I tuoi dati restano a te:</b> il CV resta solo nel tuo browser e non viene mai inviato a un server.",
         "<b>Pensato per il telefono:</b> crea un CV in pochi minuti, senza computer.",
         "<b>10 lingue:</b> italiano, inglese, turco, tedesco, francese, spagnolo, portoghese, russo, arabo e cinese."],
    faq_t="Domande frequenti",
    faq=[("MobilCV è davvero gratis?", "Sì. Creare il CV e scaricarlo in PDF è completamente gratuito, senza costi nascosti né filigrana."),
         ("Devo registrarmi?", "No. Non servono account, e-mail o password: apri la pagina e inizia."),
         ("Dove vengono salvati i miei dati?", "Solo sul tuo dispositivo, nella memoria locale del browser. Non vengono mai inviati ai nostri server. Con Pulisci tutto puoi cancellarli."),
         ("Posso creare il CV dal telefono?", "Sì. MobilCV è pensato per il telefono e funziona anche sul computer."),
         ("Posso aggiungere una foto al CV?", "Sì. La foto è facoltativa; tocca l'area della foto per aggiungerla."),
         ("In quali lingue posso creare il CV?", "In 10 lingue: italiano, inglese, turco, tedesco, francese, spagnolo, portoghese, russo, arabo e cinese."),
         ("Come scarico il mio CV?", "Dopo aver compilato il modulo, tocca Scarica PDF. Il CV viene salvato sul dispositivo come file PDF.")],
    more="Per consigli su CV e colloqui,",
    more_link=("https://mobilcv.net/it/", "visita il nostro blog carriera"),
),
"pt": dict(
    h1="Criar currículo grátis – sem cadastro",
    sub="Crie um currículo profissional pelo celular em 10 idiomas e baixe em PDF",
    steps_t="Seu currículo em 3 passos",
    steps=["Preencha seus dados: contato, experiência, formação e habilidades. Se quiser, adicione uma foto.",
           "Escolha o tema de cores e o idioma do currículo; veja cada alteração na hora na pré-visualização.",
           "Toque em <b>Baixar PDF</b>. Seu currículo está pronto para enviar."],
    why_t="Por que o MobilCV?",
    why=["<b>Totalmente grátis:</b> sem taxas escondidas, sem período de teste e sem marca d'água.",
         "<b>Sem cadastro:</b> não precisa de e-mail, senha nem conta.",
         "<b>Seus dados ficam com você:</b> o currículo fica só no seu navegador e nunca é enviado a um servidor.",
         "<b>Feito para o celular:</b> crie seu currículo em minutos, sem computador.",
         "<b>10 idiomas:</b> português, inglês, turco, alemão, francês, espanhol, italiano, russo, árabe e chinês."],
    faq_t="Perguntas frequentes",
    faq=[("O MobilCV é realmente grátis?", "Sim. Criar o currículo e baixar em PDF é totalmente grátis, sem taxas escondidas nem marca d'água."),
         ("Preciso fazer cadastro?", "Não. Você não precisa de conta, e-mail ou senha: é só abrir a página e começar."),
         ("Onde meus dados ficam salvos?", "Apenas no seu próprio dispositivo, no armazenamento local do navegador. Eles nunca são enviados aos nossos servidores. Use Limpar tudo para apagá-los."),
         ("Posso fazer o currículo pelo celular?", "Sim. O MobilCV foi feito para o celular e também funciona no computador."),
         ("Posso colocar foto no currículo?", "Sim. A foto é opcional; toque na área da foto para adicioná-la."),
         ("Em quais idiomas posso criar meu currículo?", "Em 10 idiomas: português, inglês, turco, alemão, francês, espanhol, italiano, russo, árabe e chinês."),
         ("Como baixo meu currículo?", "Depois de preencher o formulário, toque em Baixar PDF. O currículo é salvo no seu dispositivo como arquivo PDF.")],
    more="Para dicas de currículo e entrevista,",
    more_link=("https://mobilcv.net/pt/", "visite nosso blog de carreira"),
),
"ru": dict(
    h1="Создать резюме бесплатно – без регистрации",
    sub="Создайте профессиональное резюме с телефона на 10 языках и скачайте в PDF",
    steps_t="Резюме за 3 шага",
    steps=["Заполните данные: контакты, опыт работы, образование и навыки. При желании добавьте фото.",
           "Выберите цветовую тему и язык резюме; все изменения сразу видны в предпросмотре.",
           "Нажмите <b>Скачать PDF</b>. Резюме готово к отправке."],
    why_t="Почему MobilCV?",
    why=["<b>Полностью бесплатно:</b> без скрытых платежей, пробного периода и водяных знаков.",
         "<b>Без регистрации:</b> не нужны e-mail, пароль или аккаунт.",
         "<b>Данные остаются у вас:</b> резюме хранится только в вашем браузере и не отправляется на сервер.",
         "<b>Создан для телефона:</b> резюме за несколько минут, без компьютера.",
         "<b>10 языков:</b> русский, английский, турецкий, немецкий, французский, испанский, итальянский, португальский, арабский и китайский."],
    faq_t="Частые вопросы",
    faq=[("MobilCV действительно бесплатный?", "Да. Создать резюме и скачать его в PDF можно полностью бесплатно, без скрытых платежей и водяных знаков."),
         ("Нужно ли регистрироваться?", "Нет. Не нужны аккаунт, e-mail или пароль: откройте страницу и начните."),
         ("Где хранятся мои данные?", "Только на вашем устройстве, в локальном хранилище браузера. Они не отправляются на наши серверы. Удалить их можно кнопкой Очистить все."),
         ("Можно ли создать резюме с телефона?", "Да. MobilCV создан для телефона и также работает на компьютере."),
         ("Можно ли добавить фото в резюме?", "Да. Фото необязательно; нажмите на область фото, чтобы добавить его."),
         ("На каких языках можно создать резюме?", "На 10 языках: русский, английский, турецкий, немецкий, французский, испанский, итальянский, португальский, арабский и китайский."),
         ("Как скачать резюме?", "Заполнив форму, нажмите Скачать PDF. Резюме сохранится на вашем устройстве в виде PDF-файла.")],
    more="Советы по резюме и собеседованиям —",
    more_link=("https://mobilcv.net/ru/", "в нашем карьерном блоге"),
),
"ar": dict(
    h1="أنشئ سيرتك الذاتية مجانًا – بدون تسجيل",
    sub="أنشئ سيرة ذاتية احترافية من هاتفك بعشر لغات وحمّلها بصيغة PDF",
    steps_t="سيرتك الذاتية في 3 خطوات",
    steps=["اكتب بياناتك: معلومات الاتصال والخبرات والتعليم والمهارات، وأضف صورة إن أردت.",
           "اختر لون التصميم ولغة السيرة الذاتية، وشاهد كل تغيير فورًا في المعاينة.",
           "اضغط <b>تحميل PDF</b>، وتصبح سيرتك الذاتية جاهزة للإرسال."],
    why_t="لماذا MobilCV؟",
    why=["<b>مجاني بالكامل:</b> بلا رسوم خفية ولا فترة تجريبية ولا علامة مائية.",
         "<b>بدون تسجيل:</b> لا حاجة إلى بريد إلكتروني أو كلمة مرور أو حساب.",
         "<b>بياناتك تبقى معك:</b> تُحفظ السيرة الذاتية في متصفحك فقط ولا تُرسل إلى أي خادم.",
         "<b>مصمم للهاتف:</b> أنشئ سيرتك الذاتية في دقائق دون حاسوب.",
         "<b>10 لغات:</b> العربية والإنجليزية والتركية والألمانية والفرنسية والإسبانية والإيطالية والبرتغالية والروسية والصينية."],
    faq_t="الأسئلة الشائعة",
    faq=[("هل MobilCV مجاني فعلًا؟", "نعم. إنشاء السيرة الذاتية وتحميلها بصيغة PDF مجاني بالكامل، بلا رسوم خفية أو علامة مائية."),
         ("هل أحتاج إلى التسجيل؟", "لا. لا تحتاج إلى حساب أو بريد إلكتروني أو كلمة مرور، افتح الصفحة وابدأ."),
         ("أين تُحفظ بياناتي؟", "على جهازك فقط، في التخزين المحلي لمتصفحك، ولا تُرسل إلى خوادمنا أبدًا. يمكنك حذفها بزر مسح الكل."),
         ("هل يمكنني إنشاء السيرة الذاتية من الهاتف؟", "نعم. صُمم MobilCV للهاتف ويعمل أيضًا على الحاسوب."),
         ("هل يمكنني إضافة صورة؟", "نعم. الصورة اختيارية، اضغط على مكان الصورة لإضافتها."),
         ("بأي لغات يمكنني إنشاء سيرتي الذاتية؟", "بعشر لغات: العربية والإنجليزية والتركية والألمانية والفرنسية والإسبانية والإيطالية والبرتغالية والروسية والصينية."),
         ("كيف أحمّل سيرتي الذاتية؟", "بعد ملء النموذج اضغط تحميل PDF، فتُحفظ السيرة الذاتية على جهازك كملف PDF.")],
    more="لنصائح السيرة الذاتية والمقابلات",
    more_link=("https://mobilcv.net/ar/", "زر مدونتنا المهنية"),
),
"zh": dict(
    h1="免费制作简历 – 无需注册",
    sub="用手机以10种语言制作专业简历，并下载为PDF",
    steps_t="3步完成简历",
    steps=["填写您的信息：联系方式、工作经历、教育背景和技能，也可以添加照片。",
           "选择颜色主题和简历语言，每次修改都能在预览中即时看到。",
           "点击<b>下载PDF</b>，简历即可用于投递。"],
    why_t="为什么选择 MobilCV？",
    why=["<b>完全免费：</b>没有隐藏费用、没有试用期、没有水印。",
         "<b>无需注册：</b>不需要邮箱、密码或账号。",
         "<b>数据只属于您：</b>简历只保存在您的浏览器中，不会发送到任何服务器。",
         "<b>为手机设计：</b>无需电脑，几分钟即可完成简历。",
         "<b>10种语言：</b>中文、英语、土耳其语、德语、法语、西班牙语、意大利语、葡萄牙语、俄语和阿拉伯语。"],
    faq_t="常见问题",
    faq=[("MobilCV 真的免费吗？", "是的。制作简历并下载PDF完全免费，没有隐藏费用，也没有水印。"),
         ("需要注册吗？", "不需要。无需账号、邮箱或密码，打开页面即可开始。"),
         ("我的信息保存在哪里？", "只保存在您自己的设备上，即浏览器的本地存储中，不会发送到我们的服务器。可以用“全部清除”按钮删除。"),
         ("可以用手机制作简历吗？", "可以。MobilCV 专为手机设计，在电脑上也能使用。"),
         ("可以在简历中添加照片吗？", "可以。照片是可选的，点击照片区域即可添加。"),
         ("可以用哪些语言制作简历？", "共10种语言：中文、英语、土耳其语、德语、法语、西班牙语、意大利语、葡萄牙语、俄语和阿拉伯语。"),
         ("如何下载简历？", "填写完表格后点击“下载PDF”，简历会以PDF文件保存到您的设备。")],
    more="更多简历与面试技巧，",
    more_link=("https://mobilcv.net/zh/", "请访问我们的职业博客"),
),
}

START = "<!-- SEO_CONTENT_START -->"
END = "<!-- SEO_CONTENT_END -->"

CSS = """
        /* ===== SEO ICERIK BOLUMU (aracin altinda) ===== */
        .seo-info { width: 100%; max-width: 210mm; margin: 28px 0 0; background: #fff; border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06); padding: 28px 32px; color: #2c3e50; line-height: 1.65;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: start; }
        .seo-info h2 { font-size: 20px; margin: 22px 0 10px; color: #2c3e50; }
        .seo-info h2:first-child { margin-top: 0; }
        .seo-info ol, .seo-info ul { padding-inline-start: 22px; margin: 0 0 6px; }
        .seo-info li { margin-bottom: 6px; font-size: 15px; }
        .seo-info details { border-bottom: 1px solid #e5e7eb; padding: 10px 0; }
        .seo-info summary { cursor: pointer; font-weight: 600; font-size: 15px; list-style-position: inside; }
        .seo-info details p { margin: 8px 0 2px; font-size: 15px; color: #475569; }
        .seo-info .seo-more { margin-top: 18px; font-size: 14px; color: #475569; }
        .seo-info a { color: #2563eb; }
        @media (max-width: 768px) { .seo-info { width: calc(100vw - 20px); max-width: none; padding: 20px 18px; } }
        @media print { .seo-info { display: none !important; } }
"""


def esc(t):
    return html.escape(t, quote=False)


def block(code):
    d = C[code]
    steps = "".join(f"<li>{s}</li>" for s in d["steps"])
    why = "".join(f"<li>{s}</li>" for s in d["why"])
    faq = "".join(f"\n            <details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in d["faq"])
    url, label = d["more_link"]
    return f"""{START}
        <section class="seo-info" aria-labelledby="seo-steps-title"{' dir="rtl" lang="ar"' if code == "ar" else ''}>
            <h2 id="seo-steps-title">{esc(d['steps_t'])}</h2>
            <ol>{steps}</ol>
            <h2>{esc(d['why_t'])}</h2>
            <ul>{why}</ul>
            <h2>{esc(d['faq_t'])}</h2>{faq}
            <p class="seo-more">{esc(d['more'])} <a href="{url}" target="_blank" rel="noopener">{esc(label)}</a></p>
        </section>
        {END}"""


def faq_jsonld(code):
    data = {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                           for q, a in C[code]["faq"]]}
    return ('<script type="application/ld+json" data-seo-faq>\n'
            + json.dumps(data, ensure_ascii=False, indent=2) + "\n    </script>")


# ===================== YARDIMCILAR =====================
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


def sub_once(pattern, repl, text, name, flags=0, regex_repl=False, func=None):
    if func is not None:
        r = func
    elif regex_repl:
        r = repl
    else:
        r = lambda m: repl
    new, n = re.subn(pattern, r, text, count=1, flags=flags)
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


TR_TITLE = "Ücretsiz CV Hazırla – Üyeliksiz, Telefondan PDF | MobilCV"

FONT_LOADER = """<script data-pdf-font-loader>
    // PDF fontlari sayfa acilisini yavaslatmasin diye ayri dosyada; ilk etkilesimde veya
    // sayfa yuklendikten birkac saniye sonra, yalnizca gereken dil icin yuklenir.
    (function () {
        function load(src) {
            if (document.querySelector('script[src="' + src + '"]')) return;
            var s = document.createElement('script'); s.src = src; s.async = true; document.head.appendChild(s);
        }
        function need() {
            var sel = document.getElementById('language-select');
            var l = sel ? sel.value : (window.MOBILCV_PAGE_LANG || 'tr');
            if (l === 'zh') return;
            load(l === 'ar' ? '/pdf-font-arabic.js' : '/pdf-font-latin.js');
        }
        ['pointerdown', 'keydown', 'touchstart'].forEach(function (ev) {
            window.addEventListener(ev, need, { once: true, passive: true });
        });
        window.addEventListener('load', function () {
            setTimeout(need, 3000);
            var sel = document.getElementById('language-select');
            if (sel) sel.addEventListener('change', need);
        });
    })();
    </script>"""


def set_header(s, code):
    d = C[code]
    return sub_once(r'(<header class="header" role="banner">\s*)<h1>[^<]*</h1>(\s*)<p>[^<]*</p>',
                    f'\\g<1><h1>{esc(d["h1"])}</h1>\\g<2><p>{esc(d["sub"])}</p>', s, "header h1", regex_repl=True)


def set_seo_block(s, code):
    if START in s:
        return re.sub(re.escape(START) + r"[\s\S]*?" + re.escape(END), lambda m: block(code), s, count=1)
    return sub_once(r"</main>", "</main>\n\n        " + block(code), s, "</main>")


def set_faq(s, code):
    return sub_once(r'<script type="application/ld\+json"(?: data-seo-faq)?>\s*\{\s*"@context": "https://schema\.org",\s*"@type": "FAQPage"[\s\S]*?</script>',
                    faq_jsonld(code), s, "FAQ JSON-LD")


# ===================== CEREZ ONAYI (KVKK / GDPR) =====================
GA_ID = "G-7KFT12L3X8"
CONSENT = {
    "tr": ("Ziyaret istatistikleri için Google Analytics çerezlerini kullanmak istiyoruz. CV bilgileriniz bundan etkilenmez ve cihazınızda kalır.", "Kabul et", "Reddet", "Ayrıntılar", "Çerez ayarları"),
    "en": ("We'd like to use Google Analytics cookies to count visits. Your CV data is not affected and stays on your device.", "Accept", "Reject", "Details", "Cookie settings"),
    "de": ("Wir möchten Google-Analytics-Cookies verwenden, um Besuche zu zählen. Ihre Lebenslaufdaten sind davon nicht betroffen und bleiben auf Ihrem Gerät.", "Akzeptieren", "Ablehnen", "Details", "Cookie-Einstellungen"),
    "fr": ("Nous souhaitons utiliser des cookies Google Analytics pour mesurer les visites. Les données de votre CV ne sont pas concernées et restent sur votre appareil.", "Accepter", "Refuser", "Détails", "Paramètres des cookies"),
    "es": ("Queremos usar cookies de Google Analytics para contar las visitas. Los datos de tu currículum no se ven afectados y se quedan en tu dispositivo.", "Aceptar", "Rechazar", "Detalles", "Configuración de cookies"),
    "it": ("Vorremmo usare i cookie di Google Analytics per contare le visite. I dati del tuo CV non sono coinvolti e restano sul tuo dispositivo.", "Accetta", "Rifiuta", "Dettagli", "Impostazioni cookie"),
    "pt": ("Gostaríamos de usar cookies do Google Analytics para contar as visitas. Os dados do seu currículo não são afetados e ficam no seu dispositivo.", "Aceitar", "Recusar", "Detalhes", "Configurações de cookies"),
    "ru": ("Мы хотим использовать файлы cookie Google Analytics для подсчёта посещений. Данные вашего резюме это не затрагивает — они остаются на вашем устройстве.", "Принять", "Отклонить", "Подробнее", "Настройки cookie"),
    "ar": ("نود استخدام ملفات تعريف الارتباط من Google Analytics لإحصاء الزيارات. لا يتأثر محتوى سيرتك الذاتية ويبقى على جهازك.", "قبول", "رفض", "التفاصيل", "إعدادات ملفات تعريف الارتباط"),
    "zh": ("我们希望使用 Google Analytics Cookie 统计访问量。您的简历数据不受影响，仍只保存在您的设备上。", "接受", "拒绝", "详情", "Cookie 设置"),
}

CONSENT_CSS = """
        /* ===== CEREZ ONAY BANDI ===== */
        #cookie-consent { position: fixed; left: 12px; right: 12px; bottom: 12px; z-index: 2147483000; max-width: 640px; margin: 0 auto;
            background: #fff; color: #1f2937; border-radius: 14px; box-shadow: 0 8px 30px rgba(0,0,0,0.25); padding: 14px 16px;
            font: 14px/1.5 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: none; }
        #cookie-consent.show { display: block; }
        #cookie-consent p { margin: 0 0 10px; }
        #cookie-consent a { color: #2563eb; }
        #cookie-consent .cc-btns { display: flex; gap: 10px; }
        #cookie-consent button { flex: 1; padding: 10px 12px; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer;
            border: 2px solid #2563eb; }
        #cookie-consent .cc-accept { background: #2563eb; color: #fff; }
        #cookie-consent .cc-reject { background: #fff; color: #2563eb; }
        @media print { #cookie-consent { display: none !important; } }
"""


def consent_script():
    data = {c: {"msg": v[0], "ok": v[1], "no": v[2], "more": v[3], "set": v[4], "url": PRIVACY[c][0]} for c, v in CONSENT.items()}
    return ("""<script data-consent>
    // Google Analytics YALNIZCA ziyaretci "Kabul et" derse yuklenir (KVKK / GDPR).
    (function () {
        var GA = '""" + GA_ID + """', KEY = 'mobilcv_consent';
        var T = """ + json.dumps(data, ensure_ascii=False) + """;
        function get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
        function put(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }
        function lang() {
            var s = document.getElementById('language-select');
            var l = (s && s.value) || window.MOBILCV_PAGE_LANG || 'tr';
            return T[l] ? l : 'en';
        }
        function loadGA() {
            if (window.__gaLoaded) return; window.__gaLoaded = true;
            window.dataLayer = window.dataLayer || [];
            window.gtag = function () { dataLayer.push(arguments); };
            gtag('js', new Date()); gtag('config', GA);
            var s = document.createElement('script'); s.async = true;
            s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA; document.head.appendChild(s);
        }
        function clearGA() {
            var host = location.hostname.replace(/^www\\./, '');
            document.cookie.split(';').forEach(function (c) {
                var n = c.split('=')[0].trim();
                if (n === '_ga' || n.indexOf('_ga_') === 0 || n === '_gid') {
                    ['', '.' + host, location.hostname].forEach(function (d) {
                        document.cookie = n + '=; Max-Age=0; path=/' + (d ? '; domain=' + d : '');
                    });
                }
            });
        }
        var box;
        function render() {
            var t = T[lang()];
            box.setAttribute('dir', lang() === 'ar' ? 'rtl' : 'ltr');
            box.innerHTML = '<p>' + t.msg + ' <a href="' + t.url + '" target="_blank" rel="noopener">' + t.more + '</a></p>' +
                '<div class="cc-btns"><button type="button" class="cc-reject">' + t.no + '</button>' +
                '<button type="button" class="cc-accept">' + t.ok + '</button></div>';
            box.querySelector('.cc-accept').onclick = function () { put('granted'); box.classList.remove('show'); loadGA(); };
            box.querySelector('.cc-reject').onclick = function () {
                var was = window.__gaLoaded; put('denied'); clearGA(); box.classList.remove('show');
                if (was) location.reload();
            };
            document.querySelectorAll('[data-cookie-settings]').forEach(function (a) { a.textContent = t.set; });
        }
        function show() { render(); box.classList.add('show'); }
        document.addEventListener('DOMContentLoaded', function () {
            box = document.createElement('div'); box.id = 'cookie-consent';
            box.setAttribute('role', 'dialog'); box.setAttribute('aria-live', 'polite');
            document.body.appendChild(box); render();
            var v = get();
            if (v === 'granted') loadGA(); else if (v !== 'denied') box.classList.add('show');
            document.querySelectorAll('[data-cookie-settings]').forEach(function (a) {
                a.addEventListener('click', function (e) { e.preventDefault(); show(); });
            });
            var sel = document.getElementById('language-select');
            if (sel) sel.addEventListener('change', function () { setTimeout(render, 0); });
        });
    })();
    </script>""")


def consent_upgrade(s):
    """Tawk.to'yu kaldirir, Google Analytics'i onay bandinin arkasina alir. Tekrar calistirmak zararsizdir."""
    # 1) Tawk.to canli sohbet
    s = re.sub(r"[ \t]*<!--Start of Tawk\.to Script-->\s*<!-- Tawk\.to[^>]*-->\s*<!--Start of Tawk\.to Script-->\s*"
               r"<script type=\"text/javascript\">\s*var Tawk_API[\s\S]*?</script>\s*<!--End of Tawk\.to Script-->\s*", "\n", s)
    if "embed.tawk.to" in s:
        sys.exit("HATA: Tawk.to kodu beklenen bicimde degil; script durduruldu, hicbir dosya degismedi.")
    # 2) Dogrudan yuklenen Google Analytics
    if "data-consent" not in s:
        s = sub_once(r"[ \t]*<!-- Google Analytics -->\s*<script async src=\"https://www\.googletagmanager\.com/gtag/js\?id=" + GA_ID +
                     r"\"></script>\s*<script>\s*window\.dataLayer[\s\S]*?gtag\('config', '" + GA_ID + r"'\);\s*</script>\s*",
                     "    <!-- Google Analytics: yalnizca onay verilirse yuklenir (sayfa sonundaki data-consent) -->\n", s,
                     "Google Analytics blogu")
        s = sub_once(r"</style>\s*</head>", CONSENT_CSS + "    </style>\n</head>", s, "</style></head> (cerez)")
        s = sub_once(r"</body>\s*</html>\s*$", "    " + consent_script() + "\n</body>\n</html>\n", s, "</body> (cerez)")
    else:
        s = re.sub(r"<script data-consent>[\s\S]*?</script>", lambda m: consent_script(), s, count=1)
    if "googletagmanager.com/gtag/js?id=" + GA_ID + "\"></script>" in s:
        sys.exit("HATA: Google Analytics hala dogrudan yukleniyor; script durduruldu.")
    # 3) Alt kisma "Cerez ayarlari" linki
    if 'data-cookie-settings style=' not in s:
        s = sub_once(r'(<a href="[^"]*" target="_blank" rel="noopener me" style="font-size:12px;">Threads</a>)', None, s,
                     "Threads linki (cerez ayarlari)",
                     func=lambda m: m.group(1) + ' · <a href="#" data-cookie-settings style="font-size:12px;">' + CONSENT["tr"][4] + '</a>')
    # 4) Eski yorumlardaki Tawk.to aciklamasini guncelle (yalnizca yorum)
    s = s.replace("GA ve Tawk.to script'lerine kasıtlı olarak SRI eklenmedi", "GA script'ine kasıtlı olarak SRI eklenmedi")
    return s


def seo_upgrade(src, fonts_out):
    """Kok (Turkce) sayfaya SEO icerigini ekler / gunceller. Tekrar calistirmak zararsizdir."""
    s = set_header(src, "tr")
    # JS'in dil degisince yazdigi baslik da ayni olsun (sira: tr en de fr es it pt ru ar zh)
    order = ["tr", "en", "de", "fr", "es", "it", "pt", "ru", "ar", "zh"]
    for key, field in (("appTitle", "h1"), ("appDescription", "sub")):
        it = iter(order)
        s, n = re.subn(rf'"{key}":(\s*)"[^"]*"', lambda m: f'"{key}":{m.group(1)}"{C[next(it)][field]}"', s)
        if n != 10:
            sys.exit(f"HATA: {key} ceviri sayisi 10 degil ({n}); script durduruldu, hicbir dosya degismedi.")
    # Turkce baslik
    s = sub_once(r"<title>[^<]*</title>", f"<title>{TR_TITLE}</title>", s, "title")
    s = sub_once(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{TR_TITLE}">', s, "og:title")
    s = sub_once(r'<meta name="twitter:title" content="[^"]*">', f'<meta name="twitter:title" content="{TR_TITLE}">', s, "twitter:title")
    # Kok canonical, hreflang ile ayni (sonda / ile)
    s = s.replace('<link rel="canonical" href="https://www.mobilcv.com">', '<link rel="canonical" href="https://www.mobilcv.com/">')
    # Hata duzeltmesi: alttaki sabit bardaki "PDF Indir" yazisi diger dillerde Turkce kaliyordu
    s = s.replace("(t.downloadPdf || 'PDF İndir')", "(t.savePDF || t.downloadPdf || 'PDF İndir')")
    # CSS
    if ".seo-info {" not in s:
        s = sub_once(r"</style>\s*</head>", CSS + "    </style>\n</head>", s, "</style></head>")
    # Gorunur SSS bolumu + FAQ verisi
    s = set_seo_block(s, "tr")
    s = set_faq(s, "tr")
    # PDF fontlarini ayri dosyalara tasi
    for const, fname in (("CV_PDF_FONT_BASE64", "pdf-font-latin.js"), ("CV_PDF_FONT_ARABIC_BASE64", "pdf-font-arabic.js")):
        m = re.search(rf'const {const} = "([A-Za-z0-9+/=]+)";', s)
        if m:
            fonts_out[fname] = f'window.{const}="{m.group(1)}";\n'
            s = s[:m.start()] + f"// {const}: /{fname} dosyasindan, gerektiginde yuklenir." + s[m.end():]
            s = sub_once(rf"doc\.addFileToVFS\('([A-Za-z]+)\.ttf', {const}\);",
                         None, s, f"{const} kullanimi", regex_repl=True,
                         func=lambda mm, c=const: (f"if (!window.{c}) throw new Error('PDF fontu henuz yuklenmedi');\n"
                                                   f"                        doc.addFileToVFS('{mm.group(1)}.ttf', window.{c});"))
    if "data-extra-i18n" not in s:
        s = sub_once(r"</body>\s*</html>\s*$", "    " + EXTRA_I18N + "\n</body>\n</html>\n", s, "</body> (i18n)")
    if "data-pdf-font-loader" not in s:
        s = sub_once(r"</body>\s*</html>\s*$", "    " + FONT_LOADER + "\n</body>\n</html>\n", s, "</body>")
    return s


# Sayfada gozle gorunmeyen ama Google'in okudugu sabit metinler (dil sayfalarinda Turkce kaliyordu)
STATIC_TR = ["Ana içeriğe atla", "CV Oluşturucu", "CV Kontrolleri", "CV Formu", "İptal", "Bayrak", "Fotoğraf", "Takvimden seç"]
STATIC = {
    "en": ["Skip to main content", "CV Builder", "CV Controls", "CV Form", "Cancel", "Flag", "Photo", "Pick from calendar"],
    "de": ["Zum Hauptinhalt springen", "Lebenslauf-Editor", "Lebenslauf-Steuerung", "Lebenslauf-Formular", "Abbrechen", "Flagge", "Foto", "Aus Kalender wählen"],
    "fr": ["Aller au contenu principal", "Créateur de CV", "Commandes du CV", "Formulaire du CV", "Annuler", "Drapeau", "Photo", "Choisir dans le calendrier"],
    "es": ["Saltar al contenido principal", "Creador de currículum", "Controles del currículum", "Formulario del currículum", "Cancelar", "Bandera", "Foto", "Elegir en el calendario"],
    "it": ["Vai al contenuto principale", "Creatore di CV", "Comandi del CV", "Modulo del CV", "Annulla", "Bandiera", "Foto", "Scegli dal calendario"],
    "pt": ["Ir para o conteúdo principal", "Criador de currículo", "Controles do currículo", "Formulário do currículo", "Cancelar", "Bandeira", "Foto", "Escolher no calendário"],
    "ru": ["Перейти к основному содержанию", "Конструктор резюме", "Управление резюме", "Форма резюме", "Отмена", "Флаг", "Фото", "Выбрать в календаре"],
    "ar": ["انتقل إلى المحتوى الرئيسي", "منشئ السيرة الذاتية", "أدوات السيرة الذاتية", "نموذج السيرة الذاتية", "إلغاء", "العلم", "الصورة", "اختر من التقويم"],
    "zh": ["跳到主要内容", "简历生成器", "简历控制", "简历表单", "取消", "国旗", "照片", "从日历选择"],
}
ORDER = ["tr", "en", "de", "fr", "es", "it", "pt", "ru", "ar", "zh"]

# Dil degisince title / aria-label metinlerini de cevir (sitenin kendi ceviri kodu bunlari atliyordu)
EXTRA_I18N = """<script data-extra-i18n>
    (function () {
        function apply() {
            var sel = document.getElementById('language-select');
            if (!sel || typeof translations === 'undefined') return;
            var t = translations[sel.value] || translations.tr;
            document.querySelectorAll('[data-key-title]').forEach(function (el) {
                var v = t[el.getAttribute('data-key-title')]; if (v) el.title = v;
            });
            var th = document.getElementById('theme-options');
            if (th && t.selectTheme) th.setAttribute('aria-label', t.selectTheme);
        }
        document.addEventListener('DOMContentLoaded', function () {
            apply();
            var sel = document.getElementById('language-select');
            if (sel) sel.addEventListener('change', function () { setTimeout(apply, 0); });
        });
    })();
    </script>"""


def tr_value(root, key, code):
    vals = re.findall(rf'"{key}":\s*"([^"]*)"', root)
    return vals[ORDER.index(code)] if len(vals) == 10 else None


def localize_static(s, code, root):
    tr, loc = STATIC_TR, STATIC[code]
    pairs = [
        ('class="skip-link sr-only">' + tr[0] + "</a>", 'class="skip-link sr-only">' + loc[0] + "</a>"),
        ('class="sr-only">' + tr[1] + "</h2>", 'class="sr-only">' + loc[1] + "</h2>"),
        ('class="sr-only">' + tr[2] + "</h2>", 'class="sr-only">' + loc[2] + "</h2>"),
        ('class="sr-only">' + tr[3] + "</h2>", 'class="sr-only">' + loc[3] + "</h2>"),
        ('id="date-picker-cancel">' + tr[4] + "</button>", 'id="date-picker-cancel">' + loc[4] + "</button>"),
        ("flagElement.alt = '" + tr[5] + "';", "flagElement.alt = '" + loc[5] + "';"),
        ('<img id="avatar" alt="' + tr[6] + '"', '<img id="avatar" alt="' + loc[6] + '"'),
        ('title="' + tr[7] + '"', 'title="' + loc[7] + '"'),
    ]
    for a, b in pairs:
        s = s.replace(a, b)
    # data-key-title olan dugmelerin title'i ve tema grubunun aria-label'i
    s = re.sub(r'title="[^"]*"( data-key-title="(\w+)")',
               lambda m: f'title="{tr_value(root, m.group(2), code) or ""}"{m.group(1)}', s)
    th = tr_value(root, "selectTheme", code)
    if th:
        s = re.sub(r'(id="theme-options"[^>]*aria-label=")[^"]*"', lambda m: m.group(1) + th + '"', s)
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
    # Ana baslik, gorunur SSS bolumu ve FAQ verisi bu dilde
    s = set_header(s, code)
    s = set_seo_block(s, code)
    s = set_faq(s, code)
    s = localize_static(s, code, root)
    s = s.replace('data-cookie-settings style="font-size:12px;">' + CONSENT["tr"][4] + "<",
                  'data-cookie-settings style="font-size:12px;">' + CONSENT[code][4] + "<")
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
    fonts = {}
    root = consent_upgrade(seo_upgrade(add_social(add_privacy_link(patch_root(src))), fonts))
    pages = {c: make_lang_page(root, c, d) for c, d in LANGS.items()}  # once hepsini hazirla, hata varsa hicbir sey yazilmaz

    if root != src:
        shutil.copy(p, "index.html.yedek")
        p.write_text(root, encoding="utf-8")
        print("index.html duzeltildi (yedek: index.html.yedek)")
    for fname, js in fonts.items():
        Path(fname).write_text(js, encoding="utf-8")
        print(f"{fname} yazildi (PDF fontu sayfadan ayrildi)")
    for c, page in pages.items():
        Path(c).mkdir(exist_ok=True)
        (Path(c) / "index.html").write_text(page, encoding="utf-8")
        print(f"{c}/index.html olusturuldu  ->  {url_of(c)}")

    target = Path("sitemap.xml")
    if target.exists():
        target = Path("sitemap-diller.xml")
    target.write_text(sitemap(), encoding="utf-8")
    print(f"{target} yazildi.")
    print("\nTAMAM. Simdi degisiklikleri GitHub'a gonderin (commit + push).")


if __name__ == "__main__":
    main()
