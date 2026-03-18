/**
 * Auth hook — simplified for prototype (always authenticated).
 */
import type { User } from '@/types'

const demoUser: User = {
  id: '00000000-0000-0000-0000-000000000002',
  email: 'demo@example.com',
  full_name: 'Demo User',
  role: 'admin',
  org_id: '00000000-0000-0000-0000-000000000001',
  organization_name: 'Demo Organization',
}

export const useAuth = () => {
  return {
    token: 'demo-token',
    user: demoUser,
    isAuthenticated: true,
    isLoading: false,
    login: (_token: string, _user: User) => {},
    logout: () => {},
    setUser: (_user: User) => {},
  }
}
