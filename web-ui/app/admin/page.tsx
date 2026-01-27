'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'
import { getApiUrl } from '@/lib/env'
import { createAuthHeaders } from '@/lib/api-client'

export const dynamic = 'force-dynamic'

export default function AdminDashboard() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'cache' | 'system' | 'moderation' | 'billing' | 'model-preferences'>('overview')

  // Redirect if not admin
  useEffect(() => {
    if (!authLoading && (!user || !user.is_admin)) {
      router.push('/')
    }
  }, [user, authLoading, router])

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
      </div>
    )
  }

  if (!user || !user.is_admin) {
    return null // Will redirect
  }

  return (
    <main className="min-h-screen flex flex-col bg-dark-bg">
      <Navbar selectedFeature="blog" onFeatureSelect={() => {}} />
      <div className="flex-1 container mx-auto px-4 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gradient mb-2">Admin Dashboard</h1>
          <p className="text-gray-200">Manage users, system, cache, and moderation</p>
        </div>

        {/* Tabs */}
        <div className="flex space-x-4 mb-6 border-b border-dark-border overflow-x-auto">
          {(['overview', 'users', 'cache', 'system', 'moderation', 'billing', 'model-preferences'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 font-semibold transition-colors whitespace-nowrap ${
                activeTab === tab
                  ? 'text-neon-cyan border-b-2 border-neon-cyan'
                  : 'text-gray-300 hover:text-gray-100'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1).replace('-', ' ')}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="glass-effect neon-border rounded-lg p-6">
          {activeTab === 'overview' && <OverviewTab />}
          {activeTab === 'users' && <UsersTab />}
          {activeTab === 'cache' && <CacheTab />}
          {activeTab === 'system' && <SystemTab />}
          {activeTab === 'moderation' && <ModerationTab />}
          {activeTab === 'billing' && <BillingTab />}
          {activeTab === 'model-preferences' && <ModelPreferencesTab />}
        </div>
      </div>
      <Footer />
    </main>
  )
}

// Overview Tab Component
function OverviewTab() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch overview stats
    Promise.all([
      fetch(getApiUrl('v1/admin/users/admins'), { headers: createAuthHeaders(), credentials: 'include' }).then(r => r.json()).catch(() => ({ count: 0, admins: [] })),
      fetch(getApiUrl('v1/admin/cache/stats'), { headers: createAuthHeaders(), credentials: 'include' }).then(r => r.json()).catch(() => ({ stats: {} })),
      fetch(getApiUrl('health'), { headers: createAuthHeaders(), credentials: 'include' }).then(r => r.json()).catch(() => ({ status: 'unknown' })),
    ])
      .then(([admins, cache, health]) => {
        setStats({ admins, cache, health })
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="text-center py-8 text-gray-300">Loading overview...</div>
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="glass-effect neon-border rounded-lg p-6">
        <h3 className="text-xl font-bold mb-2 text-gradient">Admin Users</h3>
        <p className="text-3xl font-bold text-neon-cyan">{stats?.admins?.count || 0}</p>
        <p className="text-sm text-gray-300 mt-2">Total administrators</p>
      </div>
      <div className="glass-effect neon-border rounded-lg p-6">
        <h3 className="text-xl font-bold mb-2 text-gradient">System Status</h3>
        <p className={`text-2xl font-bold ${stats?.health?.status === 'healthy' ? 'text-green-400' : 'text-red-400'}`}>
          {stats?.health?.status || 'Unknown'}
        </p>
        <p className="text-sm text-gray-300 mt-2">Overall system health</p>
      </div>
      <div className="glass-effect neon-border rounded-lg p-6">
        <h3 className="text-xl font-bold mb-2 text-gradient">Cache Stats</h3>
        <p className="text-sm text-gray-300">Check Cache tab for details</p>
        <p className="text-xs text-gray-400 mt-2">View detailed cache statistics</p>
      </div>
    </div>
  )
}

// Users Tab Component
function UsersTab() {
  const [admins, setAdmins] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    loadAdmins()
  }, [])

  const loadAdmins = async () => {
    try {
      const response = await fetch(getApiUrl('v1/admin/users/admins'), {
        headers: createAuthHeaders(),
        credentials: 'include',
      })
      if (response.ok) {
        const data = await response.json()
        setAdmins(data.admins || [])
      }
    } catch (err) {
      console.error('Failed to load admins:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleMakeAdmin = async (userId: number) => {
    setActionLoading(true)
    setMessage(null)
    try {
      const response = await fetch(getApiUrl(`v1/admin/users/${userId}/make-admin`), {
        method: 'POST',
        headers: createAuthHeaders(),
        credentials: 'include',
      })
      const data = await response.json()
      if (response.ok) {
        setMessage({ type: 'success', text: data.message })
        loadAdmins()
        setSelectedUserId(null)
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to make user admin' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to make user admin' })
    } finally {
      setActionLoading(false)
    }
  }

  const handleRemoveAdmin = async (userId: number) => {
    setActionLoading(true)
    setMessage(null)
    try {
      const response = await fetch(getApiUrl(`v1/admin/users/${userId}/remove-admin`), {
        method: 'POST',
        headers: createAuthHeaders(),
        credentials: 'include',
      })
      const data = await response.json()
      if (response.ok) {
        setMessage({ type: 'success', text: data.message })
        loadAdmins()
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to remove admin status' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to remove admin status' })
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-8 text-gray-300">Loading admin users...</div>
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4 text-gradient">Admin User Management</h2>
      
      {message && (
        <div className={`mb-4 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`}>
          {message.text}
        </div>
      )}

      <div className="mb-6 glass-effect neon-border rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-3 text-white">Make User Admin</h3>
        <div className="flex gap-2">
          <input
            type="number"
            placeholder="User ID"
            value={selectedUserId || ''}
            onChange={(e) => setSelectedUserId(e.target.value ? parseInt(e.target.value) : null)}
            className="flex-1 px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-white"
          />
          <button
            onClick={() => selectedUserId && handleMakeAdmin(selectedUserId)}
            disabled={!selectedUserId || actionLoading}
            className="px-6 py-2 bg-neon-cyan text-dark-bg rounded-lg font-semibold hover:bg-neon-cyan/80 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {actionLoading ? 'Processing...' : 'Make Admin'}
          </button>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-3 text-white">Current Admin Users ({admins.length})</h3>
        <div className="space-y-2">
          {admins.length === 0 ? (
            <div className="text-center py-8 text-gray-400">No admin users found</div>
          ) : (
            admins.map((admin) => (
              <div key={admin.id} className="glass-effect neon-border rounded-lg p-4 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-white">{admin.email}</p>
                  {admin.full_name && <p className="text-sm text-gray-300">{admin.full_name}</p>}
                  <p className="text-xs text-gray-400">ID: {admin.id} | Created: {admin.created_at ? new Date(admin.created_at).toLocaleDateString() : 'N/A'}</p>
                </div>
                <button
                  onClick={() => handleRemoveAdmin(admin.id)}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Remove Admin
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

// Cache Tab Component
function CacheTab() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [userIdsInput, setUserIdsInput] = useState('')
  const [topicsInput, setTopicsInput] = useState('')

  useEffect(() => {
    loadCacheStats()
  }, [])

  const loadCacheStats = async () => {
    try {
      const response = await fetch(getApiUrl('v1/admin/cache/stats'), {
        headers: createAuthHeaders(),
        credentials: 'include',
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data.stats || {})
      }
    } catch (err) {
      console.error('Failed to load cache stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleInvalidateUsers = async () => {
    setActionLoading(true)
    setMessage(null)
    try {
      const ids = userIdsInput.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id))
      if (ids.length === 0) {
        setMessage({ type: 'error', text: 'Please enter at least one valid user ID' })
        setActionLoading(false)
        return
      }
      const response = await fetch(getApiUrl('v1/admin/cache/invalidate/users'), {
        method: 'POST',
        headers: createAuthHeaders({ 'Content-Type': 'application/json' }),
        credentials: 'include',
        body: JSON.stringify({ user_ids: ids }),
      })
      const data = await response.json()
      if (response.ok) {
        setMessage({ type: 'success', text: `Invalidated ${data.invalidated_count} user caches` })
        setUserIdsInput('')
        loadCacheStats()
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to invalidate caches' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to invalidate caches' })
    } finally {
      setActionLoading(false)
    }
  }

  const handleInvalidateContent = async (clearAll: boolean) => {
    setActionLoading(true)
    setMessage(null)
    try {
      const response = await fetch(getApiUrl('v1/admin/cache/invalidate/content'), {
        method: 'POST',
        headers: createAuthHeaders({ 'Content-Type': 'application/json' }),
        credentials: 'include',
        body: JSON.stringify({
          clear_all: clearAll,
          topics: clearAll ? undefined : topicsInput.split(',').map(t => t.trim()).filter(t => t.length > 0),
        }),
      })
      const data = await response.json()
      if (response.ok) {
        setMessage({ type: 'success', text: data.message || 'Cache invalidated successfully' })
        setTopicsInput('')
        loadCacheStats()
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to invalidate cache' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to invalidate cache' })
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-8 text-gray-300">Loading cache statistics...</div>
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4 text-gradient">Cache Management</h2>
      
      {message && (
        <div className={`mb-4 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`}>
          {message.text}
        </div>
      )}

      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3 text-white">Cache Statistics</h3>
        <div className="glass-effect neon-border rounded-lg p-4">
          <pre className="bg-dark-card p-4 rounded-lg overflow-auto text-sm text-gray-300 max-h-64">
            {JSON.stringify(stats, null, 2)}
          </pre>
        </div>
      </div>

      <div className="space-y-4">
        <div className="glass-effect neon-border rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3 text-white">Invalidate User Caches</h3>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              placeholder="User IDs (comma-separated, e.g., 1,2,3)"
              value={userIdsInput}
              onChange={(e) => setUserIdsInput(e.target.value)}
              className="flex-1 px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-white"
            />
            <button
              onClick={handleInvalidateUsers}
              disabled={actionLoading}
              className="px-6 py-2 bg-neon-cyan text-dark-bg rounded-lg font-semibold hover:bg-neon-cyan/80 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {actionLoading ? 'Processing...' : 'Invalidate'}
            </button>
          </div>
          <p className="text-xs text-gray-400">Enter comma-separated user IDs to invalidate their caches</p>
        </div>

        <div className="glass-effect neon-border rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3 text-white">Invalidate Content Cache</h3>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              placeholder="Topics (comma-separated, leave empty for all)"
              value={topicsInput}
              onChange={(e) => setTopicsInput(e.target.value)}
              className="flex-1 px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-white"
            />
            <button
              onClick={() => handleInvalidateContent(false)}
              disabled={actionLoading || topicsInput.trim().length === 0}
              className="px-6 py-2 bg-neon-purple text-white rounded-lg font-semibold hover:bg-neon-purple/80 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {actionLoading ? 'Processing...' : 'Invalidate Topics'}
            </button>
          </div>
          <div className="mt-2">
            <button
              onClick={() => {
                if (confirm('This will clear ALL content cache. Are you sure?')) {
                  handleInvalidateContent(true)
                }
              }}
              disabled={actionLoading}
              className="px-6 py-2 bg-red-500/20 text-red-400 rounded-lg font-semibold hover:bg-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {actionLoading ? 'Processing...' : 'Clear All Content Cache'}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">Clear cache by specific topics or clear all content cache</p>
        </div>
      </div>
    </div>
  )
}

// System Tab Component
function SystemTab() {
  const [health, setHealth] = useState<any>(null)
  const [meta, setMeta] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(getApiUrl('health'), { headers: createAuthHeaders(), credentials: 'include' }).then(r => r.json()).catch(() => ({ status: 'unknown' })),
      fetch(getApiUrl('meta'), { headers: createAuthHeaders(), credentials: 'include' }).then(r => r.json()).catch(() => ({})),
    ])
      .then(([healthData, metaData]) => {
        setHealth(healthData)
        setMeta(metaData)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="text-center py-8 text-gray-300">Loading system information...</div>
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4 text-gradient">System Information</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="glass-effect neon-border rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3 text-white">System Health</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-300">Status:</span>
              <span className={`font-semibold ${health?.status === 'healthy' ? 'text-green-400' : 'text-red-400'}`}>
                {health?.status || 'Unknown'}
              </span>
            </div>
            {health?.components && Object.entries(health.components).map(([key, value]: [string, any]) => (
              <div key={key} className="flex justify-between">
                <span className="text-gray-300 capitalize">{key}:</span>
                <span className={`font-semibold ${
                  value.status === 'ok' ? 'text-green-400' : 
                  value.status === 'degraded' ? 'text-yellow-400' : 
                  'text-red-400'
                }`}>
                  {value.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-effect neon-border rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3 text-white">System Metadata</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-300">Service:</span>
              <span className="text-white">{meta?.service || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-300">Version:</span>
              <span className="text-white">{meta?.version || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-300">Environment:</span>
              <span className="text-white">{meta?.environment || 'N/A'}</span>
            </div>
            {meta?.commit && (
              <div className="flex justify-between">
                <span className="text-gray-300">Commit:</span>
                <span className="text-white font-mono text-sm">{meta.commit.substring(0, 7)}</span>
              </div>
            )}
            {meta?.build_time && (
              <div className="flex justify-between">
                <span className="text-gray-300">Build Time:</span>
                <span className="text-white text-sm">{meta.build_time}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="glass-effect neon-border rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-3 text-white">Full Health Data</h3>
        <pre className="bg-dark-card p-4 rounded-lg overflow-auto text-sm text-gray-300 max-h-96">
          {JSON.stringify(health, null, 2)}
        </pre>
      </div>
    </div>
  )
}

// Moderation Tab Component
function ModerationTab() {
  const [actionLoading, setActionLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const handleBumpVersion = async () => {
    if (!confirm('This will invalidate ALL content cache. Are you sure?')) {
      return
    }

    setActionLoading(true)
    setMessage(null)
    try {
      const response = await fetch(getApiUrl('v1/admin/moderation/bump-version'), {
        method: 'POST',
        headers: createAuthHeaders(),
        credentials: 'include',
      })
      const data = await response.json()
      if (response.ok) {
        setMessage({ type: 'success', text: data.message || 'Moderation version bumped successfully' })
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to bump moderation version' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to bump moderation version' })
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4 text-gradient">Moderation Management</h2>
      
      {message && (
        <div className={`mb-4 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`}>
          {message.text}
        </div>
      )}

      <div className="glass-effect neon-border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 text-white">Bump Moderation Version</h3>
        <p className="text-gray-300 mb-4">
          This will invalidate ALL content cache and force regeneration with new moderation rules.
          Use this when moderation rules or content policies have changed.
        </p>
        <button
          onClick={handleBumpVersion}
          disabled={actionLoading}
          className="px-6 py-3 bg-red-500/20 text-red-400 rounded-lg font-semibold hover:bg-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {actionLoading ? 'Processing...' : 'Bump Moderation Version'}
        </button>
      </div>
    </div>
  )
}

// Billing Tab Component (Dunning Processes)
function BillingTab() {
  const [processes, setProcesses] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedProcess, setSelectedProcess] = useState<number | null>(null)
  const [processDetails, setProcessDetails] = useState<any>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [detailsLoading, setDetailsLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [statusFilter])

  const loadData = async () => {
    setLoading(true)
    try {
      const [processesData, statsData] = await Promise.all([
        fetch(getApiUrl(`v1/admin/dunning/processes${statusFilter ? `?status=${statusFilter}` : ''}`), {
          headers: createAuthHeaders(),
          credentials: 'include',
        }).then(r => r.json()).catch(() => ({ processes: [], count: 0, total: 0 })),
        fetch(getApiUrl('v1/admin/dunning/stats'), {
          headers: createAuthHeaders(),
          credentials: 'include',
        }).then(r => r.json()).catch(() => ({ stats: null })),
      ])
      
      setProcesses(processesData.processes || [])
      setStats(statsData.stats)
    } catch (err) {
      console.error('Failed to load billing data:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadProcessDetails = async (processId: number) => {
    setDetailsLoading(true)
    try {
      const response = await fetch(getApiUrl(`v1/admin/dunning/processes/${processId}`), {
        headers: createAuthHeaders(),
        credentials: 'include',
      })
      if (response.ok) {
        const data = await response.json()
        setProcessDetails(data)
        setSelectedProcess(processId)
      }
    } catch (err) {
      console.error('Failed to load process details:', err)
    } finally {
      setDetailsLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-8 text-gray-300">Loading billing data...</div>
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4 text-gradient">Billing & Payment Recovery</h2>
      
      {/* Statistics */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="glass-effect neon-border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-1">Total Processes</h3>
            <p className="text-2xl font-bold text-white">{stats.total || 0}</p>
          </div>
          <div className="glass-effect neon-border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-1">Active</h3>
            <p className="text-2xl font-bold text-yellow-400">{stats.by_status?.active || 0}</p>
          </div>
          <div className="glass-effect neon-border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-1">Amount Due</h3>
            <p className="text-xl font-bold text-red-400">${(stats.total_amount_due || 0).toFixed(2)}</p>
          </div>
          <div className="glass-effect neon-border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-1">Recovery Rate</h3>
            <p className="text-xl font-bold text-green-400">{(stats.recovery_rate || 0).toFixed(1)}%</p>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="mb-4">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-white"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="grace_period">Grace Period</option>
          <option value="recovering">Recovering</option>
          <option value="recovered">Recovered</option>
          <option value="cancelled">Cancelled</option>
          <option value="exhausted">Exhausted</option>
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Process List */}
        <div>
          <h3 className="text-lg font-semibold mb-3 text-white">Dunning Processes ({processes.length})</h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {processes.length === 0 ? (
              <div className="text-center py-8 text-gray-400">No dunning processes found</div>
            ) : (
              processes.map((process) => (
                <div
                  key={process.id}
                  onClick={() => loadProcessDetails(process.id)}
                  className={`glass-effect neon-border rounded-lg p-4 cursor-pointer hover:border-neon-cyan transition-colors ${
                    selectedProcess === process.id ? 'border-neon-cyan' : ''
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-semibold text-white">Process #{process.id}</p>
                      <p className="text-xs text-gray-400">Subscription: {process.subscription_id}</p>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      process.status === 'active' ? 'bg-yellow-500/20 text-yellow-400' :
                      process.status === 'recovered' ? 'bg-green-500/20 text-green-400' :
                      process.status === 'cancelled' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {process.status}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-300">Due: ${process.amount_due?.toFixed(2)}</span>
                    <span className="text-gray-300">Recovered: ${process.amount_recovered?.toFixed(2)}</span>
                  </div>
                  {process.next_action_at && (
                    <p className="text-xs text-gray-400 mt-1">
                      Next action: {new Date(process.next_action_at).toLocaleString()}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Process Details */}
        <div>
          <h3 className="text-lg font-semibold mb-3 text-white">Process Details</h3>
          {detailsLoading ? (
            <div className="text-center py-8 text-gray-300">Loading details...</div>
          ) : processDetails ? (
            <div className="glass-effect neon-border rounded-lg p-4 space-y-4">
              <div>
                <h4 className="font-semibold text-white mb-2">Process Information</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-300">Status:</span>
                    <span className="text-white">{processDetails.process.status}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Stage:</span>
                    <span className="text-white">{processDetails.process.current_stage}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Amount Due:</span>
                    <span className="text-white">${processDetails.process.amount_due?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Amount Recovered:</span>
                    <span className="text-green-400">${processDetails.process.amount_recovered?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Attempts:</span>
                    <span className="text-white">{processDetails.process.total_attempts}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Emails Sent:</span>
                    <span className="text-white">{processDetails.process.total_emails_sent}</span>
                  </div>
                </div>
              </div>

              {processDetails.payment_attempts && processDetails.payment_attempts.length > 0 && (
                <div>
                  <h4 className="font-semibold text-white mb-2">Payment Attempts ({processDetails.payment_attempts.length})</h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {processDetails.payment_attempts.map((attempt: any) => (
                      <div key={attempt.id} className="bg-dark-card p-2 rounded text-xs">
                        <div className="flex justify-between">
                          <span className="text-gray-300">${attempt.amount?.toFixed(2)}</span>
                          <span className={`${
                            attempt.status === 'succeeded' ? 'text-green-400' :
                            attempt.status === 'failed' ? 'text-red-400' :
                            'text-yellow-400'
                          }`}>
                            {attempt.status}
                          </span>
                        </div>
                        {attempt.failure_message && (
                          <p className="text-red-400 mt-1">{attempt.failure_message}</p>
                        )}
                        <p className="text-gray-400 mt-1">
                          {attempt.attempted_at ? new Date(attempt.attempted_at).toLocaleString() : 'N/A'}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {processDetails.notifications && processDetails.notifications.length > 0 && (
                <div>
                  <h4 className="font-semibold text-white mb-2">Notifications ({processDetails.notifications.length})</h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {processDetails.notifications.map((notif: any) => (
                      <div key={notif.id} className="bg-dark-card p-2 rounded text-xs">
                        <div className="flex justify-between">
                          <span className="text-gray-300">{notif.notification_type}</span>
                          <span className="text-gray-400">{notif.sent_to}</span>
                        </div>
                        <p className="text-gray-300 mt-1">{notif.subject}</p>
                        <p className="text-gray-400 mt-1">
                          {notif.sent_at ? new Date(notif.sent_at).toLocaleString() : 'N/A'}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">Select a process to view details</div>
          )}
        </div>
      </div>
    </div>
  )
}

// Model Preferences Tab Component
function ModelPreferencesTab() {
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [preferences, setPreferences] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [editingPreference, setEditingPreference] = useState<{ content_type: string; model_name: string } | null>(null)

  useEffect(() => {
    loadAvailableModels()
  }, [])

  const loadAvailableModels = async () => {
    try {
      const response = await fetch(getApiUrl('v1/admin/model-preferences/available-models'), {
        headers: createAuthHeaders(),
        credentials: 'include',
      })
      if (response.ok) {
        const data = await response.json()
        setAvailableModels(data.models || [])
      }
    } catch (err) {
      console.error('Failed to load available models:', err)
    }
  }

  const loadUserPreferences = async (userId: number) => {
    setLoading(true)
    setMessage(null)
    try {
      const response = await fetch(getApiUrl(`v1/admin/users/${userId}/model-preferences`), {
        headers: createAuthHeaders(),
        credentials: 'include',
      })
      if (response.ok) {
        const data = await response.json()
        setPreferences(data)
        setSelectedUserId(userId)
      } else {
        const errorData = await response.json()
        setMessage({ type: 'error', text: errorData.detail || 'Failed to load user preferences' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to load user preferences' })
    } finally {
      setLoading(false)
    }
  }

  const handleSetPreference = async (contentType: string, modelName: string) => {
    if (!selectedUserId) return
    
    setActionLoading(true)
    setMessage(null)
    try {
      const response = await fetch(getApiUrl(`v1/admin/users/${selectedUserId}/model-preferences`), {
        method: 'POST',
        headers: createAuthHeaders({ 'Content-Type': 'application/json' }),
        credentials: 'include',
        body: JSON.stringify({
          user_id: selectedUserId,
          content_type: contentType,
          model_name: modelName,
        }),
      })
      const data = await response.json()
      if (response.ok) {
        setMessage({ type: 'success', text: data.message || 'Model preference set successfully' })
        loadUserPreferences(selectedUserId)
        setEditingPreference(null)
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to set model preference' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to set model preference' })
    } finally {
      setActionLoading(false)
    }
  }

  const handleDeletePreference = async (contentType: string) => {
    if (!selectedUserId) return
    
    if (!confirm(`Remove custom model for ${contentType}? User will revert to tier-based model.`)) {
      return
    }
    
    setActionLoading(true)
    setMessage(null)
    try {
      const response = await fetch(getApiUrl(`v1/admin/users/${selectedUserId}/model-preferences/${contentType}`), {
        method: 'DELETE',
        headers: createAuthHeaders(),
        credentials: 'include',
      })
      const data = await response.json()
      if (response.ok) {
        setMessage({ type: 'success', text: data.message || 'Model preference removed' })
        loadUserPreferences(selectedUserId)
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to remove model preference' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to remove model preference' })
    } finally {
      setActionLoading(false)
    }
  }

  const contentTypes = ['blog', 'social', 'audio', 'video']

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4 text-gradient">User Model Preferences</h2>
      
      {message && (
        <div className={`mb-4 p-4 rounded-lg ${
          message.type === 'success' 
            ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
            : 'bg-red-500/20 text-red-400 border border-red-500/30'
        }`}>
          {message.text}
        </div>
      )}

      {/* User Selection */}
      <div className="mb-6 glass-effect neon-border rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-3 text-white">Select User</h3>
        <div className="flex gap-2">
          <input
            type="number"
            placeholder="User ID"
            value={selectedUserId || ''}
            onChange={(e) => {
              const userId = e.target.value ? parseInt(e.target.value) : null
              setSelectedUserId(userId)
              if (userId) {
                loadUserPreferences(userId)
              } else {
                setPreferences(null)
              }
            }}
            className="flex-1 px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-white"
          />
          <button
            onClick={() => selectedUserId && loadUserPreferences(selectedUserId)}
            disabled={!selectedUserId || loading}
            className="px-6 py-2 bg-neon-cyan text-dark-bg rounded-lg font-semibold hover:bg-neon-cyan/80 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Load Preferences'}
          </button>
        </div>
        {preferences && (
          <p className="text-sm text-gray-300 mt-2">
            User: {preferences.user_email} (ID: {preferences.user_id})
          </p>
        )}
      </div>

      {/* Model Preferences */}
      {preferences && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-white">Model Preferences</h3>
          {contentTypes.map((contentType) => {
            const preference = preferences.preferences?.find((p: any) => p.content_type === contentType)
            const isEditing = editingPreference?.content_type === contentType
            
            return (
              <div key={contentType} className="glass-effect neon-border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-white capitalize">{contentType}</h4>
                  {preference && !isEditing && (
                    <button
                      onClick={() => handleDeletePreference(contentType)}
                      disabled={actionLoading}
                      className="px-3 py-1 bg-red-500/20 text-red-400 rounded text-sm hover:bg-red-500/30 disabled:opacity-50"
                    >
                      Remove
                    </button>
                  )}
                </div>
                
                {isEditing ? (
                  <div className="flex gap-2">
                    <select
                      value={editingPreference.model_name}
                      onChange={(e) => setEditingPreference({ ...editingPreference, model_name: e.target.value })}
                      className="flex-1 px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-white"
                    >
                      {availableModels.map((model) => (
                        <option key={model} value={model}>{model}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => handleSetPreference(contentType, editingPreference.model_name)}
                      disabled={actionLoading}
                      className="px-4 py-2 bg-green-500/20 text-green-400 rounded hover:bg-green-500/30 disabled:opacity-50"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingPreference(null)}
                      className="px-4 py-2 bg-gray-500/20 text-gray-400 rounded hover:bg-gray-500/30"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-gray-300">
                        Model: <span className="text-white font-semibold">
                          {preference?.model_name || 'Tier-based (default)'}
                        </span>
                      </p>
                      {preference && (
                        <p className="text-xs text-gray-400 mt-1">
                          Set on {new Date(preference.updated_at || preference.created_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => setEditingPreference({
                        content_type: contentType,
                        model_name: preference?.model_name || availableModels[0] || 'gpt-4o-mini'
                      })}
                      className="px-4 py-2 bg-neon-cyan text-dark-bg rounded-lg font-semibold hover:bg-neon-cyan/80"
                    >
                      {preference ? 'Change' : 'Set Custom'}
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
