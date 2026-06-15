import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'
import type { User } from '@/types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (full_name: string, email: string, password: string, role: 'candidate' | 'recruiter' | 'superadmin') => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const stored = localStorage.getItem('user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    try {
      const res = await api.get('/auth/me')
      const u: User = res.data.user
      setUser(u)
      localStorage.setItem('user', JSON.stringify(u))
    } catch {
      setUser(null)
      localStorage.removeItem('user')
      localStorage.removeItem('access_token')
    }
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      refreshUser().finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [refreshUser])

  const login = async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password })
    const { user: u, access_token } = res.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('user', JSON.stringify(u))
    setUser(u)
  }

  const register = async (
    full_name: string,
    email: string,
    password: string,
    role: 'candidate' | 'recruiter' | 'superadmin',
  ) => {
    const res = await api.post('/auth/register', { full_name, email, password, role })
    const { user: u, access_token } = res.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('user', JSON.stringify(u))
    setUser(u)
  }

  const logout = async () => {
    try { await api.post('/auth/logout') } catch { /* ignore */ }
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}