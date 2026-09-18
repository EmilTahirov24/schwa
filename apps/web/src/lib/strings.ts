/** The two languages the page speaks. Azerbaijani first: it is who the tool is for. */

export type Language = "az" | "en";

export type Strings = (typeof strings)[Language];

export const strings = {
  az: {
    heroTitle: "Hərfsiz yazılmış mətni düzəldir.",
    heroLead:
      "Klaviaturada ə, ı, ğ, ş, ç, ö, ü yoxdursa, mətn hərfsiz yazılır. Schwa onları kontekstə baxaraq geri qaytarır.",
    heroPrivate: "Model sənin brauzerində işləyir — yazdığın heç yerə göndərilmir.",

    editorTitle: "Özün yaz",
    placeholder: "Bura hərfsiz yaz… məsələn: sabah gorusek, sene zeng edecem",
    examples: "Nümunələr",
    copy: "Kopyala",
    copied: "Kopyalandı",
    clear: "Təmizlə",
    restoredLetters: (count: number) => `${count} hərf bərpa olundu`,
    nothingYet: "Yazdıqca burada düzəlmiş mətn görünəcək",
    loading: (loaded: string, total: string) => `Model yüklənir… ${loaded} / ${total}`,
    loadingSimple: "Model yüklənir…",
    failed: "Model yüklənmədi. Brauzerin WebAssembly-ni dəstəkləyirmi?",
    fromModel: (percent: number) => `model · ${percent}% əmin`,
    fromDictionary: "lüğətdən · həmişə belə yazılır",
    keepHint: "kliklə: yazdığın kimi saxla",
    undoHint: "kliklə: düzəldilmiş formaya qaytar",

    howTitle: "Necə işləyir",
    how: "Yeddi hərf klaviaturasız yazılanda bir ASCII hərfə çevrilir və hər birinin cəmi bir alternativi var. Ona görə model cümləni yenidən yazmır — hər hərf üçün tək bir suala cavab verir: burada diakritik varmı? Nəticədə diakritikdən başqa heç nə dəyişə bilmir.",
    ambiguityTitle: "Çətinlik haradadır",
    ambiguity:
      "“qiz” sözü həm “qız”, həm də “qiz” ola bilər. Hansı olduğunu yalnız yanındakı sözlər deyir — ona görə lüğət kifayət etmir, model lazımdır.",

    resultsTitle: "Nə qədər dəqiqdir",
    results:
      "Test setindən: 172 328 cümlə, öyrətmədə heç görünməmiş məqalələrdən, bir dəfə ölçülüb.",
    resultsCaveat:
      "Bu ölçmə Vikipediya mətnindədir. Gündəlik yazışmada rəqəm fərqli ola bilər — onu ölçmək növbəti addımdır.",
    columnSystem: "Sistem",
    columnAmbiguous: "Çoxmənalı sözlər",
    columnSentences: "Tam düzgün cümlə",
    rowLexicon: "Lüğət",
    rowTagger: "Model",
    rowHybrid: "Model + lüğət",

    getTitle: "İstifadə et",
    getExtensionTitle: "Brauzer əlavəsi",
    getExtension:
      "WhatsApp Web, Instagram, Gmail — istənilən saytda mətni seç və Ctrl+Shift+E bas. Model brauzerin içindədir.",
    getExtensionCta: "Mənbə kodu",
    getPythonTitle: "Python",
    getPython: "Öz layihəndə istifadə et. Model paketin içindədir, heç nə yükləmir.",
    getSourceTitle: "Mənbə",
    getSource: "Data, öyrətmə, ölçmələr və hər qərarın izahı — hamısı açıqdır.",
    getSourceCta: "GitHub-da bax",

    privacy: "Məxfilik",
    madeBy: "Emil Tahirov",
  },
  en: {
    heroTitle: "Puts the Azerbaijani letters back.",
    heroLead:
      "Without the right keyboard, ə, ı, ğ, ş, ç, ö and ü simply get dropped. Schwa restores them by reading the context.",
    heroPrivate: "The model runs in your browser — nothing you type is sent anywhere.",

    editorTitle: "Try it",
    placeholder: "Type without the letters… e.g. sabah gorusek, sene zeng edecem",
    examples: "Examples",
    copy: "Copy",
    copied: "Copied",
    clear: "Clear",
    restoredLetters: (count: number) => `${count} letter${count === 1 ? "" : "s"} restored`,
    nothingYet: "The restored text appears here as you type",
    loading: (loaded: string, total: string) => `Loading the model… ${loaded} / ${total}`,
    loadingSimple: "Loading the model…",
    failed: "The model did not load. Does this browser support WebAssembly?",
    fromModel: (percent: number) => `model · ${percent}% sure`,
    fromDictionary: "dictionary · always spelled this way",
    keepHint: "click to keep what you typed",
    undoHint: "click to restore it again",

    howTitle: "How it works",
    how: "The seven letters collapse to one ASCII letter each when typed without the layout, and every collapsed letter has exactly one alternative. So the model never rewrites the sentence — it answers one question per character: does this one carry a diacritic? Nothing but diacritics can change.",
    ambiguityTitle: "Where it gets hard",
    ambiguity:
      "“qiz” can be “qız” (girl) or “qiz”. Only the surrounding words tell which — which is why a dictionary is not enough and a model is needed.",

    resultsTitle: "How accurate it is",
    results:
      "Test split: 172,328 sentences from articles never seen in training, scored once.",
    resultsCaveat:
      "That is encyclopedic prose. How it does on everyday writing is the next thing to measure, not something to assume.",
    columnSystem: "System",
    columnAmbiguous: "Ambiguous words",
    columnSentences: "Sentences exactly right",
    rowLexicon: "Dictionary",
    rowTagger: "Model",
    rowHybrid: "Model + dictionary",

    getTitle: "Use it",
    getExtensionTitle: "Browser extension",
    getExtension:
      "WhatsApp Web, Instagram, Gmail — select text on any site and press Ctrl+Shift+E. The model lives inside the browser.",
    getExtensionCta: "Source code",
    getPythonTitle: "Python",
    getPython: "Use it in your own project. The model ships inside the package — nothing to download.",
    getSourceTitle: "Source",
    getSource: "Data, training, measurements and the reasoning behind every decision — all open.",
    getSourceCta: "See it on GitHub",

    privacy: "Privacy",
    madeBy: "Emil Tahirov",
  },
} as const;

/**
 * Sentences for the opening animation and the example chips. Each pair is what the model
 * actually returns for that input - recorded from the shipped model, not written by hand.
 */
export const DEMO_PAIRS: ReadonlyArray<readonly [string, string]> = [
  ["sence neden basliyaq", "səncə nədən başlıyaq"],
  ["usaqlar bagcada oynayir", "uşaqlar bağçada oynayır"],
  ["men bu gun mektebe getmedim", "mən bu gün məktəbə getmədim"],
  ["telefonumu evde unutmusam", "telefonumu evdə unutmuşam"],
  ["sabah gorusek", "sabah görüşək"],
];

export const EXAMPLES = [
  "sence neden basliyaq?",
  "usaqlar bagcada oynayir, men ise evde kitab oxuyuram",
  "sabah gorusek, saat altida zeng edecem",
  "Bakida hava cox isti idi, denize getdik",
];

export const GITHUB_URL = "https://github.com/EmilTahirov24/schwa";
