import { useState, useEffect } from 'react'
import {
  Card,
  Title,
  Text,
  Metric,
  Flex,
  Badge,
  LineChart,
  Grid,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableHeaderCell,
} from '@tremor/react'

interface MetricData {
  cpu: number
  memory: number
  disk: number
  gateway_status: boolean
  timestamp: number
  collected_at?: string
}

interface HistoryData {
  time: string
  cpu: number
  memory: number
  disk: number
}

interface AgentSummary {
  agent_id: string
  agent_name: string | null
  status: string
  latest_memory: number | null
  latest_cpu: number | null
  last_seen: string | null
}

interface AlertOut {
  id: number
  alert_type: string
  severity: string
  title: string
  message: string | null
  is_resolved: boolean
  created_at: string
}

function App() {
  const [realtime, setRealtime] = useState<MetricData | null>(null)
  const [history, setHistory] = useState<HistoryData[]>([])
  const [agents, setAgents] = useState<AgentSummary[]>([])
  const [alerts, setAlerts] = useState<AlertOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 获取实时数据
  const fetchRealtime = async () => {
    try {
      const response = await fetch('/api/v1/metrics/realtime')
      if (!response.ok) throw new Error('获取数据失败')
      const data = await response.json()
      setRealtime(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  // 获取历史数据
  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/v1/metrics/history?hours=24')
      if (!response.ok) throw new Error('获取历史数据失败')
      const data = await response.json()
      setHistory(data)
    } catch (err) {
      console.error('获取历史数据失败:', err)
    }
  }

  // 获取 Agent 列表
  const fetchAgents = async () => {
    try {
      const response = await fetch('/api/v1/agents/list')
      if (!response.ok) throw new Error('获取 Agent 列表失败')
      const data = await response.json()
      setAgents(data)
    } catch (err) {
      console.error('获取 Agent 列表失败:', err)
    }
  }

  // 获取告警列表
  const fetchAlerts = async () => {
    try {
      const response = await fetch('/api/v1/alerts?is_resolved=false&limit=10')
      if (!response.ok) throw new Error('获取告警列表失败')
      const data = await response.json()
      setAlerts(data)
    } catch (err) {
      console.error('获取告警列表失败:', err)
    }
  }

  useEffect(() => {
    // 初始加载
    fetchRealtime()
    fetchHistory()
    fetchAgents()
    fetchAlerts()

    // 每5秒刷新
    const interval = setInterval(() => {
      fetchRealtime()
      fetchAgents()
      fetchAlerts()
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Text>加载中...</Text>
      </div>
    )
  }

  if (error && !realtime) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="max-w-md">
          <Title>错误</Title>
          <Text>{error}</Text>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 标题 */}
        <div className="mb-8">
          <Title>OC-Monitor v3.0</Title>
          <Text>轻量级、高性能的 OpenClaw 监控系统</Text>
        </div>

        {/* 实时数据卡片 */}
        <Grid numItemsSm={2} numItemsLg={4} className="gap-6 mb-8">
          {/* CPU */}
          <Card>
            <Flex justifyContent="between" alignItems="center">
              <Text>CPU</Text>
              <Badge color={realtime && realtime.cpu > 80 ? 'red' : realtime && realtime.cpu > 60 ? 'yellow' : 'green'}>
                {realtime ? `${realtime.cpu.toFixed(1)}%` : '-'}
              </Badge>
            </Flex>
            <Metric>{realtime ? `${realtime.cpu.toFixed(1)}%` : '-'}</Metric>
          </Card>

          {/* 内存 */}
          <Card>
            <Flex justifyContent="between" alignItems="center">
              <Text>内存</Text>
              <Badge color={realtime && realtime.memory > 80 ? 'red' : realtime && realtime.memory > 60 ? 'yellow' : 'green'}>
                {realtime && realtime.memory > 80 ? '高' : realtime && realtime.memory > 60 ? '中' : '低'}
              </Badge>
            </Flex>
            <Metric>{realtime ? `${realtime.memory.toFixed(1)}%` : '-'}</Metric>
          </Card>

          {/* 磁盘 */}
          <Card>
            <Flex justifyContent="between" alignItems="center">
              <Text>磁盘</Text>
              <Badge color={realtime && realtime.disk > 80 ? 'red' : realtime && realtime.disk > 60 ? 'yellow' : 'green'}>
                {realtime && realtime.disk > 80 ? '高' : realtime && realtime.disk > 60 ? '中' : '低'}
              </Badge>
            </Flex>
            <Metric>{realtime ? `${realtime.disk.toFixed(1)}%` : '-'}</Metric>
          </Card>

          {/* Gateway 状态 */}
          <Card>
            <Flex justifyContent="between" alignItems="center">
              <Text>Gateway</Text>
              <Badge color={realtime && realtime.gateway_status ? 'green' : 'red'}>
                {realtime && realtime.gateway_status ? '运行中' : '已停止'}
              </Badge>
            </Flex>
            <Metric>{realtime && realtime.gateway_status ? '✓' : '✗'}</Metric>
          </Card>
        </Grid>

        {/* 历史趋势图 */}
        <Card className="mb-6">
          <Title>24小时趋势</Title>
          <LineChart
            className="h-72 mt-4"
            data={history}
            index="time"
            categories={['cpu', 'memory', 'disk']}
            colors={['blue', 'green', 'purple']}
            valueFormatter={(value) => `${value.toFixed(1)}%`}
            yAxisWidth={48}
          />
        </Card>

        {/* Agent 列表 */}
        <Card className="mb-6">
          <Title>Agent 状态</Title>
          <Table className="mt-4">
            <TableHead>
              <TableRow>
                <TableHeaderCell>Agent ID</TableHeaderCell>
                <TableHeaderCell>名称</TableHeaderCell>
                <TableHeaderCell>状态</TableHeaderCell>
                <TableHeaderCell>内存</TableHeaderCell>
                <TableHeaderCell>CPU</TableHeaderCell>
                <TableHeaderCell>最后更新</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {agents.map((agent) => (
                <TableRow key={agent.agent_id}>
                  <TableCell>{agent.agent_id}</TableCell>
                  <TableCell>{agent.agent_name || '-'}</TableCell>
                  <TableCell>
                    <Badge color={agent.status === 'online' ? 'green' : 'red'}>
                      {agent.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{agent.latest_memory ? `${agent.latest_memory.toFixed(1)} MB` : '-'}</TableCell>
                  <TableCell>{agent.latest_cpu ? `${agent.latest_cpu.toFixed(1)}%` : '-'}</TableCell>
                  <TableCell>{agent.last_seen ? new Date(agent.last_seen).toLocaleString() : '-'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>

        {/* 告警列表 */}
        <Card>
          <Title>活跃告警</Title>
          {alerts.length === 0 ? (
            <Text className="mt-4">暂无活跃告警</Text>
          ) : (
            <Table className="mt-4">
              <TableHead>
                <TableRow>
                  <TableHeaderCell>类型</TableHeaderCell>
                  <TableHeaderCell>严重程度</TableHeaderCell>
                  <TableHeaderCell>标题</TableHeaderCell>
                  <TableHeaderCell>时间</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {alerts.map((alert) => (
                  <TableRow key={alert.id}>
                    <TableCell>{alert.alert_type}</TableCell>
                    <TableCell>
                      <Badge 
                        color={alert.severity === 'critical' ? 'red' : alert.severity === 'warning' ? 'yellow' : 'blue'}
                      >
                        {alert.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>{alert.title}</TableCell>
                    <TableCell>{new Date(alert.created_at).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>

        {/* 错误提示 */}
        {error && (
          <Card className="mt-6">
            <Text color="red">{error}</Text>
          </Card>
        )}
      </div>
    </div>
  )
}

export default App
