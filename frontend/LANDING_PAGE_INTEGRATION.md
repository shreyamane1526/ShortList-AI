# Landing Page Integration Guide

## 🚀 Quick Integration (5 minutes)

### Step 1: Update Your Router

In `frontend/src/App.tsx` or your main router file:

```typescript
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { LandingPage } from '@/pages/landing'
import CandidateLayout from '@/components/layout/CandidateLayout'
import RecruiterLayout from '@/components/layout/RecruiterLayout'

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Landing Page - Public */}
        <Route path="/" element={<LandingPage />} />
        
        {/* Candidate Routes */}
        <Route path="/candidate/*" element={<CandidateLayout />} />
        
        {/* Recruiter Routes */}
        <Route path="/dashboard/*" element={<RecruiterLayout />} />
      </Routes>
    </Router>
  )
}
```

### Step 2: Import CSS

In `frontend/src/main.tsx`:

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import './styles/landing.css'  // Add this line

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### Step 3: Install Dependencies

```bash
cd frontend
npm install @radix-ui/react-tabs
```

### Step 4: Test

```bash
npm run dev
```

Visit `http://localhost:5173` to see the landing page!

---

## 🔗 Navigation Integration

### Update Navbar Links

In `frontend/src/pages/landing/components/Navbar.tsx`:

```typescript
const navLinks = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'For Recruiters', href: '#recruiters' },
  { label: 'For Candidates', href: '#candidates' },
]

// Update buttons to navigate to auth or dashboard
<button onClick={() => navigate('/auth')}>Login</button>
<button onClick={() => navigate('/auth?role=candidate')}>Get Started</button>
```

### Update CTA Buttons

In `frontend/src/pages/landing/components/CTASection.tsx`:

```typescript
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

### Update Footer Links

In `frontend/src/pages/landing/components/Footer.tsx`:

```typescript
const footerLinks = {
  Product: [
    { label: 'Features', href: '#features' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Pricing', href: '/pricing' },
    { label: 'Security', href: '/security' },
  ],
  // ... rest of links
}
```

---

## 🎨 Customization

### Update Brand Colors

1. **Update Navbar Logo**:
```typescript
// Navbar.tsx
<div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg">
  {/* Change from-blue-600 to-blue-700 to your colors */}
</div>
```

2. **Update Primary Buttons**:
```typescript
// Change all instances of bg-blue-600 to your color
className="bg-blue-600 hover:bg-blue-700"
```

3. **Update Gradients**:
```typescript
// HeroSection.tsx
className="bg-gradient-to-b from-white via-blue-50/30 to-white"
// Change blue-50 to your color
```

### Update Content

1. **Hero Headline**:
```typescript
// HeroSection.tsx
<h1>Your custom headline here</h1>
```

2. **Features**:
```typescript
// FeaturesSection.tsx
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

3. **Company Name**:
```bash
# Find and replace all instances
Find: "Shortlist AI"
Replace: "Your Company Name"
```

---

## 📊 Analytics Integration

### Add Google Analytics

In `frontend/src/pages/landing/LandingPage.tsx`:

```typescript
import { useEffect } from 'react'

export default function LandingPage() {
  useEffect(() => {
    // Google Analytics
    window.gtag?.('event', 'page_view', {
      page_path: '/',
      page_title: 'Shortlist AI - Landing Page',
    })
  }, [])

  return (
    // ... rest of component
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

---

## 📧 Email Capture

### Add Newsletter Signup

Create `frontend/src/pages/landing/components/NewsletterSection.tsx`:

```typescript
import { useState } from 'react'

export default function NewsletterSection() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Call your API
    await fetch('/api/newsletter/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })
    
    setSubmitted(true)
    setEmail('')
  }

  return (
    <section className="py-20 px-4 bg-gray-50">
      <div className="max-w-2xl mx-auto text-center">
        <h2 className="text-3xl font-bold mb-4">Stay Updated</h2>
        <p className="text-gray-600 mb-8">Get the latest updates on AI hiring</p>
        
        {submitted ? (
          <p className="text-green-600 font-semibold">Thanks for subscribing!</p>
        ) : (
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="flex-1 px-4 py-3 rounded-lg border border-gray-300"
            />
            <button
              type="submit"
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Subscribe
            </button>
          </form>
        )}
      </div>
    </section>
  )
}
```

Add to `LandingPage.tsx`:
```typescript
import NewsletterSection from './components/NewsletterSection'

