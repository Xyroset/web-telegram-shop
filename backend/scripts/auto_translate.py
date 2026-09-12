import argparse
import json
import random
import re
import time
from pathlib import Path
from typing import TypeAlias

from deep_translator import GoogleTranslator, MyMemoryTranslator
from deep_translator.exceptions import LanguageNotSupportedException
from prints import Prints

PROTECTED_PATTERN = re.compile(r"(<[^>]+>|\{[^\}]+\}|\%\([a-zA-Z0-9_]+\)[s|d])")
BASE_LANG = "en"

JSONType: TypeAlias = dict[str, "JSONType"] | list["JSONType"] | str | int | float | bool | None


MYMEMORY_LANG_MAP: dict[str, str] = {
    "acehnese": "ace-ID",
    "afrikaans": "af-ZA",
    "akan": "ak-GH",
    "albanian": "sq-AL",
    "amharic": "am-ET",
    "antigua and barbuda creole english": "aig-AG",
    "arabic": "ar-SA",
    "arabic egyptian": "ar-EG",
    "aragonese": "an-ES",
    "armenian": "hy-AM",
    "assamese": "as-IN",
    "asturian": "ast-ES",
    "austrian german": "de-AT",
    "awadhi": "awa-IN",
    "ayacucho quechua": "quy-PE",
    "azerbaijani": "az-AZ",
    "bahamas creole english": "bah-BS",
    "bajan": "bjs-BB",
    "balinese": "ban-ID",
    "balkan gipsy": "rm-RO",
    "bambara": "bm-ML",
    "banjar": "bjn-ID",
    "bashkir": "ba-RU",
    "basque": "eu-ES",
    "belarusian": "be-BY",
    "belgian french": "fr-BE",
    "bemba": "bem-ZM",
    "bengali": "bn-IN",
    "bhojpuri": "bho-IN",
    "bihari": "bh-IN",
    "bislama": "bi-VU",
    "borana": "gax-KE",
    "bosnian": "bs-BA",
    "bosnian (cyrillic)": "bs-Cyrl-BA",
    "breton": "br-FR",
    "buginese": "bug-ID",
    "bulgarian": "bg-BG",
    "burmese": "my-MM",
    "catalan": "ca-ES",
    "catalan valencian": "cav-ES",
    "cebuano": "ceb-PH",
    "central atlas tamazight": "tzm-MA",
    "central aymara": "ayr-BO",
    "central kanuri (latin script)": "knc-NG",
    "chadian arabic": "shu-TD",
    "chamorro": "ch-GU",
    "cherokee": "chr-US",
    "chhattisgarhi": "hne-IN",
    "chinese simplified": "zh-CN",
    "chinese trad. (hong kong)": "zh-HK",
    "chinese traditional": "zh-TW",
    "chinese traditional macau": "zh-MO",
    "chittagonian": "ctg-BD",
    "chokwe": "cjk-AO",
    "classical greek": "grc-GR",
    "comorian ngazidja": "zdj-KM",
    "coptic": "cop-EG",
    "crimean tatar": "crh-RU",
    "crioulo upper guinea": "pov-GW",
    "croatian": "hr-HR",
    "czech": "cs-CZ",
    "danish": "da-DK",
    "dari": "prs-AF",
    "dimli": "diq-TR",
    "dutch": "nl-NL",
    "dyula": "dyu-CI",
    "dzongkha": "dz-BT",
    "eastern yiddish": "ydd-US",
    "emakhuwa": "vmw-MZ",
    "english": "en-GB",
    "english australia": "en-AU",
    "english canada": "en-CA",
    "english india": "en-IN",
    "english ireland": "en-IE",
    "english new zealand": "en-NZ",
    "english singapore": "en-SG",
    "english south africa": "en-ZA",
    "english us": "en-US",
    "esperanto": "eo-EU",
    "estonian": "et-EE",
    "ewe": "ee-GH",
    "fanagalo": "fn-FNG",
    "faroese": "fo-FO",
    "fijian": "fj-FJ",
    "filipino": "fil-PH",
    "finnish": "fi-FI",
    "flemish": "nl-BE",
    "fon": "fon-BJ",
    "french": "fr-FR",
    "french canada": "fr-CA",
    "french swiss": "fr-CH",
    "friulian": "fur-IT",
    "fula": "ff-FUL",
    "galician": "gl-ES",
    "gamargu": "mfi-NG",
    "garo": "grt-IN",
    "georgian": "ka-GE",
    "german": "de-DE",
    "gilbertese": "gil-KI",
    "glavda": "glw-NG",
    "greek": "el-GR",
    "grenadian creole english": "gcl-GD",
    "guarani": "gn-PY",
    "gujarati": "gu-IN",
    "guyanese creole english": "gyn-GY",
    "haitian creole french": "ht-HT",
    "halh mongolian": "khk-MN",
    "hausa": "ha-NE",
    "hawaiian": "haw-US",
    "hebrew": "he-IL",
    "higi": "hig-NG",
    "hiligaynon": "hil-PH",
    "hill mari": "mrj-RU",
    "hindi": "hi-IN",
    "hmong": "hmn-CN",
    "hungarian": "hu-HU",
    "icelandic": "is-IS",
    "igbo ibo": "ibo-NG",
    "igbo ig": "ig-NG",
    "ilocano": "ilo-PH",
    "indonesian": "id-ID",
    "inuktitut greenlandic": "kl-GL",
    "irish gaelic": "ga-IE",
    "italian": "it-IT",
    "italian swiss": "it-CH",
    "jamaican creole english": "jam-JM",
    "japanese": "ja-JP",
    "javanese": "jv-ID",
    "jingpho": "kac-MM",
    "k'iche'": "quc-GT",
    "kabiyè": "kbp-TG",
    "kabuverdianu": "kea-CV",
    "kabylian": "kab-DZ",
    "kalenjin": "kln-KE",
    "kamba": "kam-KE",
    "kannada": "kn-IN",
    "kanuri": "kr-KAU",
    "karen": "kar-MM",
    "kashmiri (devanagari script)": "ks-IN",
    "kashmiri (arabic script)": "kas-IN",
    "kazakh": "kk-KZ",
    "khasi": "kha-IN",
    "khmer": "km-KH",
    "kikuyu kik": "kik-KE",
    "kikuyu ki": "ki-KE",
    "kimbundu": "kmb-AO",
    "kinyarwanda": "rw-RW",
    "kirundi": "rn-BI",
    "kisii": "guz-KE",
    "kongo": "kg-CG",
    "konkani": "kok-IN",
    "korean": "ko-KR",
    "northern kurdish": "kmr-TR",
    "kurdish sorani": "ckb-IQ",
    "kyrgyz": "ky-KG",
    "lao": "lo-LA",
    "latgalian": "ltg-LV",
    "latin": "la-XN",
    "latvian": "lv-LV",
    "ligurian": "lij-IT",
    "limburgish": "li-NL",
    "lingala": "ln-LIN",
    "lithuanian": "lt-LT",
    "lombard": "lmo-IT",
    "luba-kasai": "lua-CD",
    "luganda": "lg-UG",
    "luhya": "luy-KE",
    "luo": "luo-KE",
    "luxembourgish": "lb-LU",
    "maa": "mas-KE",
    "macedonian": "mk-MK",
    "magahi": "mag-IN",
    "maithili": "mai-IN",
    "malagasy": "mg-MG",
    "malay": "ms-MY",
    "malayalam": "ml-IN",
    "maldivian": "dv-MV",
    "maltese": "mt-MT",
    "mandara": "mfi-CM",
    "manipuri": "mni-IN",
    "manx gaelic": "gv-IM",
    "maori": "mi-NZ",
    "marathi": "mr-IN",
    "margi": "mrt-NG",
    "mari": "mhr-RU",
    "marshallese": "mh-MH",
    "mende": "men-SL",
    "meru": "mer-KE",
    "mijikenda": "nyf-KE",
    "minangkabau": "min-ID",
    "mizo": "lus-IN",
    "mongolian": "mn-MN",
    "montenegrin": "sr-ME",
    "morisyen": "mfe-MU",
    "moroccan arabic": "ar-MA",
    "mossi": "mos-BF",
    "ndau": "ndc-MZ",
    "ndebele": "nr-ZA",
    "nepali": "ne-NP",
    "nigerian fulfulde": "fuv-NG",
    "niuean": "niu-NU",
    "north azerbaijani": "azj-AZ",
    "sesotho": "nso-ZA",
    "northern uzbek": "uzn-UZ",
    "norwegian bokmål": "nb-NO",
    "norwegian nynorsk": "nn-NO",
    "nuer": "nus-SS",
    "nyanja": "ny-MW",
    "occitan": "oc-FR",
    "occitan aran": "oc-ES",
    "odia": "or-IN",
    "oriya": "ory-IN",
    "urdu": "ur-PK",
    "palauan": "pau-PW",
    "pali": "pi-IN",
    "pangasinan": "pag-PH",
    "papiamentu": "pap-CW",
    "pashto": "ps-PK",
    "persian": "fa-IR",
    "pijin": "pis-SB",
    "plateau malagasy": "plt-MG",
    "polish": "pl-PL",
    "portuguese": "pt-PT",
    "portuguese brazil": "pt-BR",
    "potawatomi": "pot-US",
    "punjabi": "pa-IN",
    "punjabi (pakistan)": "pnb-PK",
    "quechua": "qu-PE",
    "rohingya": "rhg-MM",
    "rohingyalish": "rhl-MM",
    "romanian": "ro-RO",
    "romansh": "roh-CH",
    "rundi": "run-BI",
    "russian": "ru-RU",
    "saint lucian creole french": "acf-LC",
    "samoan": "sm-WS",
    "sango": "sg-CF",
    "sanskrit": "sa-IN",
    "santali": "sat-IN",
    "sardinian": "sc-IT",
    "scots gaelic": "gd-GB",
    "sena": "seh-ZW",
    "serbian cyrillic": "sr-Cyrl-RS",
    "serbian latin": "sr-Latn-RS",
    "seselwa creole french": "crs-SC",
    "setswana (south africa)": "tn-ZA",
    "shan": "shn-MM",
    "shona": "sn-ZW",
    "sicilian": "scn-IT",
    "silesian": "szl-PL",
    "sindhi snd": "snd-PK",
    "sindhi sd": "sd-PK",
    "sinhala": "si-LK",
    "slovak": "sk-SK",
    "slovenian": "sl-SI",
    "somali": "so-SO",
    "sotho southern": "st-LS",
    "south azerbaijani": "azb-AZ",
    "southern pashto": "pbt-PK",
    "southwestern dinka": "dik-SS",
    "spanish": "es-ES",
    "spanish argentina": "es-AR",
    "spanish colombia": "es-CO",
    "spanish latin america": "es-419",
    "spanish mexico": "es-MX",
    "spanish united states": "es-US",
    "sranan tongo": "srn-SR",
    "standard latvian": "lvs-LV",
    "standard malay": "zsm-MY",
    "sundanese": "su-ID",
    "swahili": "sw-KE",
    "swati": "ss-SZ",
    "swedish": "sv-SE",
    "swiss german": "de-CH",
    "syriac (aramaic)": "syc-TR",
    "tagalog": "tl-PH",
    "tahitian": "ty-PF",
    "tajik": "tg-TJ",
    "tamashek (tuareg)": "tmh-DZ",
    "tamasheq": "taq-ML",
    "tamil india": "ta-IN",
    "tamil sri lanka": "ta-LK",
    "taroko": "trv-TW",
    "tatar": "tt-RU",
    "telugu": "te-IN",
    "tetum": "tet-TL",
    "thai": "th-TH",
    "tibetan": "bo-CN",
    "tigrinya": "ti-ET",
    "tok pisin": "tpi-PG",
    "tokelauan": "tkl-TK",
    "tongan": "to-TO",
    "tosk albanian": "als-AL",
    "tsonga": "ts-ZA",
    "tswa": "tsc-MZ",
    "tswana": "tn-BW",
    "tumbuka": "tum-MW",
    "turkish": "tr-TR",
    "turkmen": "tk-TM",
    "tuvaluan": "tvl-TV",
    "twi": "tw-GH",
    "udmurt": "udm-RU",
    "ukrainian": "uk-UA",
    "uma": "ppk-ID",
    "umbundu": "umb-AO",
    "uyghur uig": "uig-CN",
    "uyghur ug": "ug-CN",
    "uzbek": "uz-UZ",
    "venetian": "vec-IT",
    "vietnamese": "vi-VN",
    "vincentian creole english": "svc-VC",
    "virgin islands creole english": "vic-US",
    "wallisian": "wls-WF",
    "waray (philippines)": "war-PH",
    "welsh": "cy-GB",
    "west central oromo": "gaz-ET",
    "western persian": "pes-IR",
    "wolof": "wo-SN",
    "xhosa": "xh-ZA",
    "yiddish": "yi-YD",
    "yoruba": "yo-NG",
    "zulu": "zu-ZA",
}


