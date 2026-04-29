const BASE = '/api'

export async function fetchTickers() {
  const r = await fetch(`${BASE}/tickers`)
  if (!r.ok) throw new Error('Failed to fetch tickers')
  return r.json()
}

export async function addTicker(symbol, upThreshold = 0.6, downThreshold = 0.6) {
  const r = await fetch(`${BASE}/tickers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, up_threshold: upThreshold, down_threshold: downThreshold }),
  })
  if (!r.ok) {
    const err = await r.json()
    throw new Error(err.detail || 'Failed to add ticker')
  }
  return r.json()
}

export async function removeTicker(symbol) {
  const r = await fetch(`${BASE}/tickers/${symbol}`, { method: 'DELETE' })
  if (!r.ok) throw new Error('Failed to remove ticker')
  return r.json()
}

export async function fetchLatestSignals() {
  const r = await fetch(`${BASE}/signals`)
  if (!r.ok) throw new Error('Failed to fetch signals')
  return r.json()
}

export async function fetchSignals(symbol, limit = 20) {
  const r = await fetch(`${BASE}/signals/${symbol}?limit=${limit}`)
  if (!r.ok) throw new Error('Failed to fetch signals')
  return r.json()
}

export async function fetchModelStats(symbol) {
  const r = await fetch(`${BASE}/model-stats/${symbol}`)
  if (!r.ok) return null
  return r.json()
}

export async function fetchAllModelStats() {
  const r = await fetch(`${BASE}/model-stats`)
  if (!r.ok) return []
  return r.json()
}

export function createWebSocket(onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws`)
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)) } catch {}
  }
  return ws
}
