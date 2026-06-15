import { Brain, Target, Zap, BarChart3, Users, Shield, ArrowRight } from 'lucide-react'

export default function FeaturesSection() {
  const features = [
    {
      icon: Brain,
      title: 'AI Evaluation Engine',
      description: 'Advanced machine learning analyzes technical skills, project quality, and cultural fit.',
      color: 'from-blue-500 to-blue-600',
    },
    {
      icon: Target,
      title: 'Skill Gap Detection',
      description: 'Identify exactly what skills candidates need to develop for growth.',
      color: 'from-purple-500 to-purple-600',
    },
    {
      icon: Zap,
      title: 'Real-time Matching',
      description: 'Instant candidate-to-job matching with confidence scores.',
      color: 'from-pink-500 to-pink-600',
    },
    {
      icon: BarChart3,
      title: 'Recruiter Dashboard',
      description: 'Beautiful, intuitive interface to manage and rank candidates.',
      color: 'from-green-500 to-green-600',
    },
    {
      icon: Users,
      title: 'Candidate Insights',
      description: 'Personalized feedback and growth recommendations for every candidate.',
      color: 'from-orange-500 to-orange-600',
    },
    {
      icon: Shield,
      title: 'Inclusion & Fairness',
      description: 'Bias-free evaluation ensuring equal opportunities for all candidates.',
      color: 'from-red-500 to-red-600',
    },
  ]

  return (
    <section id="features" className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-white to-gray-50">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            Powerful Features
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Everything you need to build smarter hiring teams
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <div
                key={index}
                className="group bg-white rounded-2xl p-8 border border-gray-100 hover:border-blue-200 hover:shadow-xl transition-all duration-300 cursor-pointer"
              >
                {/* Icon */}
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                  <Icon size={24} className="text-white" />
                </div>

                {/* Content */}
                <h3 className="text-lg font-bold text-gray-900 mb-3">
                  {feature.title}
                </h3>
                <p className="text-gray-600 text-sm leading-relaxed mb-4">
                  {feature.description}
                </p>

                {/* Learn More Link */}
                <div className="flex items-center text-blue-600 font-semibold text-sm group-hover:gap-2 transition-all">
                  Learn more
                  <ArrowRight size={16} className="ml-1 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