def _get_mymemory_lang_code(short_code: str) -> str:
    """
    Maps a standard 2-letter language code to a MyMemory specific regional code.

    **Business Rules:**
    - Fetches Google's dictionary to map the short code back to its full language name.
    - Looks up the full language name in MYMEMORY_LANG_MAP.
    - Falls back to the short code if no mapping is found.
    """
    try:
        google_langs = GoogleTranslator().get_supported_languages(as_dict=True)
        code_to_name = {code: name for name, code in google_langs.items()}

        lang_name = code_to_name.get(short_code)
        if not lang_name:
            return short_code

        return MYMEMORY_LANG_MAP.get(lang_name, short_code)
    except Exception as e:
        Prints.print_warning(msg=f"Failed to map MyMemory language code for {short_code}: {e}")
        return short_code


def _resolve_project_root() -> Path:
    """
    Locates the backend/project root directory by searching for manage.py
    or falling back to the parent directory hierarchy.
    """
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "manage.py").exists():
            return parent
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _resolve_project_root()


def _resolve_backend_locales_dir() -> Path:
    if (PROJECT_ROOT / "locales").exists():
        return PROJECT_ROOT / "locales"
    if (PROJECT_ROOT / "locale").exists():
        return PROJECT_ROOT / "locale"
    return PROJECT_ROOT / "locales"


