# Landing Page - Example Usage

## Basic Usage

### Import and Use

```typescript
import { LandingPage } from '@/pages/landing'

export default function App() {
  return <LandingPage />
}
```

## Router Integration

### React Router Setup

```typescript
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { LandingPage } from '@/pages/landing'
import AuthPage from '@/pages/AuthPage'
import CandidateDashboard from '@/pages/candidate/Dashboard'
import RecruiterDashboard from '@/pages/recruiter/Dashboard'

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />
        
        {/* Protected Routes */}
        <Route path="/candidate/*" element={<CandidateDashboard />} />
        <Route path="/dashboard/*" element={<RecruiterDashboard />} />
      </Routes>
    </Router>
  )
}
```

## Customization Examples

### Change Primary Color

**Before:**
```tsx
className="bg-blue-600 hover:bg-blue-700"
```

**After:**
```tsx
className="bg-purple-600 hover:bg-purple-700"
```

### Update Hero Headline

**In HeroSection.tsx:**
```tsx
<h1 className="text-5xl lg:text-6xl font-bold text-gray-900 leading-tight">
  Your Custom Headline Here
</h1>
```

### Update Features

**In FeaturesSection.tsx:**
```tsx
const features = [
  {
    icon: Brain,
    title: 'Your Feature Title',
    description: 'Your feature description',
    color: 'from-blue-500 to-blue-600',
  },
  // ... more features
]
```

### Update Company Name

**Find and replace:**
```bash
Find: "Shortlist AI"
Replace: "Your Company Name"
```

## Navigation Integration

### Update Navbar Links

```typescript
// Navbar.tsx
const navLinks = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'For Recruiters', href: '#recruiters' },
  { label: 'For Candidates', href: '#candidates' },
]

// Update buttons
<button onClick={() => navigate('/auth')}>Login</button>
<button onClick={() => navigate('/auth?role=candidate')}>Get Started</button>
```

### Update CTA Buttons

```typescript
// CTASection.tsx
import { useNavigate } from 'react-router-dom'

export default function CTASection() {
  const navigate = useNavigate()

  return (
    <button onClick={() => navigate('/auth?role=candidate')}>
      Get Started Free
    </button>
  )
}
```

## Analytics Integration

### Google Analytics

```typescript
// LandingPage.tsx
import { useEffect } from 'react'

export default function LandingPage() {
  useEffect(() => {
    // Page view
    window.gtag?.('event', 'page_view', {
      page_path: '/',
      page_title: 'Shortlist AI - Landing Page',
    })
  }, [])

  return (
    // ... component
  )
}
```

### Track Button Clicks

```typescript
<button onClick={() => {
  window.gtag?.('event', 'get_started_click', {
    location: 'hero_section',
  })
  navigate('/auth')
}}>
  Get Started
</button>
```

### Track Section Views

```typescript
useEffect(() => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        window.gtag?.('event', 'section_view', {
          section: entry.target.id,
        })
      }
    })
  })

  document.querySelectorAll('section').forEach((section) => {
    observer.observe(section)
  })

  return () => observer.disconnect()
}, [])
```

## Email Capture

### Add Newsletter Signup

```typescript
// components/NewsletterSection.tsx
import { useState } from 'react'

export default function NewsletterSection() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const response = await fetch('/api/newsletter/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })

      if (response.ok) {
        setSubmitted(true)
        setEmail('')
      }
    } catch (error) {
      console.error('Subscription error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="py-20 px-4 bg-gray-50">
      <div className="max-w-2xl mx-auto text-center">
        <h2 className="text-3xl font-bold mb-4">Stay Updated</h2>
        <p className="text-gray-600 mb-8">Get the latest updates on AI hiring</p>

        {submitted ? (
          <p className="text-green-600 font-semibold">
            Thanks for subscribing! Check your email.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="flex gap-2 max-w-md mx-auto">
            <input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="flex-1 px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Subscribing...' : 'Subscribe'}
            </button>
          </form>
        )}
      </div>
    </section>
  )
}
```

Add to LandingPage.tsx:
```typescript
import NewsletterSection from './components/NewsletterSection'

export default function LandingPage() {
  return (
    <div>
      <Navbar scrolled={scrolled} />
      <HeroSection />
      <SocialProof />
      <HowItWorks />
      <FeaturesSection />
      <DualUserSection />
      <NewsletterSection />  {/* Add here */}
      <LivePreviewSection />
      <CTASection />
      <Footer />
    </div>
  )
}
```

## Add Testimonials Section

