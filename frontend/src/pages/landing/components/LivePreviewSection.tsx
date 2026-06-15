import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Users, BarChart3 } from 'lucide-react'

export default function LivePreviewSection() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            See It In Action
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Beautiful, intuitive interfaces for both candidates and recruiters
          </p>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-xl">
          <Tabs defaultValue="candidate" className="w-full">
            <TabsList className="w-full rounded-none border-b border-gray-100 bg-gray-50 p-0">
              <TabsTrigger
                value="candidate"
                className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:bg-white"
              >
                <Users size={20} className="mr-2" />
                Candidate Dashboard
              </TabsTrigger>
              <TabsTrigger
                value="recruiter"
                className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:bg-white"
              >
                <BarChart3 size={20} className="mr-2" />
                Recruiter Dashboard
              </TabsTrigger>
            </TabsList>

            {/* Candidate Dashboard */}
            <TabsContent value="candidate" className="p-8">
              <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900">My Applications</h3>
                    <p className="text-gray-600">Track your job applications and evaluations</p>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-blue-600">5</div>
                    <div className="text-sm text-gray-600">Total applications</div>
                  </div>
                </div>

                {/* Application Cards */}
                <div className="space-y-3">
                  {[
                    { job: 'Senior Backend Engineer', company: 'TechCorp', score: 92, status: 'Shortlisted' },
                    { job: 'Full Stack Developer', company: 'StartupHub', score: 88, status: 'Evaluating' },
                    { job: 'DevOps Engineer', company: 'CloudScale', score: 85, status: 'Pending' },
                  ].map((app, i) => (
                    <div key={i} className="flex items-center justify-between p-4 border border-gray-100 rounded-xl hover:border-blue-200 hover:bg-blue-50/50 transition-all">
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900">{app.job}</h4>
                        <p className="text-sm text-gray-600">{app.company}</p>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <div className="text-lg font-bold text-gray-900">{app.score}%</div>
                          <div className="text-xs text-gray-500">Match</div>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          app.status === 'Shortlisted'
                            ? 'bg-green-100 text-green-700'
                            : app.status === 'Evaluating'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}>
                          {app.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>

            {/* Recruiter Dashboard */}
            <TabsContent value="recruiter" className="p-8">
              <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900">Candidates</h3>
                    <p className="text-gray-600">Ranked by AI match score</p>
                  </div>
                  <div className="flex gap-4">
                    <div className="text-right">
                      <div className="text-3xl font-bold text-blue-600">24</div>
                      <div className="text-sm text-gray-600">Total candidates</div>
                    </div>
                    <div className="text-right">
                      <div className="text-3xl font-bold text-green-600">8</div>
                      <div className="text-sm text-gray-600">Shortlisted</div>
                    </div>
                  </div>
                </div>

                {/* Candidate Table */}
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left py-3 px-4 font-semibold text-gray-700">Candidate</th>
                        <th className="text-left py-3 px-4 font-semibold text-gray-700">Score</th>
                        <th className="text-left py-3 px-4 font-semibold text-gray-700">Skills</th>
                        <th className="text-left py-3 px-4 font-semibold text-gray-700">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { name: 'Sarah Chen', score: 92, skills: 'Python, React, AWS', status: 'Shortlisted' },
                        { name: 'Alex Kumar', score: 88, skills: 'Node.js, PostgreSQL', status: 'Shortlisted' },
                        { name: 'Emma Wilson', score: 85, skills: 'Java, Spring Boot', status: 'Evaluating' },
                      ].map((candidate, i) => (
                        <tr key={i} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                          <td className="py-4 px-4">
                            <div className="font-semibold text-gray-900">{candidate.name}</div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-2">
                              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-bold">
                                {candidate.score}
                              </div>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="text-sm text-gray-600">{candidate.skills}</div>
                          </td>
                          <td className="py-4 px-4">
                            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                              candidate.status === 'Shortlisted'
                                ? 'bg-green-100 text-green-700'
                                : 'bg-blue-100 text-blue-700'
                            }`}>
                              {candidate.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </section>
  )
}