def _resolve_frontend_locales_dir() -> Path:
    """
    Resolves the frontend locales directory path, checking both container (/app/shop_config)
    and root monorepo locations.
    """
    possible_paths = [
        PROJECT_ROOT / "shop_config/frontend/locales",
        PROJECT_ROOT / "config/frontend/locales",
        PROJECT_ROOT.parent / "shop_config/frontend/locales",
        PROJECT_ROOT.parent / "config/frontend/locales",
    ]
    for path in possible_paths:
        if path.exists():
            return path
    return PROJECT_ROOT / "shop_config/frontend/locales"


FRONTEND_LOCALES_DIR = _resolve_frontend_locales_dir()
BACKEND_LOCALES_DIR = _resolve_backend_locales_dir()


def translate_text(
    text: str, translators: list[GoogleTranslator | MyMemoryTranslator], cache: dict[str, str], max_retries: int = 3
) -> str:
    """
    Translates text while strictly preserving HTML tags, template variables, and whitespace.

    **Business Rules:**
    - Uses XML-like placeholders (e.g., <m0>) to protect interpolation variables.
    - Implements fallback strategy using multiple translator services to bypass rate-limiting.
    - Implements exponential backoff and jitter.
    """
    if not text.strip():
        return text

    if text in cache:
        return cache[text]

    tags = PROTECTED_PATTERN.findall(text)
    placeholder_text = text

    for i, tag in enumerate(tags):
        placeholder = f"<m{i}>"
        placeholder_text = placeholder_text.replace(tag, placeholder, 1)

    for translator in translators:
        translator_name = translator.__class__.__name__

        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(1.0, 2.5))
                translated = translator.translate(placeholder_text)

                if not translated:
                    raise ValueError(f"Received empty response from {translator_name} API.")

                translated = re.sub(r"<m\s*(\d+)\s*>", r"<m\1>", translated, flags=re.IGNORECASE)

                for i, tag in enumerate(tags):
                    placeholder = f"<m{i}>"
                    translated = translated.replace(placeholder, tag, 1)

                cache[text] = translated
                Prints.print_info(msg=f"Translated via {translator_name}: '{text[:30].replace(chr(10), ' ')}...'")
                return translated

            except Exception as e:
                Prints.print_warning(
                    msg=f"{translator_name} attempt {attempt + 1}/{max_retries} failed for '{text}': {e}"
                )

                if attempt == max_retries - 1:
                    Prints.print_error(msg=f"{translator_name} failed. Switching to next translator if available.")
                    break

                time.sleep((2**attempt) + random.uniform(1.0, 3.0))

    Prints.print_error(msg=f"All translators failed to translate '{text}'.")
    return ""