export default function LandingPage() {
  return (
    <div>
      {/* ... other sections */}
      <NewsletterSection />
      <CTASection />
      <Footer />
    </div>
  )
}
```

---

## 🔐 Security Considerations

### Protect API Endpoints

```typescript
// Only allow authenticated requests
const handleGetStarted = async () => {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCsrfToken(), // Add CSRF protection
    },
    body: JSON.stringify({ email, role }),
  })
}
```

### Rate Limiting

```typescript
// Implement rate limiting on backend
// POST /api/newsletter/subscribe - 5 requests per minute per IP
// POST /api/auth/register - 10 requests per hour per IP
```

---

## 🚀 Deployment

### Build for Production

```bash
cd frontend
npm run build
```

### Environment Variables

Create `.env.production`:

```
VITE_API_URL=https://api.shortlistai.com
VITE_GA_ID=G-XXXXXXXXXX
```

### Deploy to Vercel

```bash
vercel deploy --prod
```

### Deploy to Netlify

```bash
netlify deploy --prod --dir=dist
```

---

## 📱 Mobile Optimization

### Test on Mobile

```bash
# Start dev server
npm run dev

# Access from mobile device
http://your-ip:5173
```

### Common Mobile Issues

1. **Touch targets too small**: Ensure buttons are at least 44x44px
2. **Text too small**: Use responsive font sizes
3. **Horizontal scroll**: Check for overflow issues

---

## 🎯 SEO Optimization

### Add Meta Tags

In `frontend/index.html`:

```html
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="AI-powered hiring platform for modern teams" />
  <meta name="keywords" content="hiring, AI, recruitment, talent matching" />
  <meta property="og:title" content="Shortlist AI - Hire Smarter" />
  <meta property="og:description" content="AI-powered talent matching" />
  <meta property="og:image" content="/og-image.png" />
  <title>Shortlist AI - Hire Smarter with AI-Powered Talent Matching</title>
</head>
```

### Add Sitemap

Create `frontend/public/sitemap.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://shortlistai.com/</loc>
    <lastmod>2024-01-15</lastmod>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://shortlistai.com/features</loc>
    <lastmod>2024-01-15</lastmod>
    <priority>0.8</priority>
  </url>
</urlset>
```

---

## ✅ Pre-Launch Checklist

- [ ] Update all company branding
- [ ] Update all links and URLs
- [ ] Add analytics tracking
- [ ] Set up email capture
- [ ] Configure CTA buttons
- [ ] Test on all devices
- [ ] Test all links
- [ ] Test forms
- [ ] Performance optimization
- [ ] SEO optimization
- [ ] Security audit
- [ ] Accessibility audit
- [ ] Add favicon
- [ ] Add social media links
- [ ] Set up error tracking
- [ ] Configure CDN
- [ ] Set up monitoring
- [ ] Create privacy policy
- [ ] Create terms of service
- [ ] Deploy to production

---

## 🆘 Troubleshooting

### Styles not loading
```bash
# Clear cache and rebuild
rm -rf node_modules/.vite
npm run dev
```

### Components not found
```bash
# Check imports are correct
import { LandingPage } from '@/pages/landing'
```

### Animations not working
```bash
# Check landing.css is imported
import '@/styles/landing.css'
```

### Mobile menu not working
```bash
# Check state management
const [mobileOpen, setMobileOpen] = useState(false)
```

---

## 📞 Support

For issues:
1. Check the component files
2. Review the README
3. Check browser console for errors
4. Test in different browsers

---

**Ready to launch! 🚀**
