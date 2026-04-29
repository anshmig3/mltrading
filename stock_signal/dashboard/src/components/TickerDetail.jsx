import React, { useEffect, useState } from 'react'
import { X, CheckCircle, XCircle, MinusCircle } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { fetchSignals, fetchModelStats } from '../api'

const SIGNAL_COLOR = { GREEN: '#22c55e', RED: '#ef4444', GRAY: '#6b7280' }
const OUTCOME_ICON = {
  UP:   <CheckCircle size={14} color="#22c55e" />,
  DOWN: <XCircle size={14} color="#ef4444" />,
  NEUTRAL: <MinusCircle size={14} color="#6b7280" />,
}

export default function TickerDetail({ symbol, onClose }) {
  const [signals, setSignals] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!symbol) return
    setLoading(true)
    Promise.all([fetchSignals(symbol, 20), fetchModelStats(symbol)])
      .then(([sigs, st]) => {
        setSignals(sigs)
        setStats(st)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [symbol])

  const probChartData = signals
    .slice()
    .reverse()
    .map(s => ({
      ts: s.candle_ts ? new Date(s.candle_ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
      p_up: s.p_up ? +(s.p_up * 100).toFixed(1) : null,
      p_down: s.p_down ? +(s.p_down * 100).toFixed(1) : null,
      p_neutral: s.p_neutral ? +(s.p_neutral * 100).toFixed(1) : null,
    }))

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 100, padding: 20,
    }} onClick={onClose}>
      <div
        style={{
          background: '#1a1d27', borderRadius: 16, width: '100%', maxWidth: 720,
          maxHeight: '85vh', overflow: 'auto', padding: 24,
          border: '1px solid #2d3148',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 22, fontWeight: 700 }}>{symbol} — Detail</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        {loading ? (
          <div style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>Loading...</div>
        ) : (
          <>
            {stats && (
              <div style={{ background: '#0f1117', borderRadius: 10, padding: 16, marginBottom: 20 }}>
                <div style={{ color: '#9ca3af', fontSize: 12, marginBottom: 10, fontWeight: 600 }}>MODEL STATS</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                  {[
                    ['Version', stats.version],
                    ['Samples', stats.sample_count?.toLocaleString()],
                    ['Precision UP', stats.precision_up != null ? (stats.precision_up * 100).toFixed(1) + '%' : 'N/A'],
                    ['Precision DOWN', stats.precision_down != null ? (stats.precision_down * 100).toFixed(1) + '%' : 'N/A'],
                    ['F1 UP', stats.f1_up != null ? stats.f1_up.toFixed(3) : 'N/A'],
                    ['F1 DOWN', stats.f1_down != null ? stats.f1_down.toFixed(3) : 'N/A'],
                    ['Accuracy', stats.accuracy != null ? (stats.accuracy * 100).toFixed(1) + '%' : 'N/A'],
                    ['Overrides 30d', stats.overrides_30d ?? 'N/A'],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <div style={{ fontSize: 10, color: '#6b7280' }}>{label}</div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#f1f5f9' }}>{value ?? '--'}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {probChartData.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ color: '#9ca3af', fontSize: 12, marginBottom: 10, fontWeight: 600 }}>ML PROBABILITY HISTORY</div>
                <ResponsiveContainer width="100%" height={160}>
                  <LineChart data={probChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
                    <XAxis dataKey="ts" tick={{ fontSize: 9, fill: '#6b7280' }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 9, fill: '#6b7280' }} unit="%" />
                    <Tooltip
                      contentStyle={{ background: '#1e2130', border: 'none', fontSize: 11 }}
                      formatter={v => [`${v}%`, '']}
                    />
                    <Line type="monotone" dataKey="p_up" stroke="#22c55e" dot={false} strokeWidth={1.5} name="P(up)" />
                    <Line type="monotone" dataKey="p_down" stroke="#ef4444" dot={false} strokeWidth={1.5} name="P(down)" />
                    <Line type="monotone" dataKey="p_neutral" stroke="#6b7280" dot={false} strokeWidth={1} name="P(neutral)" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            <div>
              <div style={{ color: '#9ca3af', fontSize: 12, marginBottom: 10, fontWeight: 600 }}>LAST 20 SIGNALS</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {signals.map(s => (
                  <div key={s.id} style={{
                    background: '#0f1117', borderRadius: 8, padding: '10px 14px',
                    display: 'flex', alignItems: 'center', gap: 12,
                    borderLeft: `3px solid ${SIGNAL_COLOR[s.final_signal] || '#4b5563'}`,
                  }}>
                    <span style={{ fontSize: 10, color: '#6b7280', width: 70 }}>
                      {s.candle_ts ? new Date(s.candle_ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--'}
                    </span>
                    <span style={{ color: SIGNAL_COLOR[s.final_signal] || '#9ca3af', fontSize: 12, fontWeight: 700, width: 50 }}>
                      {s.final_signal}
                    </span>
                    {s.ml_overridden ? (
                      <span style={{ fontSize: 10, color: '#f59e0b' }}>overridden</span>
                    ) : null}
                    <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4 }}>
                      {s.outcome_at_4c ? OUTCOME_ICON[s.outcome_at_4c] : <span style={{ color: '#4b5563', fontSize: 10 }}>pending</span>}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