def merge_and_translate_node(
    base_node: JSONType,
    target_node: JSONType | None,
    translators: list[GoogleTranslator | MyMemoryTranslator],
    cache: dict[str, str],
) -> JSONType:
    """
    Recursively merges base JSON with target JSON.
    Translates only strings that are missing or empty in the target node using fallback translators.
    """
    if isinstance(base_node, dict):
        result: dict[str, JSONType] = {}
        target_dict = target_node if isinstance(target_node, dict) else {}
        for key, base_val in base_node.items():
            result[key] = merge_and_translate_node(base_val, target_dict.get(key), translators, cache)
        return result

    if isinstance(base_node, list):
        if isinstance(target_node, list) and len(target_node) == len(base_node):
            return [merge_and_translate_node(b, t, translators, cache) for b, t in zip(base_node, target_node)]
        return [merge_and_translate_node(b, None, translators, cache) for b in base_node]

    if isinstance(base_node, str):
        if isinstance(target_node, str) and target_node.strip():
            return target_node
        return translate_text(base_node, translators, cache)

    return base_node


def process_frontend(target_lang: str, translator: GoogleTranslator, cache: dict[str, str]) -> None:
    """
    Handles parsing and translating Frontend JSON locale files incrementally.
    Preserves existing translations and only translates missing keys.
    """
    base_file_path = FRONTEND_LOCALES_DIR / f"{BASE_LANG}.json"
    target_file_path = FRONTEND_LOCALES_DIR / f"{target_lang}.json"

    if not base_file_path.exists():
        Prints.print_error(msg=f"Frontend base file not found: {base_file_path}")
        return

    with open(base_file_path, "r", encoding="utf-8") as f:
        base_data = json.load(f)

    target_data = {}
    if target_file_path.exists():
        Prints.print_info(msg=f"Found existing {target_file_path.name}. Merging and translating only missing keys...")
        try:
            with open(target_file_path, "r", encoding="utf-8") as f:
                target_data = json.load(f)
        except json.JSONDecodeError:
            Prints.print_warning(msg=f"Could not parse {target_file_path.name}. Starting fresh.")
            target_data = {}

    translated_data = merge_and_translate_node(base_data, target_data, translator, cache)

    with open(target_file_path, "w", encoding="utf-8") as f:
        json.dump(translated_data, f, ensure_ascii=False, indent=2)

    Prints.print_success(msg=f"Frontend translation successfully synced and saved to {target_file_path}.")


