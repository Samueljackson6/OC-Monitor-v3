import { useEffect, useMemo, useState } from 'react'
import './index.css'

type MetricData = {
  cpu: number
  memory: number
  disk: number
  gateway_status: boolean
  timestamp: number
  collected_at?: string
}

type HistoryData = {
  time: string
  cpu: number
  memory: number
  disk: number
}

type AgentSummary = {
  agent_id: string
  agent_name: string | null
  status: string
  latest_memory: number | null
  latest_cpu: number | null
  last_seen: string | null
}

type AlertOut = {
  id: number
  alert_type: string
  severity: string
  title: string
  message: string | null
  is_resolved: boolean
  created_at: string
}

type RuntimeInfo = {
  app_name: string
  app_version: string
  environment: string
  auth_required: boolean
  ingest_token_configured: boolean
  updated_at: string
}

type LoadState = 'loading' | 'ready' | 'error'

const endpoints = {
  realtime: '/api/v1/metrics/realtime',
  history: '/api/v1/metrics/history?hours=24',
  agents: '/api/v1/agents/list',
  alerts: '/api/v1/alerts?is_resolved=false&limit=10',
  stats: '/api/v1/config/stats',
  runtime: '/api/v1/config/runtime',
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return `${value.toFixed(1)}%`
}

function formatNumber(value: number | null | undefined, suffix = '') {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return `${value.toFixed(1)}${suffix}`
}

function formatTime(value?: string | number | null) {
  if (!value) return '-'
  const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function metricTone(value: number | null | undefined, warning = 60, danger = 80) {
  if (value === null || value === undefined) return 'muted'
  if (value >= danger) return 'danger'
  if (value >= warning) return 'warning'
  return 'ok'
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`${url} ${response.status}`)
  return response.json()
}

function StatusPill({ tone, children }: { tone: string; children: React.ReactNode }) {
  return <span className={`status-pill status-${tone}`}>{children}</span>
}

function SummaryCard({
  label,
  value,
  subLabel,
  tone,
  progress,
}: {
  label: string
  value: string
  subLabel: string
  tone: string
  progress?: number
}) {
  const width = Math.max(0, Math.min(progress ?? 0, 100))
  return (
    <section className="summary-card">
      <div className="summary-topline">
        <span>{label}</span>
        <StatusPill tone={tone}>{subLabel}</StatusPill>
      </div>
      <strong>{value}</strong>
      {progress !== undefined && (
        <div className="meter" aria-hidden="true">
          <span className={`meter-fill meter-${tone}`} style={{ width: `${width}%` }} />
        </div>
      )}
    </section>
  )
}

function TrendChart({ data }: { data: HistoryData[] }) {
  const chartData = useMemo(() => data.slice(-96), [data])
  const width = 920
  const height = 300
  const padding = { left: 46, right: 20, top: 24, bottom: 44 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom

  const toPoint = (item: HistoryData, index: number, key: keyof Pick<HistoryData, 'cpu' | 'memory' | 'disk'>) => {
    const x = padding.left + (chartData.length <= 1 ? 0 : (index / (chartData.length - 1)) * plotWidth)
    const y = padding.top + (1 - Math.max(0, Math.min(item[key], 100)) / 100) * plotHeight
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }

  const makePoints = (key: keyof Pick<HistoryData, 'cpu' | 'memory' | 'disk'>) =>
    chartData.map((item, index) => toPoint(item, index, key)).join(' ')

  const axis = [0, 25, 50, 75, 100]
  const labels = chartData.filter((_, index) => index === 0 || index === Math.floor(chartData.length / 2) || index === chartData.length - 1)

  if (chartData.length === 0) {
    return <div className="empty-chart">暂无趋势数据</div>
  }

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="24 小时指标趋势">
        {axis.map((tick) => {
          const y = padding.top + (1 - tick / 100) * plotHeight
          return (
            <g key={tick}>
              <line className="chart-grid" x1={padding.left} y1={y} x2={width - padding.right} y2={y} />
              <text className="chart-label" x={padding.left - 12} y={y + 4} textAnchor="end">
                {tick}%
              </text>
            </g>
          )
        })}
        <polyline className="trend-line trend-cpu" points={makePoints('cpu')} />
        <polyline className="trend-line trend-memory" points={makePoints('memory')} />
        <polyline className="trend-line trend-disk" points={makePoints('disk')} />
        {labels.map((item, index) => {
          const sourceIndex = chartData.indexOf(item)
          const x = padding.left + (chartData.length <= 1 ? 0 : (sourceIndex / (chartData.length - 1)) * plotWidth)
          return (
            <text key={`${item.time}-${index}`} className="chart-label chart-time" x={x} y={height - 14} textAnchor={index === 0 ? 'start' : index === labels.length - 1 ? 'end' : 'middle'}>
              {item.time.slice(5)}
            </text>
          )
        })}
      </svg>
      <div className="legend-row">
        <span><i className="legend-dot cpu" />CPU</span>
        <span><i className="legend-dot memory" />内存</span>
        <span><i className="legend-dot disk" />磁盘</span>
      </div>
    </div>
  )
}

