import React, { createContext, useContext, useEffect, useMemo } from 'react'
import useNDPreferences, {
  type NDPreferences,
  type NdColorTheme,
  type NdLineSpacing,
} from '@/hooks/useNDPreferences'
import api from '@/lib/api'

type NDPreferencesContextValue = {
  prefs: NDPreferences
  setPrefs: React.Dispatch<React.SetStateAction<NDPreferences>>
  setters: ReturnType<typeof useNDPreferences>['setters']
}

const NDPreferencesContext = createContext<NDPreferencesContextValue | null>(null)

export function useNDPreferencesContext() {
  const v = useContext(NDPreferencesContext)
  if (!v) throw new Error('useNDPreferencesContext must be used within NDPreferencesProvider')
  return v
}

// Re-export types so consumers don't need to import from the hook directly
export type { NdColorTheme, NdLineSpacing, NDPreferences }

// ── Apply all preferences to the DOM ─────────────────────────────────────────
function applyRootStyles(prefs: NDPreferences) {
  const html = document.documentElement
  const body = document.body

  // ── data-* attributes (drive CSS selectors in index.css) ──────────────────
  html.setAttribute('data-dyslexia',    prefs.dyslexiaFont       ? 'true' : 'false')
  html.setAttribute('data-focus-mode',  prefs.focusMode          ? 'true' : 'false')
  html.setAttribute('data-theme',       prefs.colorTheme)
  body.setAttribute('data-theme',       prefs.colorTheme)
  html.setAttribute('data-sensory',     prefs.reduceSensory      ? 'true' : 'false')
  html.setAttribute('data-chunk',       prefs.chunkContent       ? 'true' : 'false')
  html.setAttribute('data-hide-dist',   prefs.hideDistractions   ? 'true' : 'false')
  html.setAttribute('data-plain-lang',  prefs.plainLanguage      ? 'true' : 'false')
  html.setAttribute('data-predictable', prefs.predictableLayout  ? 'true' : 'false')
  html.setAttribute('data-hi-links',    prefs.highlightLinks     ? 'true' : 'false')
  html.setAttribute('data-no-anim',     prefs.removeAnimations   ? 'true' : 'false')

  // ── Font size ─────────────────────────────────────────────────────────────
  const rootPx = prefs.textSize === 'a-' ? 14 : prefs.textSize === 'a' ? 16 : 20
  html.style.fontSize = `${rootPx}px`

  // ── Line height ───────────────────────────────────────────────────────────
  const lh = prefs.lineSpacing === 'normal' ? '1.6' : prefs.lineSpacing === 'relaxed' ? '1.8' : '2.2'
  html.style.setProperty('--nd-line-height', lh)
  body.style.lineHeight = lh

  // ── Letter / word spacing ─────────────────────────────────────────────────
  html.style.setProperty('--nd-letter-spacing', prefs.letterSpacing ? '0.06em' : '0')
  html.style.setProperty('--nd-word-spacing',   prefs.wordSpacing   ? '0.18em' : '0')

  // ── Brightness ────────────────────────────────────────────────────────────
  body.style.filter = prefs.reduceBrightness ? 'brightness(0.85)' : ''

  // ── Color theme CSS vars ──────────────────────────────────────────────────
  const themes: Record<string, Record<string, string>> = {
    default:    { bg: '#F9FAFB', text: '#111827', card: '#FFFFFF', muted: '#6B7280', focus: '#4F46E5', border: '#E5E7EB' },
    soft_cream: { bg: '#FFF8F0', text: '#2D2D2D', card: '#FFFDF8', muted: '#5C5C5C', focus: '#4F46E5', border: '#E8D5C0' },
    dark_mode:  { bg: '#1A1A2E', text: '#E0E0E0', card: '#20203A', muted: '#BFC3D1', focus: '#818CF8', border: '#2D2D4E' },
    blue_light: { bg: '#FFF9F0', text: '#1A1A1A', card: '#FFF5E6', muted: '#5C5C5C', focus: '#D97706', border: '#F5DEB3' },
  }
  const t = themes[prefs.colorTheme] ?? themes.default
  html.style.setProperty('--nd-bg',     t.bg)
  html.style.setProperty('--nd-text',   t.text)
  html.style.setProperty('--nd-card-bg',t.card)
  html.style.setProperty('--nd-muted',  t.muted)
  html.style.setProperty('--nd-focus-bg', t.focus)
  html.style.setProperty('--nd-border', t.border)

  body.style.backgroundColor = t.bg
  body.style.color = t.text
}

export function NDPreferencesProvider({ children }: { children: React.ReactNode }) {
  const { prefs, setPrefs, setters } = useNDPreferences()

  useEffect(() => {
    applyRootStyles(prefs)
    try {
      if (prefs.ndModeEnabled) api.defaults.headers.common['X-ND-Mode'] = 'true'
      else delete api.defaults.headers.common['X-ND-Mode']
    } catch { /* ignore */ }
  }, [prefs])

  // Focus mode: click to spotlight a card
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!prefs.focusMode) return
      const card = (e.target as HTMLElement).closest('.card') as HTMLElement | null
      document.querySelectorAll('.card.nd-focused').forEach(el => el.classList.remove('nd-focused'))
      if (card) card.classList.add('nd-focused')
    }
    if (prefs.focusMode) document.addEventListener('click', onClick)
    return () => document.removeEventListener('click', onClick)
  }, [prefs.focusMode])

  // Cleanup on unmount
  useEffect(() => () => {
    const html = document.documentElement
    ;['data-dyslexia','data-focus-mode','data-theme','data-sensory','data-chunk',
      'data-hide-dist','data-plain-lang','data-predictable','data-hi-links','data-no-anim',
    ].forEach(a => html.removeAttribute(a))
    document.body.removeAttribute('data-theme')
    html.style.fontSize = ''
    document.body.style.cssText = ''
  }, [])

  const value = useMemo(() => ({ prefs, setPrefs, setters }), [prefs, setPrefs, setters])
  return <NDPreferencesContext.Provider value={value}>{children}</NDPreferencesContext.Provider>
}
