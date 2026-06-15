# ND Inclusive Candidate UI — TODO

## Step 1 — Preferences plumbing
- [ ] Create `src/context/NDPreferencesContext.tsx`
- [ ] Create `src/hooks/useNDPreferences.ts`
- [ ] Define `localStorage` key `nd_preferences` and persistence
- [ ] Inject OpenDyslexic via `@font-face` and apply `<html data-dyslexia="true">`
- [ ] Apply global theme/typography via CSS variables + root font-size

## Step 2 — Accessibility toolbar
- [ ] Create `src/components/accessibility/AccessibilityToolbar.tsx`
- [ ] Draggable bottom-right toolbar + `A♿` expander
- [ ] Wire all toggles to context setters

## Step 3 — Reading ruler overlay
- [ ] Implement mouse-following ruler overlay shown when enabled

## Step 4 — Candidate layout integration
- [ ] Wrap candidate UI with `NDPreferencesContext` provider in `CandidateLayout.tsx`
- [ ] Add Skip-to-main anchor at top
- [ ] Add persistent breadcrumb trail on candidate pages
- [ ] Implement Focus Mode dimming + hide decorative UI
- [ ] Add visible large focus rings + reduced-motion handling

## Step 5 — API header for ND mode
- [ ] Update `src/lib/api.ts` to send `X-ND-Mode: true` when ND enabled
- [ ] Ensure recruiter UI unaffected

## Step 6 — Typography rules
- [ ] Increase default line-height/letter-spacing in dyslexia mode
- [ ] Ensure never justified text on candidate pages

## Step 7 — Simplify language buttons + bullet points
- [ ] Add `SimplifyLanguageBlock` component calling `POST /api/chat/ask`
- [ ] Add buttons next to every long evaluation result text block
- [ ] Replace text with rewritten version
- [ ] Make feedback bullet-based by default

## Step 8 — Forms
- [ ] Add character/word counters to all candidate textareas
- [ ] Add inline helper text under each field
- [ ] Wizard-style group navigation (optional toggle) where missing
- [ ] Preserve form state on error

## Step 9 — Pass/fail accessibility
- [ ] Ensure no red/green-only indicators; add ✓/✗ + label

## Step 10 — Final verification
- [ ] Run `npm run build` and smoke test candidate pages
- [ ] Verify settings persist and apply globally

