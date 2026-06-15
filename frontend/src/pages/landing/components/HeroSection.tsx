import { ArrowRight, Play } from 'lucide-react'

export default function HeroSection() {
  return (
    <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-white via-blue-50/30 to-white">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Left Content */}
          <div className="space-y-8 animate-fade-in">
            <div className="space-y-4">
              <div className="inline-block px-3 py-1 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full">
                🚀 AI-Powered Hiring
              </div>
              <h1 className="text-5xl lg:text-6xl font-bold text-gray-900 leading-tight">
                Hire Smarter with AI-Powered Talent Matching
              </h1>
              <p className="text-xl text-gray-600 leading-relaxed">
                Analyze candidates instantly using GitHub, LeetCode, and AI-driven insights. Make better hiring decisions in minutes, not days.
              </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 pt-4">
              <button className="px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-all duration-300 hover:shadow-lg hover:shadow-blue-600/30 flex items-center justify-center gap-2 group">
                Get Started
                <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
              </button>
              <button className="px-8 py-3 border-2 border-gray-300 text-gray-700 font-semibold rounded-lg hover:border-gray-400 hover:bg-gray-50 transition-all duration-300 flex items-center justify-center gap-2">
                <Play size={20} />
                Watch Demo
              </button>
            </div>

            {/* Trust Indicators */}
            <div className="flex items-center gap-6 pt-4 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <div className="flex -space-x-2">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 border-2 border-white flex items-center justify-center text-white text-xs font-bold"
                    >
                      {i}
                    </div>
                  ))}
                </div>
                <span>500+ teams already hiring smarter</span>
              </div>
            </div>
          </div>

          {/* Right - Dashboard Mock */}
          <div className="relative animate-fade-in-delay">
            {/* Floating Card 1 - Candidate Score */}
            <div className="absolute top-0 right-0 w-80 bg-white rounded-2xl shadow-xl p-6 border border-gray-100 hover:shadow-2xl transition-shadow duration-300 z-10">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">Candidate Match</h3>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-semibold">
                  85%
                </span>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Overall Score</span>
                  <span className="font-bold text-gray-900">8.5/10</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full" style={{ width: '85%' }}></div>
                </div>
                <div className="grid grid-cols-3 gap-2 pt-2">
                  <div className="text-center">
                    <div className="text-lg font-bold text-gray-900">12</div>
                    <div className="text-xs text-gray-500">Repos</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-gray-900">156</div>
                    <div className="text-xs text-gray-500">LeetCode</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-gray-900">5y</div>
                    <div className="text-xs text-gray-500">Experience</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Floating Card 2 - Recruiter Dashboard */}
            <div className="absolute bottom-0 left-0 w-80 bg-white rounded-2xl shadow-xl p-6 border border-gray-100 hover:shadow-2xl transition-shadow duration-300 z-20">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">Top Candidates</h3>
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full font-semibold">
                  12 new
                </span>
              </div>
              <div className="space-y-3">
                {[
                  { name: 'Sarah Chen', score: 92, role: 'Senior Engineer' },
                  { name: 'Alex Kumar', score: 88, role: 'Full Stack Dev' },
                  { name: 'Emma Wilson', score: 85, role: 'Backend Dev' },
                ].map((candidate, i) => (
                  <div key={i} className="flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg transition-colors">
                    <div>
                      <div className="text-sm font-semibold text-gray-900">{candidate.name}</div>
                      <div className="text-xs text-gray-500">{candidate.role}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold text-blue-600">{candidate.score}%</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Background Gradient */}
            <div className="absolute inset-0 bg-gradient-to-br from-blue-100/40 to-purple-100/40 rounded-3xl blur-3xl -z-10"></div>
          </div>
        </div>
      </div>
    </section>
  )
}