def process_backend(target_lang: str, translator: GoogleTranslator, cache: dict[str, str]) -> None:
    """
    Handles parsing and translating Backend Django .po files.
    Supports single-line and multiline msgid / msgstr blocks.
    Translates only entries that have an empty msgstr.
    """
    po_file_path = BACKEND_LOCALES_DIR / target_lang / "LC_MESSAGES" / "django.po"

    if not po_file_path.exists():
        Prints.print_error(msg=f"Backend PO file not found: {po_file_path}")
        Prints.print_info(msg="Did you run 'python manage.py makemessages' first?")
        return

    with open(po_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    entry_pattern = re.compile(
        r'(msgid\s+(?:".*?"\s*)+)\n(msgstr\s+""(?:\s*\n|$))',
        re.MULTILINE,
    )

    def _replace_entry(match: re.Match[str]) -> str:
        raw_msgid_block = match.group(1)
        string_parts = re.findall(r'"((?:[^"\\]|\\.)*)"', raw_msgid_block)
        full_msgid = "".join(string_parts)

        if not full_msgid.strip():
            return match.group(0)

        clean_text = full_msgid.replace(r"\"", '"').replace(r"\n", "\n")
        translated = translate_text(clean_text, translator, cache)

        escaped_translated = translated.replace('"', r"\"").replace("\n", r"\n")
        return f'{raw_msgid_block}\nmsgstr "{escaped_translated}"\n'

    updated_content, count = entry_pattern.subn(_replace_entry, content)

    with open(po_file_path, "w", encoding="utf-8") as f:
        f.write(updated_content)

    Prints.print_success(msg=f"Backend translation saved. Processed {count} entries in {po_file_path}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-translate locales for Web Telegram Shop.")
    parser.add_argument("target_lang", type=str, help="Target language code (e.g., ru, es, uk)")
    parser.add_argument(
        "--type",
        choices=["frontend", "backend"],
        required=True,
        help="Target environment to translate (frontend or backend)",
    )
    args = parser.parse_args()

    target_lang = args.target_lang.lower()
    translation_type = args.type

    Prints.print_info(msg=f"Start auto translate from {BASE_LANG} to {target_lang} for {translation_type}...")

    translators: list[GoogleTranslator | MyMemoryTranslator] = []

    try:
        translators.append(GoogleTranslator(source=BASE_LANG, target=target_lang))
    except LanguageNotSupportedException:
        Prints.print_error(msg=f"GoogleTranslator: Language code '{target_lang}' is not supported!")
        supported_dict = GoogleTranslator().get_supported_languages(as_dict=True)
        Prints.print_info(msg=f"Google available codes: {', '.join(supported_dict.values())}")
        return

    try:
        mm_source = _get_mymemory_lang_code(BASE_LANG)
        mm_target = _get_mymemory_lang_code(target_lang)
        translators.append(MyMemoryTranslator(source=mm_source, target=mm_target))
    except LanguageNotSupportedException:
        Prints.print_warning(
            msg=(
                f"MyMemoryTranslator: Language code '{target_lang}' mapped as '{mm_target}' "
                "is not supported. Skipping fallback."
            )
        )

    if not translators:
        Prints.print_error(msg="No translators could be initialized. Exiting.")
        return

    translation_cache: dict[str, str] = {}

    if translation_type == "frontend":
        process_frontend(target_lang, translators, translation_cache)
    elif translation_type == "backend":
        process_backend(target_lang, translators, translation_cache)

    Prints.print_lines()
    Prints.print_success(msg=f"\nDone! Cached hits: {len(translation_cache)}")


if __name__ == "__main__":
    main()