function AgentTable({ agents }: { agents: AgentSummary[] }) {
  if (agents.length === 0) {
    return <div className="empty-state">暂无 Agent 上报</div>
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Agent</th>
            <th>名称</th>
            <th>状态</th>
            <th>内存</th>
            <th>CPU</th>
            <th>最近上报</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((agent) => (
            <tr key={agent.agent_id}>
              <td className="mono">{agent.agent_id}</td>
              <td>{agent.agent_name || '-'}</td>
              <td>
                <StatusPill tone={agent.status === 'online' ? 'ok' : 'danger'}>{agent.status || 'unknown'}</StatusPill>
              </td>
              <td>{formatNumber(agent.latest_memory, ' MB')}</td>
              <td>{formatPercent(agent.latest_cpu)}</td>
              <td>{formatTime(agent.last_seen)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AlertList({ alerts }: { alerts: AlertOut[] }) {
  if (alerts.length === 0) return <div className="empty-state">暂无活跃告警</div>

  return (
    <div className="alert-list">
      {alerts.map((alert) => (
        <article className="alert-row" key={alert.id}>
          <div>
            <strong>{alert.title}</strong>
            <span>{alert.message || alert.alert_type}</span>
          </div>
          <StatusPill tone={alert.severity === 'critical' ? 'danger' : alert.severity === 'warning' ? 'warning' : 'info'}>
            {alert.severity}
          </StatusPill>
          <time>{formatTime(alert.created_at)}</time>
        </article>
      ))}
    </div>
  )
}

function ConfigStrip({ runtime, stats }: { runtime: RuntimeInfo | null; stats: Record<string, number | string> | null }) {
  return (
    <section className="config-strip">
      <div>
        <span>运行环境</span>
        <strong>{runtime?.environment || '-'}</strong>
      </div>
      <div>
        <span>管理认证</span>
        <strong>{runtime?.auth_required ? '已启用' : '未启用'}</strong>
      </div>
      <div>
        <span>采集令牌</span>
        <strong>{runtime?.ingest_token_configured ? '已配置' : '未配置'}</strong>
      </div>
      <div>
        <span>指标总量</span>
        <strong>{stats?.total_metrics ?? '-'}</strong>
      </div>
      <div>
        <span>告警总量</span>
        <strong>{stats?.total_alerts ?? '-'}</strong>
      </div>
    </section>
  )
}

function App() {
  const [realtime, setRealtime] = useState<MetricData | null>(null)
  const [history, setHistory] = useState<HistoryData[]>([])
  const [agents, setAgents] = useState<AgentSummary[]>([])
  const [alerts, setAlerts] = useState<AlertOut[]>([])
  const [runtime, setRuntime] = useState<RuntimeInfo | null>(null)
  const [stats, setStats] = useState<Record<string, number | string> | null>(null)
  const [state, setState] = useState<LoadState>('loading')
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const refresh = async () => {
    try {
      const [metricData, historyData, agentData, alertData, runtimeData, statsData] = await Promise.all([
        fetchJson<MetricData>(endpoints.realtime),
        fetchJson<HistoryData[]>(endpoints.history),
        fetchJson<AgentSummary[]>(endpoints.agents),
        fetchJson<AlertOut[]>(endpoints.alerts),
        fetchJson<RuntimeInfo>(endpoints.runtime),
        fetchJson<Record<string, number | string>>(endpoints.stats),
      ])
      setRealtime(metricData)
      setHistory(historyData)
      setAgents(agentData)
      setAlerts(alertData)
      setRuntime(runtimeData)
      setStats(statsData)
      setLastRefresh(new Date())
      setError(null)
      setState('ready')
    } catch (err) {
      setError(err instanceof Error ? err.message : '数据加载失败')
      setState((current) => (current === 'loading' ? 'error' : current))
    }
  }

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 15000)
    return () => window.clearInterval(timer)
  }, [])

  const gatewayTone = realtime?.gateway_status ? 'ok' : 'danger'
  const healthText = error ? '数据异常' : realtime?.gateway_status ? '运行中' : '需关注'

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-mark">OC</span>
          <div>
            <strong>OC-Monitor</strong>
            <span>OpenClaw 控制台</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="运行概览">
          <a href="#overview">运行概览</a>
          <a href="#agents">Agent 监控</a>
          <a href="#alerts">告警</a>
          <a href="#runtime">配置状态</a>
        </nav>
        <div className="sidebar-note">
          <span>公网入口</span>
          <strong>{runtime?.app_version || '3.0.0'}</strong>
        </div>
      </aside>

      <section className="content-shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">OpenClaw Operations</p>
            <h1>监控与运行控制台</h1>
            <span className="subline">最后刷新：{lastRefresh ? formatTime(lastRefresh.toISOString()) : '-'}</span>
          </div>
          <div className="topbar-actions">
            <StatusPill tone={error ? 'danger' : gatewayTone}>{healthText}</StatusPill>
            <button type="button" onClick={refresh}>刷新</button>
          </div>
        </header>

        {state === 'error' && (
          <section className="notice-panel">
            <strong>无法加载监控数据</strong>
            <span>{error}</span>
          </section>
        )}

        <section id="overview" className="summary-grid" aria-label="运行概览">
          <SummaryCard label="CPU" value={formatPercent(realtime?.cpu)} subLabel={metricTone(realtime?.cpu) === 'ok' ? '正常' : metricTone(realtime?.cpu) === 'warning' ? '偏高' : '高负载'} tone={metricTone(realtime?.cpu)} progress={realtime?.cpu} />
          <SummaryCard label="内存" value={formatPercent(realtime?.memory)} subLabel={metricTone(realtime?.memory) === 'ok' ? '正常' : metricTone(realtime?.memory) === 'warning' ? '偏高' : '高占用'} tone={metricTone(realtime?.memory)} progress={realtime?.memory} />
          <SummaryCard label="磁盘" value={formatPercent(realtime?.disk)} subLabel={metricTone(realtime?.disk, 70, 90) === 'ok' ? '正常' : metricTone(realtime?.disk, 70, 90) === 'warning' ? '关注' : '紧张'} tone={metricTone(realtime?.disk, 70, 90)} progress={realtime?.disk} />
          <SummaryCard label="Gateway" value={realtime?.gateway_status ? '在线' : '离线'} subLabel={realtime?.gateway_status ? '可用' : '异常'} tone={gatewayTone} progress={realtime?.gateway_status ? 100 : 0} />
        </section>

        <section className="panel trend-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Metrics</p>
              <h2>24 小时趋势</h2>
            </div>
            <span>{history.length} 个采样点</span>
          </div>
          <TrendChart data={history} />
        </section>

        <section className="main-grid">
          <section id="agents" className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Agents</p>
                <h2>Agent 状态</h2>
              </div>
              <span>{agents.length} 个 Agent</span>
            </div>
            <AgentTable agents={agents} />
          </section>

          <section id="alerts" className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Alerts</p>
                <h2>活跃告警</h2>
              </div>
              <span>{alerts.length} 条</span>
            </div>
            <AlertList alerts={alerts} />
          </section>
        </section>

        <section id="runtime" className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Runtime</p>
              <h2>配置与接入状态</h2>
            </div>
            <span>{runtime?.app_name || 'OC-Monitor'}</span>
          </div>
          <ConfigStrip runtime={runtime} stats={stats} />
        </section>
      </section>
    </main>
  )
}

export default App
