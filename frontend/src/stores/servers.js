import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { serversAPI, dashboardAPI } from '../services/api'

export const useServersStore = defineStore('servers', () => {
  const servers = ref([])
  const dashboardStats = ref(null)
  const isLoading = ref(false)
  const error = ref(null)
  const lastUpdated = ref(null)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const totalServers = ref(0)
  const totalPages = ref(1)

  // -------------------------
  // Reusable async executor
  // -------------------------
  const execute = async (action) => {
    isLoading.value = true
    error.value = null

    try {
      return await action()
    } catch (err) {
      error.value = err.message || 'Unexpected error'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // -------------------------
  // Health Score
  // -------------------------
  const healthScore = computed(() => {
    if (!dashboardStats.value?.average_usage) return null

    const sanitize = (val) => {
      if (val == null || isNaN(val)) return 100
      return Math.max(0, Math.min(100, Number(val)))
    }

    const cpu = sanitize(dashboardStats.value.average_usage.cpu)
    const memory = sanitize(dashboardStats.value.average_usage.memory)
    const disk = sanitize(dashboardStats.value.average_usage.disk)

    const score = 100 - (
      cpu * 0.4 +
      memory * 0.4 +
      disk * 0.2
    )

    return Math.max(0, Math.min(100, Math.round(score)))
  })

  const healthStatus = computed(() => {
    if (healthScore.value === null) return 'unknown'
    if (healthScore.value >= 80) return 'healthy'
    if (healthScore.value >= 60) return 'warning'
    return 'critical'
  })

  // -------------------------
  // Fetching
  // -------------------------
  const fetchServers = async () =>
    execute(async () => {

      const response = await serversAPI.getServers({
        page: currentPage.value,
        limit: pageSize.value
      })

      servers.value = response.data.servers
      totalServers.value = response.data.total
      totalPages.value = response.data.total_pages
      console.log(totalServers.value)
      console.log(totalPages.value)
    })

  const refreshDashboard = async () =>
    execute(async () => {
      const response = await dashboardAPI.getStats()
      dashboardStats.value = response.data
      lastUpdated.value = new Date()
    })

  // -------------------------
  // CRUD
  // -------------------------
  const createServer = async (serverData) =>
    execute(async () => {
      const response = await serversAPI.createServer(serverData)
      servers.value.push(response.data.server)
      return response.data.server
    })

  const updateServer = async (id, serverData) =>
    execute(async () => {
      const response = await serversAPI.updateServer(id, serverData)
      const index = servers.value.findIndex(s => s.id === id)
      if (index !== -1) {
        servers.value[index] = response.data.server
      }
      return response.data.server
    })

  const deleteServer = async (id) =>
    execute(async () => {
      await serversAPI.deleteServer(id)
      servers.value = servers.value.filter(s => s.id !== id)
    })

  const getServerById = (id) =>
    servers.value.find(s => s.id === parseInt(id))

  const clearError = () => {
    error.value = null
  }

  return {
    servers,
    dashboardStats,
    isLoading,
    error,
    lastUpdated,
    healthScore,
    healthStatus,
    currentPage,
    pageSize,
    totalServers,
    totalPages,
    fetchServers,
    refreshDashboard,
    createServer,
    updateServer,
    deleteServer,
    getServerById,
    clearError
  }
})
