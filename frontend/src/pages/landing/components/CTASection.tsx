import { ArrowRight } from 'lucide-react'

export default function CTASection() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-r from-blue-600 to-blue-700">
      <div className="max-w-4xl mx-auto text-center space-y-8">
        {/* Heading */}
        <div className="space-y-4">
          <h2 className="text-4xl lg:text-5xl font-bold text-white">
            Start Building Smarter Teams Today
          </h2>
          <p className="text-xl text-blue-100">
            Join hundreds of companies using AI to hire better talent
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
          <button className="px-8 py-4 bg-white text-blue-600 font-bold rounded-lg hover:bg-blue-50 transition-all duration-300 hover:shadow-lg flex items-center justify-center gap-2 group">
            Get Started Free
            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>
          <button className="px-8 py-4 border-2 border-white text-white font-bold rounded-lg hover:bg-white/10 transition-all duration-300 flex items-center justify-center gap-2">
            Schedule Demo
          </button>
        </div>

        {/* Trust Text */}
        <p className="text-blue-100 text-sm">
          No credit card required • 14-day free trial • Cancel anytime
        </p>
      </div>
    </section>
  )
}
