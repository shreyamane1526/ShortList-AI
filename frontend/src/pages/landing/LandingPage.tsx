import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AnimatedCard from '@/components/ui/effects/AnimatedCard'
import SocialProof from './components/SocialProof'
import HowItWorks from './components/HowItWorks'
import FeaturesSection from './components/FeaturesSection'
import DualUserSection from './components/DualUserSection'
import LivePreviewSection from './components/LivePreviewSection'
import CTASection from './components/CTASection'
import Footer from './components/Footer'
import { Menu, X, Zap, Star, ArrowRight, Play } from 'lucide-react'

// ─── scroll hook ──────────────────────────────────────────────────────────────
function useScrolled(threshold = 50) {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > threshold)
    window.addEventListener('scroll', fn, { passive: true })
    return () => window.removeEventListener('scroll', fn)
  }, [threshold])
  return scrolled
}

// ─── Navbar ───────────────────────────────────────────────────────────────────
function Navbar() {
  const scrolled = useScrolled()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  const links = [
    { label: 'Features',      href: '#features' },
    { label: 'How It Works',  href: '#how-it-works' },
    { label: 'For Recruiters',href: '#recruiters' },
    { label: 'For Candidates',href: '#candidates' },
  ]

  return (
    <nav className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
      scrolled ? 'bg-white shadow-sm border-b border-gray-100' : 'bg-white/90 backdrop-blur-md'
    }`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <a href="/" className="flex items-center gap-2.5 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center shadow-sm">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-gray-900 text-lg tracking-tight">
              Shortlist<span className="text-blue-600">AI</span>
            </span>
          </a>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-7">
            {links.map(l => (
              <a key={l.label} href={l.href}
                className="text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors">
                {l.label}
              </a>
            ))}
          </div>

          {/* Desktop buttons */}
          <div className="hidden md:flex items-center gap-3">
            <button
              onClick={() => navigate('/auth')}
              className="px-4 py-2 text-sm font-semibold text-gray-700 hover:text-blue-600 transition-colors"
            >
              Log in
            </button>
            <button
              onClick={() => navigate('/auth')}
              className="px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors"
            >
              Get Started
            </button>
          </div>

          {/* Mobile toggle */}
          <button onClick={() => setOpen(!open)} className="md:hidden p-2 text-gray-600">
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {/* Mobile menu */}
        {open && (
          <div className="md:hidden border-t border-gray-100 py-4 space-y-1 bg-white">
            {links.map(l => (
              <a key={l.label} href={l.href} onClick={() => setOpen(false)}
                className="block px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors">
                {l.label}
              </a>
            ))}
            <div className="flex gap-2 px-4 pt-3">
              <button
                onClick={() => navigate('/auth')}
                className="flex-1 py-2.5 text-sm font-semibold border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Log in
              </button>
              <button
                onClick={() => navigate('/auth')}
                className="flex-1 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors"
              >
                Get Started
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}

// ─── Hero ─────────────────────────────────────────────────────────────────────
function Hero() {
  const navigate = useNavigate()

  return (
    <section className="relative pt-24 pb-16 lg:pt-32 lg:pb-24 overflow-hidden bg-gradient-to-b from-white via-blue-50/30 to-white">
      {/* Background blobs */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-blue-50 rounded-full blur-3xl opacity-60 -translate-y-1/2 translate-x-1/3 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[400px] h-[600px] bg-indigo-50 rounded-full blur-3xl opacity-50 translate-y-1/2 -translate-x-1/4 pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">

          {/* Left copy */}
          <div className="space-y-8">
            <span className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-100 text-blue-700 text-xs font-semibold rounded-full">
              <Zap size={12} className="fill-blue-600 text-blue-600" />
              AI-Powered Hiring Platform
            </span>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black leading-[1.1] tracking-tight bg-gradient-to-r from-gray-900 via-blue-900 to-purple-900 bg-clip-text text-transparent mb-4">
              Hire Smarter with AI‑Powered Talent Matching
            </h1>

            <p className="text-lg sm:text-xl text-gray-500 leading-relaxed max-w-lg">
              Analyze candidates instantly using GitHub, LeetCode, and AI-driven insights.
              Make better hiring decisions in minutes, not weeks.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => navigate('/auth')}
                className="group inline-flex items-center justify-center gap-2 px-7 py-3.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 shadow-lg shadow-blue-600/30 transition-all"
              >
                Get Started Free
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </button>
              <button className="inline-flex items-center justify-center gap-2 px-7 py-3.5 border-2 border-gray-200 text-gray-700 font-semibold rounded-xl hover:border-blue-300 hover:bg-blue-50 transition-all">
                <Play size={16} className="fill-gray-600 text-gray-600" />
                Watch Demo
              </button>
            </div>

            <div className="flex items-center gap-4 pt-2">
              <div className="flex -space-x-2.5">
                {['SC', 'AK', 'EW', 'MR'].map((initials, i) => (
                  <div
                    key={i}
                    className="w-9 h-9 rounded-full border-2 border-white flex items-center justify-center text-white text-xs font-bold shadow-sm"
                    style={{ background: ['#2563eb', '#7c3aed', '#059669', '#dc2626'][i] }}
                  >
                    {initials}
                  </div>
                ))}
              </div>
              <div>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map(s => (
                    <Star key={s} size={13} className="fill-amber-400 text-amber-400" />
                  ))}
                </div>
                <p className="text-sm text-gray-500 mt-0.5">
                  Trusted by <span className="font-semibold text-gray-700">500+</span> hiring teams
                </p>
              </div>
            </div>
          </div>

          {/* Right mock dashboard */}
          <div className="relative space-y-4">
            {/* Card 1 – AI Score */}
            <AnimatedCard className="bg-white rounded-2xl border border-gray-100 shadow-xl p-5 relative" delay={0.1}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">AI Evaluation</p>
                  <h3 className="font-bold text-gray-900 mt-0.5">Sarah Chen</h3>
                </div>
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg">
                  <span className="text-white font-black text-lg">92</span>
                </div>
              </div>
              <div className="space-y-2.5">
                {[
                  { label: 'Technical Skills', pct: 95, color: 'bg-blue-500' },
                  { label: 'GitHub Activity',  pct: 88, color: 'bg-purple-500' },
                  { label: 'Problem Solving',  pct: 91, color: 'bg-emerald-500' },
                ].map(bar => (
                  <div key={bar.label}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-600">{bar.label}</span>
                      <span className="font-semibold text-gray-800">{bar.pct}%</span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className={`h-full ${bar.color} rounded-full`} style={{ width: `${bar.pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex gap-2 mt-4">
                <span className="px-2.5 py-1 bg-green-50 text-green-700 text-xs font-semibold rounded-full">✓ Strong Match</span>
                <span className="px-2.5 py-1 bg-blue-50 text-blue-700 text-xs font-semibold rounded-full">Python · React · AWS</span>
              </div>
            </AnimatedCard>

            {/* Card 2 – Top Candidates */}
            <AnimatedCard className="bg-white rounded-2xl border border-gray-100 shadow-xl p-5" delay={0.2}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-gray-900">Top Candidates</h3>
                <span className="px-2.5 py-1 bg-blue-50 text-blue-700 text-xs font-semibold rounded-full">12 new</span>
              </div>
              <div className="space-y-3">
                {[
                  { name: 'Sarah Chen', role: 'Senior Engineer', score: 92, color: '#2563eb' },
                  { name: 'Alex Kumar', role: 'Full Stack Dev',  score: 88, color: '#7c3aed' },
                  { name: 'Emma Wilson', role: 'Backend Dev',    score: 85, color: '#059669' },
                ].map((c, i) => (
                  <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                      style={{ background: c.color }}
                    >
                      {c.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-gray-900 text-sm truncate">{c.name}</p>
                      <p className="text-xs text-gray-500">{c.role}</p>
                    </div>
                    <span className="text-sm font-bold text-blue-600 shrink-0">{c.score}%</span>
                  </div>
                ))}
              </div>
            </AnimatedCard>

            {/* Floating badge */}
            <div className="absolute -top-3 -right-3 bg-white rounded-xl shadow-lg border border-gray-100 px-3 py-2 flex items-center gap-2">
              <motion.div
                className="w-2 h-2 rounded-full bg-green-500"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ repeat: Infinity, duration: 1.5 }}
              />
              <span className="text-xs font-semibold text-gray-700">AI Evaluating…</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Testimonials (inline — no separate file needed) ──────────────────────────
function Testimonials() {
  const testimonials = [
    {
      quote: "Shortlist AI cut our screening time by 70%. We find better candidates faster than ever.",
      name: "Priya Sharma",
      role: "Head of Engineering, TechCorp",
      initials: "PS",
      color: "#2563eb",
    },
    {
      quote: "The AI feedback helped me understand exactly what skills to build. I got shortlisted within a week.",
      name: "Alex Kumar",
      role: "Software Engineer",
      initials: "AK",
      color: "#7c3aed",
    },
    {
      quote: "Finally a hiring tool that's fair and transparent. The bias-free evaluation is a game changer.",
      name: "Emma Wilson",
      role: "CTO, StartupHub",
      initials: "EW",
      color: "#059669",
    },
  ]

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">What people are saying</h2>
          <p className="text-xl text-gray-600">Trusted by candidates and recruiters worldwide</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {testimonials.map((t, i) => (
            <motion.div
              key={i}
              className="bg-white rounded-2xl border border-gray-100 p-8 shadow-sm hover:shadow-md transition-shadow"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <div className="flex gap-1 mb-4">
                {[1,2,3,4,5].map(s => (
                  <Star key={s} size={14} className="fill-amber-400 text-amber-400" />
                ))}
              </div>
              <p className="text-gray-700 text-sm leading-relaxed mb-6">"{t.quote}"</p>
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
                  style={{ background: t.color }}
                >
                  {t.initials}
                </div>
                <div>
                  <p className="font-semibold text-gray-900 text-sm">{t.name}</p>
                  <p className="text-xs text-gray-500">{t.role}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar />
      <main>
        <Hero />
        <SocialProof />
        <HowItWorks />
        <FeaturesSection />
        <DualUserSection />
        <LivePreviewSection />
        <Testimonials />
        <CTASection />
      </main>
      <Footer />
    </div>
  )
}
