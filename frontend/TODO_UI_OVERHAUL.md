# UI Overhaul TODO - Particles, Animations, Effects

## Approved Plan Steps (Breakdown)

### 1. Install Dependencies ✅ [AI]
- cd frontend && npm i framer-motion react-tsparticles tsparticles-engine tsparticles-slim

### 2. Update Global Styles (index.css)
- Add neonGlow keyframes, scanlines CSS, particles-bg class, gradient mesh, update btn-primary for neon

### 3. Create Effects Components ✅
- ParticleBackground.tsx (lazy-load, mouse-responsive)
- GlitchText.tsx (random activation on headings)
- ScanlineOverlay.tsx (toggleable retro overlay)
- AnimatedCard.tsx (framer-motion HOC for shadcn cards)

### 4. Update App.tsx ✅
- Add MotionConfig, lazy ParticleBackground + Suspense
- Global ScanlineOverlay (Ctrl+S toggle)
- Neon spinners
- ParticleBackground.tsx (lazy-load, mouse-responsive)
- GlitchText.tsx (random activation on headings)
- ScanlineOverlay.tsx (toggleable retro overlay)
- AnimatedCard.tsx (framer-motion HOC for shadcn cards)

### 4. Update App.tsx
- Add MotionProvider, lazy ParticleBackground + Suspense
- Global ScanlineOverlay toggle state

### 5. Update LandingPage.tsx
- Hero h1 → GlitchText
- Wrap cards with AnimatedCard/motion.div (fade-up, hover lift)

### 6. Apply to Other Pages/Layouts
- Update dashboard cards (CandidateDashboard, RecruiterCandidates etc.) with motion

### 7. Test & Optimize
- npm run dev, check perf/mobile
- Lighthouse score >60 perf
- Add to main TODO.md

## Progress Tracker
- [ ] Step 1
- [ ] Step 2
- [ ] ...
