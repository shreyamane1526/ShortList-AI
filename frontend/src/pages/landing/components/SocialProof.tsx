export default function SocialProof() {
  const companies = [
    { name: 'TechCorp', logo: '🏢' },
    { name: 'StartupHub', logo: '🚀' },
    { name: 'InnovateLabs', logo: '⚡' },
    { name: 'FutureAI', logo: '🤖' },
    { name: 'CloudScale', logo: '☁️' },
    { name: 'DataFlow', logo: '📊' },
  ]

  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 bg-white border-y border-gray-100">
      <div className="max-w-7xl mx-auto">
        <p className="text-center text-sm font-semibold text-gray-600 mb-8">
          TRUSTED BY MODERN HIRING TEAMS
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8 items-center">
          {companies.map((company) => (
            <div
              key={company.name}
              className="flex flex-col items-center justify-center p-4 rounded-lg hover:bg-gray-50 transition-colors group cursor-pointer"
            >
              <div className="text-4xl mb-2 group-hover:scale-110 transition-transform">{company.logo}</div>
              <p className="text-sm text-gray-600 text-center font-medium">{company.name}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