```typescript
// components/TestimonialsSection.tsx
export default function TestimonialsSection() {
  const testimonials = [
    {
      name: 'Sarah Chen',
      role: 'Hiring Manager at TechCorp',
      image: '👩‍💼',
      quote: 'Shortlist AI reduced our hiring time by 60%. Incredible tool!',
    },
    {
      name: 'Alex Kumar',
      role: 'CTO at StartupHub',
      image: '👨‍💼',
      quote: 'The AI evaluation is spot-on. We found our best engineers using this.',
    },
    {
      name: 'Emma Wilson',
      role: 'Recruiter at CloudScale',
      image: '👩‍💼',
      quote: 'Finally, a tool that actually understands technical skills.',
    },
  ]

  return (
    <section className="py-20 px-4 bg-white">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-4xl font-bold text-center mb-16">
          Loved by Hiring Teams
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {testimonials.map((testimonial, i) => (
            <div key={i} className="bg-gray-50 rounded-2xl p-8 border border-gray-100">
              <div className="flex items-center gap-4 mb-4">
                <div className="text-4xl">{testimonial.image}</div>
                <div>
                  <h3 className="font-bold text-gray-900">{testimonial.name}</h3>
                  <p className="text-sm text-gray-600">{testimonial.role}</p>
                </div>
              </div>
              <p className="text-gray-700 italic">"{testimonial.quote}"</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

## Add Pricing Section

```typescript
// components/PricingSection.tsx
export default function PricingSection() {
  const plans = [
    {
      name: 'Starter',
      price: '$99',
      period: '/month',
      features: [
        'Up to 10 evaluations/month',
        'Basic dashboard',
        'Email support',
      ],
    },
    {
      name: 'Professional',
      price: '$299',
      period: '/month',
      featured: true,
      features: [
        'Unlimited evaluations',
        'Advanced dashboard',
        'Priority support',
        'Custom integrations',
      ],
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: 'pricing',
      features: [
        'Everything in Professional',
        'Dedicated account manager',
        'Custom features',
        'SLA guarantee',
      ],
    },
  ]

  return (
    <section className="py-20 px-4 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-4xl font-bold text-center mb-16">
          Simple, Transparent Pricing
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan, i) => (
            <div
              key={i}
              className={`rounded-2xl p-8 ${
                plan.featured
                  ? 'bg-blue-600 text-white border-2 border-blue-600 transform scale-105'
                  : 'bg-white border border-gray-200'
              }`}
            >
              <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
              <div className="mb-6">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-sm opacity-75">/{plan.period}</span>
              </div>
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, j) => (
                  <li key={j} className="flex items-center gap-2">
                    <span>✓</span> {feature}
                  </li>
                ))}
              </ul>
              <button
                className={`w-full py-3 rounded-lg font-semibold transition-colors ${
                  plan.featured
                    ? 'bg-white text-blue-600 hover:bg-gray-100'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                Get Started
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

## Add FAQ Section

```typescript
// components/FAQSection.tsx
import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

export default function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  const faqs = [
    {
      question: 'How does the AI evaluation work?',
      answer: 'Our AI analyzes GitHub repos, LeetCode profiles, and resumes to provide comprehensive candidate evaluations.',
    },
    {
      question: 'Is my data secure?',
      answer: 'Yes, we use enterprise-grade encryption and comply with GDPR, CCPA, and other data protection regulations.',
    },
    {
      question: 'Can I integrate with my ATS?',
      answer: 'Yes, we support integrations with popular ATS platforms like Greenhouse, Lever, and more.',
    },
    {
      question: 'What is the pricing?',
      answer: 'We offer flexible pricing starting at $99/month. Check our pricing page for details.',
    },
  ]

  return (
    <section className="py-20 px-4 bg-white">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-4xl font-bold text-center mb-16">
          Frequently Asked Questions
        </h2>

        <div className="space-y-4">
          {faqs.map((faq, i) => (
            <div key={i} className="border border-gray-200 rounded-lg">
              <button
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
              >
                <span className="font-semibold text-gray-900">{faq.question}</span>
                <ChevronDown
                  size={20}
                  className={`transition-transform ${
                    openIndex === i ? 'rotate-180' : ''
                  }`}
                />
              </button>
              {openIndex === i && (
                <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                  <p className="text-gray-700">{faq.answer}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

## Complete Example

```typescript
// LandingPage.tsx with all sections
import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import HeroSection from './components/HeroSection'
import SocialProof from './components/SocialProof'
import HowItWorks from './components/HowItWorks'
import FeaturesSection from './components/FeaturesSection'
import DualUserSection from './components/DualUserSection'
import TestimonialsSection from './components/TestimonialsSection'
import PricingSection from './components/PricingSection'
import FAQSection from './components/FAQSection'
import NewsletterSection from './components/NewsletterSection'
import LivePreviewSection from './components/LivePreviewSection'
import CTASection from './components/CTASection'
import Footer from './components/Footer'

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div className="min-h-screen bg-white">
      <Navbar scrolled={scrolled} />
      <HeroSection />
      <SocialProof />
      <HowItWorks />
      <FeaturesSection />
      <DualUserSection />
      <TestimonialsSection />
      <PricingSection />
      <FAQSection />
      <NewsletterSection />
      <LivePreviewSection />
      <CTASection />
      <Footer />
    </div>
  )
}
```

---

**These examples show how to customize and extend the landing page!**
