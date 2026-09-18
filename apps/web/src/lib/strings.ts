/** The two languages the page speaks. Azerbaijani first: it is who the tool is for. */

export type Language = "az" | "en";

export const strings = {
  az: {
    tagline: "Azərbaycan hərflərini bərpa edir",
    intro:
      "Klaviaturada ə, ı, ğ, ş, ç, ö, ü yoxdursa, mətn hərfsiz yazılır. Bu alət onları geri qaytarır. Dəyişən sözlər altdan xətlənir — razı deyilsənsə, üstünə klikləyib əvvəlki halına qaytar.",
    placeholder: "Mətni bura yaz və ya yapışdır",
    restore: "Düzəlt",
    working: "İşləyir…",
    example: "Nümunə",
    clear: "Təmizlə",
    copy: "Kopyala",
    copied: "Kopyalandı",
    result: "Nəticə",
    changes: (count: number) => `${count} söz dəyişdi`,
    noChanges: "Heç nə dəyişmədi",
    offline: "Mətni emal etmək alınmadı. Səhifəni yeniləyib yenidən cəhd et.",
    loadingModel: "Model yüklənir…",
    local: "Model sənin brauzerində işləyir — yazdığın heç yerə göndərilmir.",
    modelFailed: "Model yüklənmədi. Brauzerin WebAssembly-ni dəstəkləyirmi?",
    howTitle: "Necə işləyir",
    how: "Hər hərf üçün bir sual var: burada diakritik varmı? Yeddi hərf cütü hərfsiz yazılanda üst-üstə düşür, hər birinin isə yalnız bir alternativi var. Ona görə model mətni yenidən yazmır — yalnız hərflərə etiket qoyur. Buna görə də diakritikdən başqa heç nə dəyişə bilmir.",
    ambiguity:
      "Çətinlik ondadır ki, qiz sözü həm qız, həm də qiz ola bilər. Doğru variantı yalnız yanındakı sözlər müəyyən edir.",
    resultsTitle: "Nə qədər dəqiqdir",
    results:
      "Rəqəmlər test setindən gəlir: 172 328 cümlə, öyrətmədə heç görünməmiş məqalələrdən, bir dəfə ölçülüb.",
    resultsCaveat:
      "Bu ölçmə Vikipediya mətnindədir. Gündəlik yazışmada rəqəm fərqli ola bilər — onu ölçmək növbəti işdir.",
    columnSystem: "Sistem",
    columnAmbiguous: "Çoxmənalı sözlər",
    columnSentences: "Tam düzgün cümlə",
    rowLexicon: "Lüğət",
    rowTagger: "Model",
    rowHybrid: "Model + lüğət",
  },
  en: {
    tagline: "Restores Azerbaijani diacritics",
    intro:
      "Azerbaijani has seven letters a plain keyboard cannot produce, so people drop them. This puts them back. Changed words are underlined — click one to keep what you typed.",
    placeholder: "Type or paste text here",
    restore: "Restore",
    working: "Working…",
    example: "Example",
    clear: "Clear",
    copy: "Copy",
    copied: "Copied",
    result: "Result",
    changes: (count: number) => `${count} word${count === 1 ? "" : "s"} changed`,
    noChanges: "Nothing changed",
    offline: "Could not process the text. Reload the page and try again.",
    loadingModel: "Loading the model…",
    local: "The model runs in your browser — nothing you type is sent anywhere.",
    modelFailed: "The model did not load. Does this browser support WebAssembly?",
    howTitle: "How it works",
    how: "Every character gets one question: does it carry a diacritic? The seven letter pairs collapse to a single ASCII letter each, and each collapsed form has exactly one alternative, so the model never rewrites the sentence — it only labels characters. That is why nothing but diacritics can change.",
    ambiguity:
      "The hard part is that qiz can be either qız or qiz. Only the surrounding words decide which one is meant.",
    resultsTitle: "How accurate it is",
    results:
      "Measured on the test split: 172,328 sentences from articles never seen in training, scored once.",
    resultsCaveat:
      "That is encyclopedic prose. How it does on everyday writing is the next thing to measure, not something to assume.",
    columnSystem: "System",
    columnAmbiguous: "Ambiguous words",
    columnSentences: "Sentences exactly right",
    rowLexicon: "Dictionary",
    rowTagger: "Model",
    rowHybrid: "Model + dictionary",
  },
} satisfies Record<Language, Record<string, unknown>>;

export const EXAMPLE =
  "sence neden basliyaq? men dunen mektebe getdim, isiq sondu ve hec kim gelmedi. usaqlar bagcada oynayirdi.";
