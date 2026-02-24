import axios from 'axios'

// In production FastAPI serves both API and frontend on same origin.
// In dev, Vite proxy forwards /api → localhost:8001.
const api = axios.create({ baseURL: '' })

api.interceptors.request.use(config => {
  // Read initData directly from Telegram's injected global — always available
  // inside a Mini App regardless of SDK initialization state.
  const tg = (window as any)?.Telegram?.WebApp
  const initDataRaw = tg?.initData || ''

  if (initDataRaw) {
    config.headers['Authorization'] = `tma ${initDataRaw}`
  } else if (import.meta.env.DEV) {
    config.headers['Authorization'] = `tma ${import.meta.env.VITE_DEV_INIT_DATA || 'dev'}`
  }
  return config
})

export default api

// Typed endpoint helpers
export const getMe           = ()                         => api.get('/api/me')
export const getCards        = ()                         => api.get('/api/cards')
export const getCard         = (id: string)               => api.get(`/api/cards/${id}`)
export const getPacks        = ()                         => api.get('/api/packs')
export const getPackStore    = ()                         => api.get('/api/packs/store')
export const openPack        = (id: string)               => api.post(`/api/packs/${id}/open`)
export const getEconomy      = ()                         => api.get('/api/economy')
export const claimDaily      = ()                         => api.post('/api/economy/daily')
export const getLeaderboard  = (metric = 'wins')          => api.get(`/api/leaderboard?metric=${metric}`)
export const createChallenge = (body: object)             => api.post('/api/battle/challenge', body)
export const acceptBattle    = (id: string, body: object) => api.post(`/api/battle/${id}/accept`, body)
export const getBattle       = (id: string)               => api.get(`/api/battle/${id}`)
export const generateLink    = ()                         => api.post('/api/link/generate')
