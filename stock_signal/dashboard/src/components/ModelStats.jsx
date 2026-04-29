import React from 'react'
import { Brain } from 'lucide-react'

export default function ModelStats({ stats }) {
  if (!stats?.length) return null

  return (
    <div style={{ marginTop: 32 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <Brain size={16} color="#6b7280" />
        <span style={{ fontSize: 13, fontWeight: 600, color: '#9ca3af', letterSpacing: 1 }}>
          MODEL PERFORMANCE
        </span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #2d3148' }}>
              {['Ticker', 'Version', 'Samples', 'Prec UP', 'Prec DOWN', 'F1 UP', 'F1 DOWN', 'Accuracy', 'Trained At'].map(h => (
                <th key={h} style={{ padding: '6px 12px', color: '#6b7280', textAlign: 'left', fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stats.map(s => (
              <tr key={s.symbol} style={{ borderBottom: '1px solid #1a1d27' }}>
                <td style={{ padding: '8px 12px', fontWeight: 700, color: '#f1f5f9' }}>{s.symbol}</td>
                <td style={{ padding: '8px 12px', color: '#6b7280', fontSize: 10 }}>{s.version}</td>
                <td style={{ padding: '8px 12px', color: '#94a3b8' }}>{s.sample_count?.toLocaleString() ?? '--'}</td>
                <td style={{ padding: '8px 12px', color: s.precision_up >= 0.6 ? '#22c55e' : s.precision_up >= 0.45 ? '#f59e0b' : '#ef4444' }}>
                  {s.precision_up != null ? (s.precision_up * 100).toFixed(1) + '%' : '--'}
                </td>
                <td style={{ padding: '8px 12px', color: s.precision_down >= 0.6 ? '#22c55e' : s.precision_down >= 0.45 ? '#f59e0b' : '#ef4444' }}>
                  {s.precision_down != null ? (s.precision_down * 100).toFixed(1) + '%' : '--'}
                </td>
                <td style={{ padding: '8px 12px', color: '#94a3b8' }}>{s.f1_up?.toFixed(3) ?? '--'}</td>
                <td style={{ padding: '8px 12px', color: '#94a3b8' }}>{s.f1_down?.toFixed(3) ?? '--'}</td>
                <td style={{ padding: '8px 12px', color: '#94a3b8' }}>
                  {s.accuracy != null ? (s.accuracy * 100).toFixed(1) + '%' : '--'}
                </td>
                <td style={{ padding: '8px 12px', color: '#6b7280', fontSize: 10 }}>
                  {s.trained_at ? new Date(s.trained_at).toLocaleDateString() : '--'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
