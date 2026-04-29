import React, { useState, useEffect, useRef } from 'react'
import { TrendingUp, TrendingDown, Minus, AlertTriangle, X } from 'lucide-react'
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'

const SIGNAL_CONFIG = {
  GREEN:  { bg: '#0d2818', border: '#22c55e', text: '#22c55e', Icon: TrendingUp,  label: 'BUY' },
  RED:    { bg: '#2a0f0f', border: '#ef4444', text: '#ef4444', Icon: TrendingDown, label: 'SELL' },
  GRAY:   { bg: '#1a1d27', border: '#4b5563', text: '#9ca3af', Icon: Minus,       label: 'HOLD' },
}

const FLAG_COLORS = {
  NLP_UNAVAILABLE:   '#f59e0b',
  OPENING_VOLATILITY:'#f97316',
  HIGH_VOLATILITY:   '#ef4444',
  HIGH_STREAK:       '#a855f7',
  LOW_PRECISION:     '#f59e0b',
  NEAR_52W_HIGH:     '#3b82f6',
  NEAR_52W_LOW:      '#06b6d4',
}

export default function SignalCard({ signal, sparklineData, onRemove, onClick, marketClosed }) {
  const [flash, setFlash] = useState(false)
  const prevSignal = useRef(signal?.final_signal)

  useEffect(() => {
    if (signal && prevSignal.current && signal.final_signal !== prevSignal.current) {
      setFlash(true)
      setTimeout(() => setFlash(false), 800)
    }
    prevSignal.current = signal?.final_signal
  }, [signal?.final_signal])

  if (!signal) return null

  const cfg = SIGNAL_CONFIG[signal.final_signal] || SIGNAL_CONFIG.GRAY
  const { Icon } = cfg
  const flags = Array.isArray(signal.flags) ? signal.flags : []
  const ts = signal.candle_ts
    ? new Date(signal.candle_ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '--'

  return (
    <div
      onClick={onClick}
      style={{
        background: flash ? cfg.border + '22' : cfg.bg,
        border: `1px solid ${cfg.border}`,
        borderRadius: 12,
        padding: '16px',
        cursor: 'pointer',
        transition: 'background 0.3s, transform 0.1s',
        position: 'relative',
        userSelect: 'none',
      }}
      onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
      onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
    >
      {marketClosed && (
        <div style={{
          position: 'absolute', inset: 0, borderRadius: 12,
          background: 'rgba(0,0,0,0.55)', display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          zIndex: 2, flexDirection: 'column', gap: 4,
        }}>
          <span style={{ color: '#9ca3af', fontSize: 11, fontWeight: 600, letterSpacing: 1 }}>MARKET CLOSED</span>
          <span style={{ color: '#6b7280', fontSize: 10 }}>Last: {ts}</span>
        </div>
      )}

      <button
        onClick={e => { e.stopPropagation(); onRemove(signal.symbol) }}
        style={{
          position: 'absolute', top: 8, right: 8, background: 'none',
          border: 'none', color: '#6b7280', cursor: 'pointer', padding: 2,
        }}
      >
        <X size={14} />
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <Icon size={20} color={cfg.text} />
        <span style={{ fontSize: 18, fontWeight: 700, color: '#f1f5f9' }}>{signal.symbol}</span>
        <span style={{
          marginLeft: 'auto', background: cfg.border + '33',
          color: cfg.text, borderRadius: 6, padding: '2px 8px',
          fontSize: 11, fontWeight: 700, letterSpacing: 1,
        }}>{cfg.label}</span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <div>
          <div style={{ color: '#9ca3af', fontSize: 11 }}>Price</div>
          <div style={{ fontSize: 20, fontWeight: 600, color: '#f1f5f9' }}>
            ${signal.close_price?.toFixed(2) ?? '--'}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ color: '#9ca3af', fontSize: 11 }}>Confidence</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: cfg.text }}>
            {signal.confidence != null ? (signal.confidence * 100).toFixed(0) + '%' : '--'}
          </div>
        </div>
      </div>

      {sparklineData?.length > 1 && (
        <div style={{ height: 48, marginBottom: 8 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparklineData}>
              <Line
                type="monotone" dataKey="close" dot={false}
                stroke={cfg.text} strokeWidth={1.5}
              />
              <Tooltip
                contentStyle={{ background: '#1e2130', border: 'none', fontSize: 11 }}
                formatter={v => [`$${v.toFixed(2)}`, '']}
                labelFormatter={() => ''}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {signal.rationale && (
        <p style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.5, marginBottom: 8 }}>
          {signal.rationale}
        </p>
      )}

      {flags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {flags.map(f => (
            <span key={f} style={{
              background: (FLAG_COLORS[f] || '#6b7280') + '22',
              color: FLAG_COLORS[f] || '#9ca3af',
              borderRadius: 4, padding: '1px 6px', fontSize: 10, fontWeight: 600,
            }}>{f}</span>
          ))}
        </div>
      )}

      <div style={{ marginTop: 8, fontSize: 10, color: '#4b5563' }}>{ts}</div>
    </div>
  )
}
