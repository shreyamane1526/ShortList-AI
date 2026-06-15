import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

// Attach JWT from localStorage on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  try {
    const raw = localStorage.getItem('nd_preferences')
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed && parsed.ndModeEnabled) {
        config.headers['X-ND-Mode'] = 'true'
      }
    }
  } catch {}
  return config
})

// On 401 → clear token and redirect to /auth
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/auth'
    }
    return Promise.reject(err)
  },
)

export default api
