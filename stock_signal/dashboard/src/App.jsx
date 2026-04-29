import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Activity, Wifi, WifiOff, RefreshCw } from 'lucide-react'
import SignalCard from './components/SignalCard'
import TickerDetail from './components/TickerDetail'
import AddTicker from './components/AddTicker'
import ModelStats from './components/ModelStats'
import {
  createWebSocket, fetchLatestSignals, fetchTickers,
  fetchAllModelStats, removeTicker,
} from './api'

function isMarketOpen() {
  const now = new Date()
  const day = now.getDay()
  if (day === 0 || day === 6) return false
  const h = now.getHours(), m = now.getMinutes()
  const mins = h * 60 + m
  return mins >= 9 * 60 + 30 && mins < 16 * 60
}

export default function App() {
  const [signals, setSignals] = useState({})
  const [sparklines, setSparklines] = useState({})
  const [tickers, setTickers] = useState([])
  const [modelStats, setModelStats] = useState([])
  const [selectedSymbol, setSelectedSymbol] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [marketClosed, setMarketClosed] = useState(!isMarketOpen())
  const [lastUpdate, setLastUpdate] = useState(null)
  const wsRef = useRef(null)

  const loadInitial = useCallback(async () => {
    try {
      const [latestSignals, tickerList, stats] = await Promise.all([
        fetchLatestSignals(),
        fetchTickers(),
        fetchAllModelStats(),
      ])
      const sigMap = {}
      const sparkMap = {}
      for (const s of latestSignals) {
        sigMap[s.symbol] = s
        sparkMap[s.symbol] = sparkMap[s.symbol] || []
        sparkMap[s.symbol].push({ close: s.close_price })
      }
      setSignals(sigMap)
      setSparklines(sparkMap)
      setTickers(tickerList.map(t => t.symbol))
      setModelStats(stats)
    } catch (e) {
      console.error('Failed to load initial data', e)
    }
  }, [])

  useEffect(() => {
    loadInitial()
  }, [loadInitial])

  useEffect(() => {
    const interval = setInterval(() => setMarketClosed(!isMarketOpen()), 60000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    function connect() {
      const ws = createWebSocket((msg) => {
        if (msg.type === 'signal') {
          const s = msg.data
          setSignals(prev => ({ ...prev, [s.symbol]: s }))
          setSparklines(prev => {
            const arr = [...(prev[s.symbol] || []), { close: s.close_price }]
            return { ...prev, [s.symbol]: arr.slice(-20) }
          })
          setLastUpdate(new Date().toLocaleTimeString())
        }
      })
      ws.onopen = () => setWsConnected(true)
      ws.onclose = () => {
        setWsConnected(false)
        setTimeout(connect, 3000)
      }
      ws.onerror = () => ws.close()
      wsRef.current = ws
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  const handleTickerAdded = (symbol) => {
    setTickers(prev => prev.includes(symbol) ? prev : [...prev, symbol])
    setSignals(prev => ({
      ...prev,
      [symbol]: prev[symbol] || {
        symbol, final_signal: 'GRAY', confidence: null,
        rationale: 'Awaiting first signal…', flags: [], close_price: null,
      },
    }))
  }

  const handleRemove = async (symbol) => {
    try {
      await removeTicker(symbol)
      setTickers(prev => prev.filter(s => s !== symbol))
      setSignals(prev => { const n = { ...prev }; delete n[symbol]; return n })
      setSparklines(prev => { const n = { ...prev }; delete n[symbol]; return n })
      if (selectedSymbol === symbol) setSelectedSymbol(null)
    } catch (e) {
      console.error('Remove failed', e)
    }
  }

  const allTickers = [
    ...tickers,
    ...Object.keys(signals).filter(s => !tickers.includes(s)),
  ]

  return (
    <div style={{ minHeight: '100vh', background: '#0f1117' }}>
      {/* Header */}
      <header style={{
        background: '#141720', borderBottom: '1px solid #1e2335',
        padding: '14px 24px', display: 'flex', alignItems: 'center', gap: 12,
        position: 'sticky', top: 0, zIndex: 50,
      }}>
        <Activity size={20} color="#3b82f6" />
        <span style={{ fontSize: 17, fontWeight: 700, color: '#f1f5f9' }}>
          Stock Signal Dashboard
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }}>
          {lastUpdate && (
            <span style={{ fontSize: 11, color: '#4b5563' }}>
              Last update: {lastUpdate}
            </span>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {wsConnected
              ? <Wifi size={14} color="#22c55e" />
              : <WifiOff size={14} color="#ef4444" />}
            <span style={{ fontSize: 11, color: wsConnected ? '#22c55e' : '#ef4444' }}>
              {wsConnected ? 'Live' : 'Reconnecting'}
            </span>
          </div>
          <div style={{
            fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: 6,
            background: marketClosed ? '#1f2937' : '#0d2818',
            color: marketClosed ? '#6b7280' : '#22c55e',
          }}>
            {marketClosed ? 'MARKET CLOSED' : 'MARKET OPEN'}
          </div>
          <button
            onClick={loadInitial}
            style={{
              background: 'none', border: '1px solid #2d3148', borderRadius: 6,
              padding: '4px 8px', color: '#9ca3af', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 4, fontSize: 12,
            }}
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </header>

      {/* Controls */}
      <div style={{ padding: '20px 24px 0', display: 'flex', alignItems: 'center', gap: 16 }}>
        <AddTicker onAdded={handleTickerAdded} />
        <span style={{ fontSize: 12, color: '#4b5563' }}>
          {allTickers.length} ticker{allTickers.length !== 1 ? 's' : ''} active
        </span>
      </div>

      {/* Signal Grid */}
      <main style={{ padding: 24 }}>
        {allTickers.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: '80px 24px', color: '#4b5563',
          }}>
            <Activity size={48} style={{ margin: '0 auto 16px', opacity: 0.3 }} />
            <div style={{ fontSize: 16, marginBottom: 8 }}>No tickers yet</div>
            <div style={{ fontSize: 13 }}>Add a ticker above to start monitoring signals.</div>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: 16,
          }}>
            {allTickers.map(symbol => (
              <SignalCard
                key={symbol}
                signal={signals[symbol] || { symbol, final_signal: 'GRAY', flags: [] }}
                sparklineData={sparklines[symbol] || []}
                onRemove={handleRemove}
                onClick={() => setSelectedSymbol(symbol)}
                marketClosed={marketClosed}
              />
            ))}
          </div>
        )}

        <ModelStats stats={modelStats} />
      </main>

      {/* Detail Panel */}
      {selectedSymbol && (
        <TickerDetail
          symbol={selectedSymbol}
          onClose={() => setSelectedSymbol(null)}
        />
      )}
    </div>
  )
}
