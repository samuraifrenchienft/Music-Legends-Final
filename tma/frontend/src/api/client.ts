import axios from 'axios'

// In production FastAPI serves both API and frontend on same origin.
// In dev, Vite proxy forwards /api → localhost:8001.
const api = axios.create({ baseURL: '' })
const INIT_DATA_KEY = 'ml_tma_init_data'

function readInitDataFromUrl(): string {
  try {
    const fromSearch = new URLSearchParams(window.location.search).get('tgWebAppData')
    if (fromSearch) return fromSearch
    const hash = (window.location.hash || '').replace(/^#/, '')
    if (hash) {
      const fromHash = new URLSearchParams(hash).get('tgWebAppData')
      if (fromHash) return fromHash
    }
  } catch {
    // ignore
  }
  return ''
}

function getStableInitData(): string {
  const tg = (window as any)?.Telegram?.WebApp
  const fromTg = (tg?.initData || '').trim()
  if (fromTg) {
    try { window.sessionStorage.setItem(INIT_DATA_KEY, fromTg) } catch { /* ignore */ }
    return fromTg
  }

  const fromUrl = readInitDataFromUrl().trim()
  if (fromUrl) {
    try { window.sessionStorage.setItem(INIT_DATA_KEY, fromUrl) } catch { /* ignore */ }
    return fromUrl
  }

  try {
    return (window.sessionStorage.getItem(INIT_DATA_KEY) || '').trim()
  } catch {
    return ''
  }
}

async function waitForInitData(maxWaitMs = 2000): Promise<string> {
  const existing = getStableInitData()
  if (existing) return existing

  const started = Date.now()
  while (Date.now() - started < maxWaitMs) {
    await new Promise((resolve) => setTimeout(resolve, 50))
    const next = getStableInitData()
    if (next) return next
  }
  return ''
}

api.interceptors.request.use(config => {
  return Promise.resolve().then(async () => {
    // Keep a stable initData token across route changes and SDK timing quirks.
    const initDataRaw = await waitForInitData()

    if (initDataRaw) {
      config.headers['Authorization'] = `tma ${initDataRaw}`
      // Proxy-safe fallback in case Authorization is stripped upstream.
      config.headers['X-Telegram-Init-Data'] = initDataRaw
    } else if (import.meta.env.DEV) {
      const devInitData = import.meta.env.VITE_DEV_INIT_DATA || 'dev'
      config.headers['Authorization'] = `tma ${devInitData}`
      config.headers['X-Telegram-Init-Data'] = devInitData
    }
    return config
  })
})

export default api

// Typed endpoint helpers
export const getMe           = ()                         => api.get('/api/me')
export const getCards        = ()                         => api.get('/api/cards')
export const getCard         = (id: string)               => api.get(`/api/cards/${id}`)
export const getPacks        = ()                         => api.get('/api/packs')
export const getPackStore    = ()                         => api.get('/api/packs/store')
export const openPack        = (id: string)               => api.post(`/api/packs/${id}/open`)
export const buyPack         = (id: string)               => api.post(`/api/packs/${id}/purchase`)
export const getEconomy      = ()                         => api.get('/api/economy')
export const claimDaily      = ()                         => api.post('/api/economy/daily')
export const getLeaderboard  = (metric = 'wins')          => api.get(`/api/leaderboard?metric=${metric}`)
export const createChallenge = (body: object)             => api.post('/api/battle/challenge', body)
export const acceptBattle    = (id: string, body: object) => api.post(`/api/battle/${id}/accept`, body)
export const cancelBattle    = (id: string)               => api.post(`/api/battle/${id}/cancel`)
export const getBattle       = (id: string)               => api.get(`/api/battle/${id}`)
export const getIncomingBattles = ()                      => api.get('/api/battle/incoming')
export const getBattleUpdates = ()                        => api.get('/api/battle/updates')
export const searchPlayers   = (q: string, limit = 10)    => api.get(`/api/players/search?q=${encodeURIComponent(q)}&limit=${limit}`)
export const registerBattlePlayer = ()                    => api.post('/api/battle/register')
export const getBattleOpponents   = ()                    => api.get('/api/battle/opponents')
export const generateLink    = ()                         => api.post('/api/link/generate')
export const getMarketplace  = ()                         => api.get('/api/marketplace')
export const sellCard        = (body: object)             => api.post('/api/marketplace/sell', body)
export const buyListing      = (id: number)               => api.post(`/api/marketplace/buy/${id}`)
export const getTrades       = ()                         => api.get('/api/trades')
export const createTrade     = (body: object)             => api.post('/api/trades', body)
export const acceptTrade     = (id: string)               => api.post(`/api/trades/${id}/accept`)
export const cancelTrade     = (id: string)               => api.post(`/api/trades/${id}/cancel`)
export const searchTradePartners = (query = '')           => api.get(`/api/trades/partners?query=${encodeURIComponent(query)}`)
export const getPartnerCards = (telegramId: number)       => api.get(`/api/trades/partners/${telegramId}/cards`)
export const getDust         = ()                         => api.get('/api/dust')
export const dustCards       = (card_ids: string[])       => api.post('/api/dust/dust_cards', { card_ids })
