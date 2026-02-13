<script>
// Core Vue imports
import { onMounted, computed } from 'vue'

// Centralized store (single source of truth for server data)
import { useServersStore } from '../stores/servers'

// Visualization components
import StatusChart from '../components/StatusChart.vue'
import UsageChart from '../components/UsageChart.vue'

export default {
  name: 'DashboardView',

  // Dashboard-specific visualization components
  components: {
    StatusChart,
    UsageChart
  },

  setup() {
    // Access global server store
    const serversStore = useServersStore()

    /**
     * Derive server status breakdown from dashboard stats.
     * Keeps template clean and avoids defensive checks there.
     */
    const statusCounts = computed(() => {
      if (!serversStore.dashboardStats) return {}
      return serversStore.dashboardStats.status_breakdown
    })

    /**
     * Derive average usage metrics.
     * Abstracted as computed to preserve reactivity.
     */
    const averageUsage = computed(() => {
      if (!serversStore.dashboardStats) return {}
      return serversStore.dashboardStats.average_usage
    })

    /**
     * Maps server status to consistent UI color styles.
     * Keeps presentation logic centralized.
     */
    const getStatusColor = (status) => {
      const colors = {
        online: 'text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
        offline: 'text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
        maintenance: 'text-yellow-700 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30',
        error: 'text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30'
      }
      return colors[status] || 'text-gray-700 bg-gray-100 dark:text-gray-400 dark:bg-gray-800'
    }

    /**
     * Dynamically determine health score color.
     * Encapsulates presentation logic separate from template.
     */
    const getHealthColor = () => {
      const status = serversStore.healthStatus
      if (status === 'healthy') return 'text-green-600'
      if (status === 'warning') return 'text-yellow-600'
      if (status === 'critical') return 'text-red-600'
      return 'text-gray-600'
    }

    /**
     * Initial dashboard load:
     * - Fetch server list (used in recent section)
     * - Fetch aggregated dashboard metrics
     * Parallelized for performance.
     */
    onMounted(async () => {
      await Promise.all([
        serversStore.fetchServers(),
        serversStore.refreshDashboard()
      ])
    })

    return {
      serversStore,
      statusCounts,
      averageUsage,
      getHealthColor,
      getStatusColor
    }
  }
}
</script>

<template>
  <!-- Global loading overlay for dashboard -->
  <div
    v-if="serversStore.isLoading"
    class="absolute inset-0 bg-white/50 flex items-center justify-center"
  >
    Loading...
  </div>

  <div class="px-6 py-8">
    <!-- Page Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
        Dashboard
      </h1>
      <p class="text-gray-600 dark:text-gray-400">
        Monitor your server infrastructure
      </p>
    </div>

    <!-- High-Level Summary Cards -->
    <!-- Designed for quick-glance operational awareness -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">

      <!-- Total Servers -->
      <div class="card p-6">
        <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">
          Total Servers
        </h3>
        <p class="text-3xl font-bold text-gray-900 dark:text-gray-100">
          {{ serversStore.dashboardStats?.total_servers || 0 }}
        </p>
      </div>

      <!-- Online Count -->
      <div class="card p-6">
        <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">
          Online
        </h3>
        <p class="text-3xl font-bold text-green-600 dark:text-green-400">
          {{ statusCounts.online || 0 }}
        </p>
      </div>

      <!-- Offline Count -->
      <div class="card p-6">
        <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">
          Offline
        </h3>
        <p class="text-3xl font-bold text-red-600 dark:text-red-400">
          {{ statusCounts.offline || 0 }}
        </p>
      </div>

      <!-- Maintenance Count -->
      <div class="card p-6">
        <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">
          Maintenance
        </h3>
        <p class="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
          {{ statusCounts.maintenance || 0 }}
        </p>
      </div>

      <!-- System Health Score -->
      <!-- Composite metric derived from weighted resource usage -->
      <div class="card p-6">
        <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">
          Health Score
        </h3>

        <p
          class="text-3xl font-bold"
          :class="getHealthColor()"
        >
          {{ serversStore.healthScore ?? '—' }}
        </p>

        <p class="text-xs text-gray-500 mt-1">
          Weighted (CPU 40%, Memory 40%, Disk 20%)
        </p>
      </div>
    </div>

    <!-- Dashboard Controls -->
    <!-- Displays last refresh timestamp and manual refresh trigger -->
    <div class="flex items-center justify-between mb-4">
      <div class="text-sm text-gray-500">
        Last updated:
        {{ serversStore.lastUpdated
            ? serversStore.lastUpdated.toLocaleTimeString()
            : 'Never' }}
      </div>

      <button
        @click="serversStore.refreshDashboard"
        class="px-3 py-1 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-500 cursor-pointer"
      >
        Refresh
      </button>
    </div>

    <!-- Visualization Layer -->
    <!-- Provides visual breakdown for quick anomaly detection -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">

      <div class="card p-6">
        <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
          Server Status Distribution
        </h3>
        <StatusChart :data="statusCounts" />
      </div>

      <div class="card p-6">
        <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
          Average Resource Usage
        </h3>
        <UsageChart :data="averageUsage" />
      </div>

    </div>

    <!-- Recent Servers Section -->
    <!-- Intended for quick operational visibility (top 10 snapshot) -->
    <div class="card">

      <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">
          Recent Servers
        </h3>
      </div>

      <div class="overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">

          <!-- Table Header -->
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                Name
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                IP Address
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                Location
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                CPU Usage
              </th>
            </tr>
          </thead>

          <!-- Table Body -->
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="server in serversStore.servers.slice(0, 10)"
              :key="server.id"
            >
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium">
                  {{ server.name }}
                </div>
              </td>

              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  class="inline-flex px-2 text-xs font-semibold rounded-full"
                  :class="getStatusColor(server.status)"
                >
                  {{ server.status }}
                </span>
              </td>

              <td class="px-6 py-4 whitespace-nowrap text-sm">
                {{ server.ip_address }}
              </td>

              <td class="px-6 py-4 whitespace-nowrap text-sm">
                {{ server.location }}
              </td>

              <td class="px-6 py-4 whitespace-nowrap text-sm">
                {{ server.cpu_usage }}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Navigation to Full Management View -->
      <div class="px-6 py-3 bg-gray-50 dark:bg-gray-700 text-right">
        <RouterLink
          to="/servers"
          class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
        >
          View all servers →
        </RouterLink>
      </div>

    </div>
  </div>
</template>
