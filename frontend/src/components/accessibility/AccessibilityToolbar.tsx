/**
 * AccessibilityToolbar
 *
 * A slide-in panel from the right edge of the screen.
 * Triggered by a fixed FAB (floating action button) at bottom-right.
 * Organised into four tabs: Dyslexia · ADHD · Autism · Display
 *
 * All settings persist to localStorage under "nd_preferences".
 */
import { useState, useEffect, useRef } from 'react'
import { X, Type, Brain, Sparkles, Monitor, RotateCcw } from 'lucide-react'
import { useNDPreferencesContext } from '@/context/NDPreferencesContext'
import type { NdColorTheme, NdLineSpacing } from '@/hooks/useNDPreferences'

// ── Small reusable toggle switch ──────────────────────────────────────────────
function Toggle({
  id, label, description, checked, onChange,
}: {
  id: string; label: string; description?: string
  checked: boolean; onChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-start justify-between gap-3 py-2">
      <div className="flex-1 min-w-0">
        <label htmlFor={id} className="text-sm font-medium cursor-pointer block" style={{ color: 'var(--nd-text,#111827)' }}>
          {label}
        </label>
        {description && (
          <p className="text-xs mt-0.5 leading-snug" style={{ color: 'var(--nd-muted,#6B7280)' }}>
            {description}
          </p>
        )}
      </div>
      <button
        id={id}
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:ring-2 focus-visible:ring-offset-1 ${
          checked ? 'bg-indigo-600' : 'bg-gray-300'
        }`}
        aria-label={label}
      >
        <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`} />
      </button>
    </div>
  )
}

// ── Section heading ───────────────────────────────────────────────────────────
function SectionHead({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-bold uppercase tracking-widest mb-1 mt-3 first:mt-0"
       style={{ color: 'var(--nd-muted,#9CA3AF)' }}>
      {children}
    </p>
  )
}

// ── Divider ───────────────────────────────────────────────────────────────────
function Divider() {
  return <div className="my-2 border-t" style={{ borderColor: 'var(--nd-border,#E5E7EB)' }} />
}

// ── Tab definitions ───────────────────────────────────────────────────────────
type Tab = 'dyslexia' | 'adhd' | 'autism' | 'display'
const TABS: { id: Tab; label: string; icon: React.ReactNode; color: string }[] = [
  { id: 'dyslexia', label: 'Dyslexia',  icon: <Type className="w-4 h-4" />,     color: '#7C3AED' },
  { id: 'adhd',     label: 'ADHD',      icon: <Brain className="w-4 h-4" />,    color: '#0891B2' },
  { id: 'autism',   label: 'Autism',    icon: <Sparkles className="w-4 h-4" />, color: '#059669' },
  { id: 'display',  label: 'Display',   icon: <Monitor className="w-4 h-4" />,  color: '#D97706' },
]

// ── Color theme swatches ──────────────────────────────────────────────────────
const COLOR_THEMES: { value: NdColorTheme; label: string; bg: string; text: string; desc: string }[] = [
  { value: 'default',    label: 'Default',    bg: '#F9FAFB', text: '#111827', desc: 'Standard light' },
  { value: 'soft_cream', label: 'Soft Cream', bg: '#FFF8F0', text: '#2D2D2D', desc: 'Warm, low-glare' },
  { value: 'blue_light', label: 'Warm Amber', bg: '#FFF9F0', text: '#1A1A1A', desc: 'Reduces blue light' },
  { value: 'dark_mode',  label: 'Dark',       bg: '#1A1A2E', text: '#E0E0E0', desc: 'Low brightness' },
]

