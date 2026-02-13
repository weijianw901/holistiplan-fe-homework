<script>
import { ref, onMounted, computed } from 'vue'
import { useServersStore } from '../stores/servers'
import EditServerModal from '../components/EditServerModal.vue'
import filterMethods from '../helpers/filterMethods'
import { useAuthStore } from '../stores/auth';

export default {
  name: 'ServersView',

  // Modal component used for editing server information
  components: {
    EditServerModal
  },

  setup() {
    const authStore = useAuthStore();
    /**
     * Centralized Pinia store.
     * Responsible for API communication, pagination state,
     * and server CRUD operations.
     */
    const serversStore = useServersStore()

    /**
     * Local UI state for modal visibility and selection.
     * These are view-level concerns, not domain data.
     */
    const showDeleteModal = ref(false)
    const serverToDelete = ref(null)
    const showEditModal = ref(false)
    const serverToEdit = ref(null)

    /**
     * Client-side filter state.
     * Filters are intentionally local and non-persistent.
     */
    const searchQuery = ref('')
    const statusFilter = ref('')
    const locationFilter = ref('')

    /**
     * Sorting configuration.
     * Maintains currently selected column and direction.
     */
    const sortKey = ref('name')
    const sortDirection = ref('asc')

    /**
     * Bulk selection state.
     * Uses Set for constant-time lookups and uniqueness.
     */
    const selectedIds = ref(new Set())

    /**
     * Derived server list.
     * Applies filtering and sorting without mutating
     * the original store data.
     */
    const servers = computed(() => {
      let result = [...serversStore.servers]

      // ---- Filtering ----
      if (searchQuery.value) {
        const q = searchQuery.value.toLowerCase()
        result = result.filter(server =>
          server.name?.toLowerCase().includes(q) ||
          server.ip_address?.toLowerCase().includes(q)
        )
      }

      if (statusFilter.value) {
        result = result.filter(server =>
          server.status === statusFilter.value
        )
      }

      if (locationFilter.value) {
        result = result.filter(server =>
          server.location === locationFilter.value
        )
      }

      // ---- Sorting ----
      result.sort((a, b) => {
        let valA = a[sortKey.value]
        let valB = b[sortKey.value]

        // Ensure numeric comparison for uptime
        if (sortKey.value === 'uptime') {
          valA = Number(valA)
          valB = Number(valB)
        }

        // Normalize string comparison
        if (typeof valA === 'string') valA = valA.toLowerCase()
        if (typeof valB === 'string') valB = valB.toLowerCase()

        if (valA < valB) return sortDirection.value === 'asc' ? -1 : 1
        if (valA > valB) return sortDirection.value === 'asc' ? 1 : -1
        return 0
      })

      return result
    })

    /**
     * Maps server status to consistent UI theme colors.
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
     * Opens delete confirmation modal.
     */
    const confirmDelete = (server) => {
      serverToDelete.value = server
      showDeleteModal.value = true
    }

    /**
     * Executes single server deletion.
     */
    const deleteServer = async () => {
      if (serverToDelete.value) {
        try {
          await serversStore.deleteServer(serverToDelete.value.id)
          showDeleteModal.value = false
          serverToDelete.value = null
        } catch (error) {
          console.error('Failed to delete server:', error)
        }
      }
    }

    /**
     * Opens edit modal.
     */
    const editServer = (server) => {
      serverToEdit.value = server
      showEditModal.value = true
    }

    /**
     * Closes edit modal.
     */
    const handleEditClose = () => {
      showEditModal.value = false
      serverToEdit.value = null
    }

    /**
     * Bulk status update operation.
     * Iterates through selected IDs and updates each.
     */
    const bulkUpdateStatus = async (newStatus) => {
      for (const id of selectedIds.value) {
        await serversStore.updateServer(id, { status: newStatus })
      }
      selectedIds.value.clear()
    }

    /**
     * Bulk deletion with confirmation safeguard.
     */
    const bulkDelete = async () => {
      if (!confirm(`Delete ${selectedIds.value.size} servers?`)) return

      for (const id of selectedIds.value) {
        await serversStore.deleteServer(id)
      }
      selectedIds.value.clear()
    }

    /**
     * Callback triggered after edit is saved.
     * Store automatically syncs updated server.
     */
    const handleEditSaved = (updatedServer) => {
      console.warn('Server updated:', updatedServer)
    }

    /**
     * Formats uptime (seconds) into human-readable string.
     */
    const formatUptime = (seconds) => {
      const days = Math.floor(seconds / 86400)
      const hours = Math.floor((seconds % 86400) / 3600)
      if (days > 0) return `${days}d ${hours}h`
      if (hours > 0) return `${hours}h`
      return `${Math.floor(seconds / 60)}m`
    }

    /**
     * Selection helpers.
     * Reassigns Set to preserve Vue reactivity.
     */
    const isSelected = (id) => selectedIds.value.has(id)

    const toggleSelect = (id) => {
      const newSet = new Set(selectedIds.value)

      if (newSet.has(id)) newSet.delete(id)
      else newSet.add(id)

      selectedIds.value = newSet
    }

    const selectedCount = computed(() => selectedIds.value.size)

    const allVisibleSelected = computed(() =>
      servers.value.length > 0 &&
      servers.value.every(server =>
        selectedIds.value.has(server.id)
      )
    )

    const toggleSelectAll = () => {
      const newSet = new Set(selectedIds.value)

      if (allVisibleSelected.value) {
        servers.value.forEach(server => newSet.delete(server.id))
      } else {
        servers.value.forEach(server => newSet.add(server.id))
      }

      selectedIds.value = newSet
    }

    /**
     * Sorting helpers.
     */
    const isSorted = (key) => sortKey.value === key

    const sortIcon = (key) => {
      if (sortKey.value !== key) return '↕'
      return sortDirection.value === 'asc' ? '▲' : '▼'
    }

    const toggleSort = (key) => {
      if (sortKey.value === key) {
        sortDirection.value =
          sortDirection.value === 'asc' ? 'desc' : 'asc'
      } else {
        sortKey.value = key
        sortDirection.value = 'asc'
      }
    }

    /**
     * Pagination handler.
     * Updates page state and fetches data from backend.
     */
    const changePage = async (page) => {
      if (page < 1 || page > serversStore.totalPages) return

      serversStore.currentPage = page
      await serversStore.fetchServers()

      selectedIds.value = new Set()
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    /**
     * Pagination display helpers.
     */
    const showingFrom = computed(() => {
      return (serversStore.currentPage - 1) * serversStore.pageSize + 1
    })

    const showingTo = computed(() => {
      const possibleEnd = serversStore.currentPage * serversStore.pageSize
      return Math.min(possibleEnd, serversStore.totalServers)
    })

    /**
     * Builds pagination range with ellipsis compression.
     */
    const pageNumbers = computed(() => {
      const total = serversStore.totalPages
      const current = serversStore.currentPage
      const delta = 2
      const range = []
      const pages = []

      for (let i = 1; i <= total; i++) {
        if (
          i === 1 ||
          i === total ||
          (i >= current - delta && i <= current + delta)
        ) {
          range.push(i)
        }
      }

      let last
      for (const page of range) {
        if (last && page - last > 1) pages.push('...')
        pages.push(page)
        last = page
      }

      return pages
    })


    /**
     * Initial server fetch on mount.
     */
    onMounted(() => {
      serversStore.fetchServers()
    })


    return {
      servers,
      showDeleteModal,
      serverToDelete,
      showEditModal,
      serverToEdit,
      serversStore,
      getStatusColor,
      confirmDelete,
      deleteServer,
      editServer,
      handleEditClose,
      handleEditSaved,
      formatUptime,
      toggleSort,
      isSorted,
      sortIcon,
      searchQuery,
      statusFilter,
      locationFilter,
      sortKey,
      sortDirection,
      selectedIds,
      isSelected,
      toggleSelect,
      toggleSelectAll,
      bulkUpdateStatus,
      bulkDelete,
      allVisibleSelected,
      selectedCount,
      showingFrom,
      showingTo,
      changePage,
      pageNumbers,
      authStore,
      ...filterMethods
    };
  }
};
</script>

<template>
  <div v-if="serversStore.isLoading" class="absolute inset-0 bg-white/50 flex items-center justify-center">
    Loading...
  </div>
  <div class="px-6 py-8">
    <div class="mb-8">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">Servers</h1>
          <p class="text-gray-600 dark:text-gray-400">Manage your server infrastructure</p>
        </div>
        <RouterLink
          to="/servers/new"
          class="btn btn-primary"
        >
          Add Server
        </RouterLink>
      </div>
    </div>

    <!-- Servers Table -->
    <div class="card overflow-hidden">
      
      <!-- sort and filter -->
      <div class="p-4 border-b border-gray-200 dark:border-gray-700 space-y-4">

        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">

          <input
            v-model="searchQuery"
            placeholder="Search name or IP..."
            class="input"
          />

          <select v-model="statusFilter" class="input cursor-pointer">
            <option value="">All Status</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
            <option value="maintenance">Maintenance</option>
            <option value="error">Error</option>
          </select>

          <input
            v-model="locationFilter"
            placeholder="Filter by location"
            class="input"
          />

          <button
            @click="searchQuery=''; statusFilter=''; locationFilter=''"
            class="btn btn-secondary cursor-pointer"
          >
            Clear Filters
          </button>

        </div>
      </div>
      <div class="overflow-x-auto">
        <div
          class="p-4 bg-gray-100 dark:bg-gray-700 flex justify-between items-center"
        >
          <div class="text-sm">
            <span v-if="selectedCount > 0">
              {{ selectedCount }} selected
            </span>
            <span v-else class="text-gray-400">
              No items selected
            </span>
          </div>
          <div v-if="authStore.user?.is_admin"
            class="space-x-2">
            <button
              @click="bulkUpdateStatus('online')"
              class="btn bg-green-600 dark:bg-green-900/30 cursor-pointer"
              :disabled="selectedCount === 0"
              :class="{ 'opacity-50 cursor-not-allowed': selectedCount === 0 }"
            >
              Set Online
            </button>

            <button
              @click="bulkUpdateStatus('offline')"
              class="btn bg-red-600 dark:bg-red-900/30 cursor-pointer"
              :disabled="selectedCount === 0"
              :class="{ 'opacity-50 cursor-not-allowed': selectedCount === 0 }"
            >
              Set Offline
            </button>

            <button
              @click="bulkUpdateStatus('maintenance')"
              class="btn bg-yellow-600 dark:bg-yellow-900/30 cursor-pointer"
              :disabled="selectedCount === 0"
              :class="{ 'opacity-50 cursor-not-allowed': selectedCount === 0 }"
            >
              Set Maintenance
            </button>

            <button
              @click="bulkUpdateStatus('error')"
              class="btn bg-red-600 dark:bg-red-900/30 cursor-pointer"
              :disabled="selectedCount === 0"
              :class="{ 'opacity-50 cursor-not-allowed': selectedCount === 0 }"
            >
              Set Error
            </button>

            <button
              @click="bulkDelete"
              class="btn btn-danger cursor-pointer"
              :disabled="selectedCount === 0"
              :class="{ 'opacity-50 cursor-not-allowed': selectedCount === 0 }"
            >
              Delete Selected
            </button>
          </div>
        </div>
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-4 text-left">
                <input
                  type="checkbox"
                  :checked="allVisibleSelected"
                  @change="toggleSelectAll"
                  class="cursor-pointer"
                />
              </th>
              <th @click="toggleSort('name')" class="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <div class="flex items-center space-x-1 cursor-pointer">
                  <span>Server</span>
                  <span
                    class="text-xs"
                    :class="{ 'text-indigo-600 font-bold': isSorted('name') }"
                  >
                    {{ sortIcon('name') }}
                  </span>
                </div>
              </th>
              <th @click="toggleSort('status')" class="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <div class="flex items-center space-x-1 cursor-pointer">
                  <span>Status</span>
                  <span
                    class="text-xs"
                    :class="{ 'text-indigo-600 font-bold': isSorted('status') }"
                  >
                    {{ sortIcon('status') }}
                  </span>
                </div>
              </th>
              <th @click="toggleSort('location')" class="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <div class="flex items-center space-x-1 cursor-pointer">
                  <span>Location</span>
                  <span
                    class="text-xs"
                    :class="{ 'text-indigo-600 font-bold': isSorted('location') }"
                  >
                    {{ sortIcon('location') }}
                  </span>
                </div>
              </th>
              <th @click="toggleSort('cpu_usage')" class="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <div class="flex items-center space-x-1 cursor-pointer">
                  <span>Usage</span>
                  <span
                    class="text-xs"
                    :class="{ 'text-indigo-600 font-bold': isSorted('cpu_usage') }"
                  >
                    {{ sortIcon('cpu_usage') }}
                  </span>
                </div>
              </th>
              <th @click="toggleSort('uptime')" class="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <div class="flex items-center space-x-1 cursor-pointer">
                  <span>Uptime</span>
                  <span
                    class="text-xs"
                    :class="{ 'text-indigo-600 font-bold': isSorted('uptime') }"
                  >
                    {{ sortIcon('uptime') }}
                  </span>
                </div>
              </th>
              <th class="px-6 py-4 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="server in servers"
              :key="server.id"
            >
              <td class="px-6 py-4">
                <input
                  type="checkbox"
                  :checked="isSelected(server.id)"
                  @change="toggleSelect(server.id)"
                  class="cursor-pointer"
                />
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div>
                  <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ server.name }}</div>
                  <div class="text-sm text-gray-500 dark:text-gray-400">{{ server.hostname }}</div>
                  <div class="text-sm text-gray-500 dark:text-gray-400">{{ server.ip_address }}</div>
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
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900 dark:text-gray-100">{{ server.location }}</div>
                <div class="text-sm text-gray-500 dark:text-gray-400">{{ server.os }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900 dark:text-gray-100">
                  CPU: {{ formatPercent(server.cpu_usage) }}%
                </div>
                <div class="text-sm text-gray-900 dark:text-gray-100">
                  Memory: {{ formatPercent(server.memory_usage) }}%
                </div>
                <div class="text-sm text-gray-900 dark:text-gray-100">
                  Disk: {{ formatPercent(server.disk_usage) }}%
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                {{ formatUptime(server.uptime) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button
                  @click="editServer(server)"
                  class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 mr-3 cursor-pointer"
                >
                  Edit
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="flex justify-between items-center p-4 border-t border-gray-200 dark:border-gray-700">

          <div class="text-sm text-gray-500">
            <div class="text-sm text-gray-500">
              Showing {{ showingFrom }}–{{ showingTo }} of {{ serversStore.totalServers }}
            </div>
          </div>
            
          <!-- Right Side -->
          <div class="flex items-center space-x-3">

            <!-- Page Size -->
            <select
              v-model="serversStore.pageSize"
              @change="changePage(1)"
              class="form-input !w-[60px] cursor-pointer"
            >
              <option :value="5">5</option>
              <option :value="10">10</option>
              <option :value="25">25</option>
              <option :value="50">50</option> 
            </select>

            <!-- Pagination -->
            <div class="flex items-center space-x-1">

              <button
                @click="changePage(serversStore.currentPage - 1)"
                :disabled="serversStore.currentPage === 1"
                class="btn btn-secondary px-3 cursor-pointer"
              >
                Previous
              </button>

              <button
                v-for="page in pageNumbers"
                :key="page"
                @click="page !== '...' && changePage(page)"
                class="px-3 py-1 rounded border text-sm"
                :disabled="page === '...'"
                :class="{
                  'bg-indigo-600 text-white border-indigo-600 cursor-pointer':
                    page === serversStore.currentPage,
                  'opacity-50 cursor-default':
                    page === '...',
                  'bg-white dark:bg-gray-700 border-gray-300':
                    page !== serversStore.currentPage && page !== '...'
                }"
              >
                {{ page }}
              </button>

              <button
                @click="changePage(serversStore.currentPage + 1)"
                :disabled="serversStore.currentPage === serversStore.totalPages"
                class="btn btn-secondary px-3 cursor-pointer"
              >
                Next
              </button>

            </div>
          </div>


        </div>
      </div>

      <div
        v-if="servers.length === 0"
        class="text-center py-12"
      >
        <p class="text-gray-500 dark:text-gray-400">No servers found.</p>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="showDeleteModal"
      class="fixed inset-0 bg-gray-600 dark:bg-gray-900 bg-opacity-50 dark:bg-opacity-75 overflow-y-auto h-full w-full z-50"
    >
      <div class="relative top-20 mx-auto p-5 border dark:border-gray-600 w-96 shadow-lg rounded-md bg-white dark:bg-gray-800">
        <div class="mt-3 text-center">
          <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">Delete Server</h3>
          <div class="mt-2 px-7 py-3">
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Are you sure you want to delete <strong class="text-gray-900 dark:text-gray-100">{{ serverToDelete?.name }}</strong>?
              This action cannot be undone.
            </p>
          </div>
          <div class="flex justify-center space-x-4 mt-4">
            <button
              @click="showDeleteModal = false"
              class="btn btn-secondary cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="deleteServer"
              class="btn btn-danger cursor-pointer"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Server Modal -->
    <EditServerModal
      v-if="serverToEdit"
      :server="serverToEdit"
      :is-visible="showEditModal"
      @close="handleEditClose"
      @saved="handleEditSaved"
    />
  </div>
</template>
