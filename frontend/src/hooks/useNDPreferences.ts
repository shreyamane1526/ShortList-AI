import { useCallback, useEffect, useMemo, useState } from 'react'

export type NdColorTheme = 'default' | 'soft_cream' | 'dark_mode' | 'blue_light'
export type NdLineSpacing = 'normal' | 'relaxed' | 'loose'

export type NDPreferences = {
  // ── Typography / Dyslexia ──────────────────────────────────────────────────
  dyslexiaFont: boolean          // OpenDyslexic font
  textSize: 'a-' | 'a' | 'a+'   // root font size
  lineSpacing: NdLineSpacing     // line-height
  letterSpacing: boolean         // extra letter spacing (0.05em)
  wordSpacing: boolean           // extra word spacing
  highlightLinks: boolean        // underline + bold all links

  // ── Color / Visual ─────────────────────────────────────────────────────────
  colorTheme: NdColorTheme
  reduceBrightness: boolean      // dims the whole page to 85%
  removeAnimations: boolean      // kills all CSS transitions/animations

  // ── ADHD / Focus ───────────────────────────────────────────────────────────
  focusMode: boolean             // dims non-active cards
  readingRuler: boolean          // horizontal highlight band
  hideDistractions: boolean      // hides decorative elements, banners
  chunkContent: boolean          // adds extra visual breaks between sections

  // ── Autism / Sensory ───────────────────────────────────────────────────────
  reduceSensory: boolean         // removes gradients, shadows, rounded corners
  plainLanguage: boolean         // shows "Simplify" buttons everywhere automatically
  predictableLayout: boolean     // locks sidebar open, removes hover effects

  // ── Global ─────────────────────────────────────────────────────────────────
  ndModeEnabled: boolean
}

const STORAGE_KEY = 'nd_preferences'

function getDefaultPrefs(): NDPreferences {
  return {
    dyslexiaFont: false,
    textSize: 'a',
    lineSpacing: 'normal',
    letterSpacing: false,
    wordSpacing: false,
    highlightLinks: false,

    colorTheme: 'default',
    reduceBrightness: false,
    removeAnimations: false,

    focusMode: false,
    readingRuler: false,
    hideDistractions: false,
    chunkContent: false,

    reduceSensory: false,
    plainLanguage: false,
    predictableLayout: false,

    ndModeEnabled: false,
  }
}

export function readNDPreferences(): NDPreferences {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return getDefaultPrefs()
    const parsed = JSON.parse(raw) as Partial<NDPreferences>
    const base = getDefaultPrefs()
    return {
      ...base,
      ...parsed,
      colorTheme: (['default', 'soft_cream', 'dark_mode', 'blue_light'] as const).includes(
        parsed.colorTheme as NdColorTheme,
      ) ? (parsed.colorTheme as NdColorTheme) : base.colorTheme,
      lineSpacing: (['normal', 'relaxed', 'loose'] as const).includes(parsed.lineSpacing as NdLineSpacing)
        ? (parsed.lineSpacing as NdLineSpacing) : base.lineSpacing,
      textSize: (['a-', 'a', 'a+'] as const).includes(parsed.textSize as NDPreferences['textSize'])
        ? (parsed.textSize as NDPreferences['textSize']) : base.textSize,
    }
  } catch {
    return getDefaultPrefs()
  }
}

export default function useNDPreferences() {
  const [prefs, setPrefs] = useState<NDPreferences>(() => getDefaultPrefs())

  // Hydrate from localStorage after mount
  useEffect(() => {
    setPrefs(readNDPreferences())
  }, [])

  // Persist on every change
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)) } catch { /* ignore */ }
  }, [prefs])

  const setters = useMemo(() => ({
    setDyslexiaFont:      (v: boolean)                      => setPrefs(p => ({ ...p, dyslexiaFont: v })),
    setTextSize:          (v: NDPreferences['textSize'])     => setPrefs(p => ({ ...p, textSize: v })),
    setLineSpacing:       (v: NdLineSpacing)                 => setPrefs(p => ({ ...p, lineSpacing: v })),
    setLetterSpacing:     (v: boolean)                       => setPrefs(p => ({ ...p, letterSpacing: v })),
    setWordSpacing:       (v: boolean)                       => setPrefs(p => ({ ...p, wordSpacing: v })),
    setHighlightLinks:    (v: boolean)                       => setPrefs(p => ({ ...p, highlightLinks: v })),

    setColorTheme:        (v: NdColorTheme)                  => setPrefs(p => ({ ...p, colorTheme: v })),
    setReduceBrightness:  (v: boolean)                       => setPrefs(p => ({ ...p, reduceBrightness: v })),
    setRemoveAnimations:  (v: boolean)                       => setPrefs(p => ({ ...p, removeAnimations: v })),

    setFocusMode:         (v: boolean)                       => setPrefs(p => ({ ...p, focusMode: v })),
    setReadingRuler:      (v: boolean)                       => setPrefs(p => ({ ...p, readingRuler: v })),
    setHideDistractions:  (v: boolean)                       => setPrefs(p => ({ ...p, hideDistractions: v })),
    setChunkContent:      (v: boolean)                       => setPrefs(p => ({ ...p, chunkContent: v })),

    setReduceSensory:     (v: boolean)                       => setPrefs(p => ({ ...p, reduceSensory: v })),
    setPlainLanguage:     (v: boolean)                       => setPrefs(p => ({ ...p, plainLanguage: v })),
    setPredictableLayout: (v: boolean)                       => setPrefs(p => ({ ...p, predictableLayout: v })),

    setNdModeEnabled:     (v: boolean)                       => setPrefs(p => ({ ...p, ndModeEnabled: v })),
    setAll:               (v: Partial<NDPreferences>)        => setPrefs(p => ({ ...p, ...v })),
  }), [])

  // Auto-derive ndModeEnabled
  const updateNdModeEnabled = useCallback(() => {
    setPrefs(p => {
      const active =
        p.dyslexiaFont || p.focusMode || p.readingRuler || p.colorTheme !== 'default' ||
        p.letterSpacing || p.wordSpacing || p.highlightLinks || p.reduceBrightness ||
        p.removeAnimations || p.hideDistractions || p.chunkContent ||
        p.reduceSensory || p.plainLanguage || p.predictableLayout
      if (p.ndModeEnabled === active) return p
      return { ...p, ndModeEnabled: active }
    })
  }, [])

  useEffect(() => { updateNdModeEnabled() }, [
    prefs.dyslexiaFont, prefs.focusMode, prefs.readingRuler, prefs.colorTheme,
    prefs.letterSpacing, prefs.wordSpacing, prefs.highlightLinks, prefs.reduceBrightness,
    prefs.removeAnimations, prefs.hideDistractions, prefs.chunkContent,
    prefs.reduceSensory, prefs.plainLanguage, prefs.predictableLayout,
    updateNdModeEnabled,
  ])

  return { prefs, setPrefs, setters, STORAGE_KEY }
}