// ── Main component ────────────────────────────────────────────────────────────
export default function AccessibilityToolbar() {
  const { prefs, setters } = useNDPreferencesContext()
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState<Tab>('dyslexia')
  const panelRef = useRef<HTMLDivElement>(null)
  const firstFocusRef = useRef<HTMLButtonElement>(null)

  // Trap focus inside panel when open
  useEffect(() => {
    if (open) {
      setTimeout(() => firstFocusRef.current?.focus(), 50)
    }
  }, [open])

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && open) setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  function resetAll() {
    setters.setAll({
      dyslexiaFont: false, letterSpacing: false, wordSpacing: false, highlightLinks: false,
      lineSpacing: 'normal', textSize: 'a',
      colorTheme: 'default', reduceBrightness: false, removeAnimations: false,
      focusMode: false, readingRuler: false, hideDistractions: false, chunkContent: false,
      reduceSensory: false, plainLanguage: false, predictableLayout: false,
    })
  }

  const activeCount = [
    prefs.dyslexiaFont, prefs.letterSpacing, prefs.wordSpacing, prefs.highlightLinks,
    prefs.focusMode, prefs.readingRuler, prefs.hideDistractions, prefs.chunkContent,
    prefs.reduceSensory, prefs.plainLanguage, prefs.predictableLayout,
    prefs.reduceBrightness, prefs.removeAnimations,
    prefs.colorTheme !== 'default', prefs.lineSpacing !== 'normal', prefs.textSize !== 'a',
  ].filter(Boolean).length

  return (
    <>
      {/* ── Backdrop ──────────────────────────────────────────────────────── */}
      {open && (
        <div
          className="fixed inset-0 z-[9997] bg-black/20"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Slide-in panel ────────────────────────────────────────────────── */}
      <div
        ref={panelRef}
        className={`nd-panel ${open ? 'open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="Accessibility settings"
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4 border-b shrink-0"
          style={{ borderColor: 'var(--nd-border,#E5E7EB)', backgroundColor: 'var(--nd-card-bg,#fff)' }}
        >
          <div>
            <h2 className="font-bold text-base" style={{ color: 'var(--nd-text,#111827)' }}>
              Accessibility
            </h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--nd-muted,#6B7280)' }}>
              {activeCount > 0 ? `${activeCount} setting${activeCount !== 1 ? 's' : ''} active` : 'All defaults'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {activeCount > 0 && (
              <button
                onClick={resetAll}
                className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg border transition-colors hover:bg-gray-50"
                style={{ color: 'var(--nd-muted,#6B7280)', borderColor: 'var(--nd-border,#E5E7EB)' }}
                aria-label="Reset all accessibility settings"
              >
                <RotateCcw className="w-3 h-3" aria-hidden="true" />
                Reset
              </button>
            )}
            <button
              ref={firstFocusRef}
              onClick={() => setOpen(false)}
              className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              aria-label="Close accessibility panel"
            >
              <X className="w-4 h-4" style={{ color: 'var(--nd-text,#111827)' }} />
            </button>
          </div>
        </div>

        {/* Tab bar */}
        <div
          className="flex border-b shrink-0"
          style={{ borderColor: 'var(--nd-border,#E5E7EB)', backgroundColor: 'var(--nd-card-bg,#fff)' }}
          role="tablist"
          aria-label="Accessibility categories"
        >
          {TABS.map(t => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              aria-controls={`nd-tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className="flex-1 flex flex-col items-center gap-1 py-2.5 text-[10px] font-semibold transition-colors relative"
              style={{
                color: tab === t.id ? t.color : 'var(--nd-muted,#9CA3AF)',
                borderBottom: tab === t.id ? `2px solid ${t.color}` : '2px solid transparent',
              }}
            >
              <span style={{ color: tab === t.id ? t.color : 'var(--nd-muted,#9CA3AF)' }}>
                {t.icon}
              </span>
              {t.label}
            </button>
          ))}
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-5 py-4" style={{ backgroundColor: 'var(--nd-card-bg,#fff)' }}>

          {/* ── DYSLEXIA TAB ──────────────────────────────────────────────── */}
          {tab === 'dyslexia' && (
            <div id="nd-tab-dyslexia" role="tabpanel" aria-label="Dyslexia settings">
              <p className="text-xs mb-3 leading-relaxed" style={{ color: 'var(--nd-muted,#6B7280)' }}>
                These settings make text easier to read for people with dyslexia.
              </p>

              <SectionHead>Font</SectionHead>
              <Toggle
                id="nd-dyslexia-font"
                label="OpenDyslexic font"
                description="Replaces all text with a font designed to reduce letter confusion"
                checked={prefs.dyslexiaFont}
                onChange={setters.setDyslexiaFont}
              />

              <Divider />
              <SectionHead>Spacing</SectionHead>
              <Toggle
                id="nd-letter-spacing"
                label="Extra letter spacing"
                description="Adds space between letters so they don't blur together"
                checked={prefs.letterSpacing}
                onChange={setters.setLetterSpacing}
              />
              <Toggle
                id="nd-word-spacing"
                label="Extra word spacing"
                description="Adds space between words to reduce crowding"
                checked={prefs.wordSpacing}
                onChange={setters.setWordSpacing}
              />

              <div className="mt-2">
                <p className="text-xs font-medium mb-2" style={{ color: 'var(--nd-text,#111827)' }}>
                  Line spacing
                </p>
                <div className="flex gap-1.5">
                  {([
                    { v: 'normal',  l: 'Normal' },
                    { v: 'relaxed', l: 'Relaxed' },
                    { v: 'loose',   l: 'Loose' },
                  ] as { v: NdLineSpacing; l: string }[]).map(o => (
                    <button
                      key={o.v}
                      onClick={() => setters.setLineSpacing(o.v)}
                      aria-pressed={prefs.lineSpacing === o.v}
                      className="flex-1 py-1.5 rounded-lg border text-xs font-medium transition-colors"
                      style={{
                        backgroundColor: prefs.lineSpacing === o.v ? '#7C3AED' : 'transparent',
                        color: prefs.lineSpacing === o.v ? '#fff' : 'var(--nd-text,#374151)',
                        borderColor: prefs.lineSpacing === o.v ? '#7C3AED' : 'var(--nd-border,#D1D5DB)',
                      }}
                    >
                      {o.l}
                    </button>
                  ))}
                </div>
              </div>

              <Divider />
              <SectionHead>Links & navigation</SectionHead>
              <Toggle
                id="nd-highlight-links"
                label="Highlight all links"
                description="Makes every link bold and underlined so they're easy to spot"
                checked={prefs.highlightLinks}
                onChange={setters.setHighlightLinks}
              />

              <Divider />
              <SectionHead>Text size</SectionHead>
              <div className="flex gap-1.5">
                {([
                  { v: 'a-' as const, l: 'A−', desc: 'Small (14px)' },
                  { v: 'a'  as const, l: 'A',  desc: 'Default (16px)' },
                  { v: 'a+' as const, l: 'A+', desc: 'Large (20px)' },
                ]).map(o => (
                  <button
                    key={o.v}
                    onClick={() => setters.setTextSize(o.v)}
                    aria-pressed={prefs.textSize === o.v}
                    aria-label={o.desc}
                    className="flex-1 py-2 rounded-lg border text-sm font-bold transition-colors"
                    style={{
                      backgroundColor: prefs.textSize === o.v ? '#7C3AED' : 'transparent',
                      color: prefs.textSize === o.v ? '#fff' : 'var(--nd-text,#374151)',
                      borderColor: prefs.textSize === o.v ? '#7C3AED' : 'var(--nd-border,#D1D5DB)',
                    }}
                  >
                    {o.l}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── ADHD TAB ──────────────────────────────────────────────────── */}
          {tab === 'adhd' && (
            <div id="nd-tab-adhd" role="tabpanel" aria-label="ADHD settings">
              <p className="text-xs mb-3 leading-relaxed" style={{ color: 'var(--nd-muted,#6B7280)' }}>
                These settings reduce distraction and help you stay focused on one thing at a time.
              </p>

              <SectionHead>Focus</SectionHead>
              <Toggle
                id="nd-focus-mode"
                label="Focus mode"
                description="Dims everything on the page except the section you click on"
                checked={prefs.focusMode}
                onChange={setters.setFocusMode}
              />
              <Toggle
                id="nd-reading-ruler"
                label="Reading ruler"
                description="A yellow band follows your cursor to mark the line you're reading"
                checked={prefs.readingRuler}
                onChange={setters.setReadingRuler}
              />

              <Divider />
              <SectionHead>Reduce clutter</SectionHead>
              <Toggle
                id="nd-hide-distractions"
                label="Hide decorative elements"
                description="Removes banners, illustrations, and non-essential visuals"
                checked={prefs.hideDistractions}
                onChange={setters.setHideDistractions}
              />
              <Toggle
                id="nd-chunk-content"
                label="Chunk content"
                description="Adds extra space between sections so each block feels separate"
                checked={prefs.chunkContent}
                onChange={setters.setChunkContent}
              />

              <Divider />
              <SectionHead>Motion</SectionHead>
              <Toggle
                id="nd-remove-animations"
                label="Stop all animations"
                description="Disables every transition, spin, and animation on the page"
                checked={prefs.removeAnimations}
                onChange={setters.setRemoveAnimations}
              />
            </div>
          )}

          {/* ── AUTISM TAB ────────────────────────────────────────────────── */}
          {tab === 'autism' && (
            <div id="nd-tab-autism" role="tabpanel" aria-label="Autism settings">
              <p className="text-xs mb-3 leading-relaxed" style={{ color: 'var(--nd-muted,#6B7280)' }}>
                These settings reduce sensory overload and make the interface more predictable.
              </p>

              <SectionHead>Sensory</SectionHead>
              <Toggle
                id="nd-reduce-sensory"
                label="Reduce visual noise"
                description="Removes gradients, shadows, and rounded corners — flat, calm layout"
                checked={prefs.reduceSensory}
                onChange={setters.setReduceSensory}
              />
              <Toggle
                id="nd-reduce-brightness"
                label="Reduce brightness"
                description="Dims the whole page to 85% — easier on light-sensitive eyes"
                checked={prefs.reduceBrightness}
                onChange={setters.setReduceBrightness}
              />

              <Divider />
              <SectionHead>Predictability</SectionHead>
              <Toggle
                id="nd-predictable-layout"
                label="Predictable layout"
                description="Removes hover effects and unexpected visual changes"
                checked={prefs.predictableLayout}
                onChange={setters.setPredictableLayout}
              />
              <Toggle
                id="nd-plain-language"
                label="Plain language mode"
                description="Shows 'Simplify' buttons on all text blocks so you can rewrite them in simple English"
                checked={prefs.plainLanguage}
                onChange={setters.setPlainLanguage}
              />

              <Divider />
              <SectionHead>Motion</SectionHead>
              <Toggle
                id="nd-remove-animations-autism"
                label="Stop all animations"
                description="Disables every transition and animation — nothing moves unexpectedly"
                checked={prefs.removeAnimations}
                onChange={setters.setRemoveAnimations}
              />
            </div>
          )}

          {/* ── DISPLAY TAB ───────────────────────────────────────────────── */}
          {tab === 'display' && (
            <div id="nd-tab-display" role="tabpanel" aria-label="Display settings">
              <p className="text-xs mb-3 leading-relaxed" style={{ color: 'var(--nd-muted,#6B7280)' }}>
                Adjust colours and contrast to suit your visual needs.
              </p>

              <SectionHead>Color theme</SectionHead>
              <div className="space-y-1.5">
                {COLOR_THEMES.map(ct => (
                  <button
                    key={ct.value}
                    onClick={() => setters.setColorTheme(ct.value)}
                    aria-pressed={prefs.colorTheme === ct.value}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all text-left"
                    style={{
                      borderColor: prefs.colorTheme === ct.value ? '#4F46E5' : 'var(--nd-border,#E5E7EB)',
                      backgroundColor: prefs.colorTheme === ct.value ? 'rgba(79,70,229,0.06)' : 'transparent',
                    }}
                  >
                    {/* Swatch */}
                    <span
                      className="w-8 h-8 rounded-lg border shrink-0 flex items-center justify-center text-xs font-bold"
                      style={{ backgroundColor: ct.bg, color: ct.text, borderColor: 'rgba(0,0,0,0.1)' }}
                      aria-hidden="true"
                    >
                      Aa
                    </span>
                    <span className="flex-1 min-w-0">
                      <span className="block text-sm font-medium" style={{ color: 'var(--nd-text,#111827)' }}>
                        {ct.label}
                      </span>
                      <span className="block text-xs" style={{ color: 'var(--nd-muted,#6B7280)' }}>
                        {ct.desc}
                      </span>
                    </span>
                    {prefs.colorTheme === ct.value && (
                      <span className="text-indigo-600 text-xs font-bold shrink-0" aria-hidden="true">✓</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="px-5 py-3 border-t shrink-0 text-xs"
          style={{ borderColor: 'var(--nd-border,#E5E7EB)', color: 'var(--nd-muted,#9CA3AF)', backgroundColor: 'var(--nd-card-bg,#fff)' }}
        >
          Settings are saved automatically in your browser.
        </div>
      </div>

      {/* ── FAB trigger button ─────────────────────────────────────────────── */}
      <button
        onClick={() => setOpen(v => !v)}
        aria-label={open ? 'Close accessibility panel' : 'Open accessibility settings'}
        aria-expanded={open}
        aria-haspopup="dialog"
        className="fixed bottom-6 right-6 z-[9998] w-14 h-14 rounded-full shadow-xl flex items-center justify-center transition-transform hover:scale-105 active:scale-95"
        style={{ backgroundColor: 'var(--nd-focus-bg,#4F46E5)', color: '#fff' }}
      >
        {/* Badge showing active count */}
        {activeCount > 0 && !open && (
          <span
            className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-orange-500 text-white text-[10px] font-bold flex items-center justify-center"
            aria-label={`${activeCount} accessibility settings active`}
          >
            {activeCount}
          </span>
        )}
        <span className="text-lg font-bold leading-none select-none" aria-hidden="true">
          {open ? '✕' : 'A♿'}
        </span>
      </button>
    </>
  )
}
