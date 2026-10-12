"""
Curated Piper voice catalog for Fahad's TTS Platform.

Voice keys match rhasspy/piper-voices. Gender labels are best-effort
(from voice/dataset names). "unknown" means it could not be determined.
Child voices are not available in the Piper voice collection yet.
"""

# (voice_key, display_name, language_code, language_name, gender, starred)
VOICES = [
    # ---------- English (US) ----------
    ("en_US-lessac-medium", "Lessac — Deep Narrator", "en_US", "English (US)", "male", True),
    ("en_US-ryan-medium", "Ryan", "en_US", "English (US)", "male", True),
    ("en_US-bryce-medium", "Bryce", "en_US", "English (US)", "male", False),
    ("en_US-danny-low", "Danny", "en_US", "English (US)", "male", False),
    ("en_US-joe-medium", "Joe", "en_US", "English (US)", "male", False),
    ("en_US-john-medium", "John", "en_US", "English (US)", "male", False),
    ("en_US-mike-medium", "Mike", "en_US", "English (US)", "male", False),
    ("en_US-norman-medium", "Norman", "en_US", "English (US)", "male", False),
    ("en_US-sam-medium", "Sam", "en_US", "English (US)", "male", False),
    ("en_US-amy-medium", "Amy", "en_US", "English (US)", "female", True),
    ("en_US-kristin-medium", "Kristin", "en_US", "English (US)", "female", True),
    ("en_US-kathleen-low", "Kathleen", "en_US", "English (US)", "female", False),
    ("en_US-ljspeech-medium", "LJSpeech", "en_US", "English (US)", "female", False),
    # ---------- English (UK) ----------
    ("en_GB-alan-medium", "Alan (British)", "en_GB", "English (UK)", "male", True),
    ("en_GB-northern_english_male-medium", "Northern English Male", "en_GB", "English (UK)", "male", False),
    ("en_GB-jenny_dioco-medium", "Jenny (British)", "en_GB", "English (UK)", "female", False),
    ("en_GB-alba-medium", "Alba (British)", "en_GB", "English (UK)", "female", False),
    ("en_GB-aru-medium", "Aru (British)", "en_GB", "English (UK)", "female", False),
    ("en_GB-cori-medium", "Cori (British)", "en_GB", "English (UK)", "female", False),
    # ---------- Urdu ----------
    ("ur_PK-fasih-medium", "Fasih (Urdu)", "ur_PK", "Urdu", "male", True),
    ("ur_PK-aegis_female-medium", "Aegis (Urdu)", "ur_PK", "Urdu", "female", True),
    # ---------- Hindi ----------
    ("hi_IN-pratham-medium", "Pratham (Hindi)", "hi_IN", "Hindi", "male", True),
    ("hi_IN-rohan-medium", "Rohan (Hindi)", "hi_IN", "Hindi", "male", False),
    ("hi_IN-priyamvada-medium", "Priyamvada (Hindi)", "hi_IN", "Hindi", "female", True),
    # ---------- Arabic ----------
    ("ar_JO-kareem-medium", "Kareem (Arabic)", "ar_JO", "Arabic", "male", True),
    # ---------- Spanish ----------
    ("es_ES-davefx-medium", "Davefx (Spain)", "es_ES", "Spanish (Spain)", "male", True),
    ("es_ES-sharvard-medium", "Sharvard (Spain)", "es_ES", "Spanish (Spain)", "male", False),
    ("es_MX-claude-high", "Claude (Mexico)", "es_MX", "Spanish (Mexico)", "male", False),
    ("es_AR-daniela-high", "Daniela (Argentina)", "es_AR", "Spanish (Argentina)", "female", True),
    # ---------- French ----------
    ("fr_FR-tom-medium", "Tom", "fr_FR", "French", "male", True),
    ("fr_FR-gilles-low", "Gilles", "fr_FR", "French", "male", False),
    ("fr_FR-siwis-medium", "Siwis", "fr_FR", "French", "female", True),
    # ---------- German ----------
    ("de_DE-thorsten-medium", "Thorsten", "de_DE", "German", "male", True),
    ("de_DE-eva_k-x_low", "Eva", "de_DE", "German", "female", False),
    ("de_DE-kerstin-low", "Kerstin", "de_DE", "German", "female", False),
    # ---------- Dutch ----------
    ("nl_NL-alex-medium", "Alex", "nl_NL", "Dutch", "male", False),
    ("nl_BE-nathalie-medium", "Nathalie", "nl_BE", "Dutch (Belgium)", "female", False),
    # ---------- Italian ----------
    ("it_IT-riccardo-x_low", "Riccardo", "it_IT", "Italian", "male", False),
    ("it_IT-serena-medium", "Serena", "it_IT", "Italian", "female", False),
    # ---------- Portuguese ----------
    ("pt_BR-cadu-medium", "Cadu", "pt_BR", "Portuguese (Brazil)", "male", False),
    ("pt_BR-faber-medium", "Faber", "pt_BR", "Portuguese (Brazil)", "male", False),
    # ---------- Farsi ----------
    ("fa_IR-amir-medium", "Amir (Farsi)", "fa_IR", "Farsi", "male", False),
    # ---------- Bengali ----------
    ("bn_BD-google-medium", "Bengali Voice", "bn_BD", "Bengali", "unknown", False),
    # ---------- Turkish ----------
    ("tr_TR-dfki-medium", "Turkish Voice", "tr_TR", "Turkish", "unknown", False),
    # ---------- Russian ----------
    ("ru_RU-dmitri-medium", "Dmitri", "ru_RU", "Russian", "male", False),
    ("ru_RU-irina-medium", "Irina", "ru_RU", "Russian", "female", False),
    # ---------- Ukrainian ----------
    ("uk_UA-mykyta-high", "Mykyta", "uk_UA", "Ukrainian", "male", False),
    ("uk_UA-tetiana-high", "Tetiana", "uk_UA", "Ukrainian", "female", False),
    # ---------- Polish ----------
    ("pl_PL-darkman-medium", "Darkman", "pl_PL", "Polish", "male", False),
    ("pl_PL-gosia-medium", "Gosia", "pl_PL", "Polish", "female", False),
    # ---------- Chinese ----------
    ("zh_CN-huayan-medium", "Huayan (Chinese)", "zh_CN", "Chinese", "female", False),
    # ---------- Japanese ----------
    ("ja_JP-hi_fi_captain-medium", "Captain (Japanese)", "ja_JP", "Japanese", "unknown", False),
]

DEFAULT_VOICE = "en_US-lessac-medium"


def voice_list():
    return [
        {
            "id": key,
            "name": name,
            "lang": lang,
            "language": language,
            "gender": gender,
            "starred": starred,
        }
        for (key, name, lang, language, gender, starred) in VOICES
    ]


def voice_ids():
    return {key for (key, _, _, _, _, _) in VOICES}


def languages():
    seen = {}
    for (_, _, lang, language, _, _) in VOICES:
        seen[lang] = language
    return [{"code": c, "name": n} for c, n in sorted(seen.items(), key=lambda x: x[1])]
