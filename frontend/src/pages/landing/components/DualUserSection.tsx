import { CheckCircle, TrendingUp, BookOpen, Clock, Award, Zap } from 'lucide-react'

export default function DualUserSection() {
  return (
    <section id="candidates" className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
          {/* For Candidates */}
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
                For Candidates
              </h2>
              <p className="text-lg text-gray-600">
                Get evaluated fairly and receive personalized growth insights
              </p>
            </div>

            <div className="space-y-4">
              {[
                {
                  icon: BookOpen,
                  title: 'Track Applications',
                  description: 'See all your applications in one place with real-time status updates',
                },
                {
                  icon: TrendingUp,
                  title: 'Get Feedback',
                  description: 'Receive detailed AI-powered feedback on your strengths and areas to improve',
                },
                {
                  icon: Award,
                  title: 'Improve Skills',
                  description: 'Get personalized recommendations to level up your technical abilities',
                },
              ].map((item, i) => {
                const Icon = item.icon
                return (
                  <div key={i} className="flex gap-4 p-4 rounded-xl hover:bg-blue-50 transition-colors group cursor-pointer">
                    <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-200 transition-colors">
                      <Icon size={20} className="text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-1">{item.title}</h3>
                      <p className="text-sm text-gray-600">{item.description}</p>
                    </div>
                  </div>
                )
              })}
            </div>

            <button className="w-full px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors">
              Sign Up as Candidate
            </button>
          </div>

          {/* For Recruiters */}
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
                For Recruiters
              </h2>
              <p className="text-lg text-gray-600">
                Find top talent faster and make data-driven hiring decisions
              </p>
            </div>

            <div className="space-y-4">
              {[
                {
                  icon: Zap,
                  title: 'Rank Candidates',
                  description: 'See candidates ranked by match score with AI-powered insights',
                },
                {
                  icon: Clock,
                  title: 'Save Time',
                  description: 'Reduce screening time from hours to minutes with automated evaluation',
                },
                {
                  icon: CheckCircle,
                  title: 'Make Better Decisions',
                  description: 'Data-driven insights help you hire the right people faster',
                },
              ].map((item, i) => {
                const Icon = item.icon
                return (
                  <div key={i} className="flex gap-4 p-4 rounded-xl hover:bg-blue-50 transition-colors group cursor-pointer">
                    <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-200 transition-colors">
                      <Icon size={20} className="text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-1">{item.title}</h3>
                      <p className="text-sm text-gray-600">{item.description}</p>
                    </div>
                  </div>
                )
              })}
            </div>

            <button className="w-full px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors">
              Sign Up as Recruiter
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
