<template>
  <div id="app" class="min-h-screen">
    <!-- Хедер только для авторизованных пользователей -->
    <header 
      v-if="isAuthenticated" 
      class="app-header p-4 border-b border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900"
    >
      <div class="flex justify-content-between align-items-center max-w-6xl mx-auto">
        <h1 class="m-0 text-xl font-bold text-surface-900 dark:text-surface-0">
          AI База Данных Очков
        </h1>
        
        <!-- Переключатель страниц -->
        <div class="flex align-items-center gap-4">
          <SelectButton 
            v-model="selectedPage" 
            :options="pageOptions" 
            option-label="label"
            option-value="value"
            @change="onPageChange"
            class="page-switcher"
          />
          
          <!-- Информация о пользователе и выход -->
          <div class="flex align-items-center gap-3">
            <div class="text-sm text-surface-700 dark:text-surface-300">
              <div class="font-medium">{{ userInfo.username }}</div>
              <div class="text-xs">{{ getRoleLabel(userInfo.role) }}</div>
            </div>
            <Button
              icon="pi pi-sign-out"
              severity="secondary"
              variant="text"
              @click="logout"
              v-tooltip.left="'Выйти'"
            />
          </div>
        </div>
      </div>
    </header>

    <div class="app-content">
      <router-view />
    </div>

    <Toast />
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import SelectButton from 'primevue/selectbutton'
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import apiService from './services/apiService'

export default {
  name: 'App',
  components: {
    SelectButton,
    Button,
    Toast
  },
  setup() {
    const router = useRouter()
    const route = useRoute()
    const toast = useToast()
    const selectedPage = ref('chat')

    // Информация о пользователе
    const userInfo = ref({
      username: '',
      role: 'support'
    })

    // Проверка авторизации
    // Привязываем к маршруту, чтобы пересчитываться после редиректа с /login
    const isAuthenticated = computed(() => {
      // зависимость от route для реактивного пересчета
      // eslint-disable-next-line no-unused-expressions
      route.fullPath
      return !!localStorage.getItem('access_token')
    })

    // Опции страниц
    const pageOptions = ref([
      {
        label: 'Чат',
        value: 'chat',
        icon: 'pi pi-comments'
      },
      {
        label: 'Файлы',
        value: 'files',
        icon: 'pi pi-upload'
      },
      {
        label: 'Данные',
        value: 'data',
        icon: 'pi pi-table'
      },
      {
        label: 'Изображения',
        value: 'images',
        icon: 'pi pi-images'
      }
    ])

    // Получение информации о пользователе
    const loadUserInfo = () => {
      const savedUserInfo = localStorage.getItem('user_info')
      if (savedUserInfo) {
        userInfo.value = JSON.parse(savedUserInfo)
      }
    }

    // Получение роли на русском
    const getRoleLabel = (role) => {
      const roleLabels = {
        'admin': 'Администратор',
        'support': 'Поддержка'
      }
      return roleLabels[role] || role
    }

    // Выход из системы
    const logout = async () => {
      try {
        await apiService.logout()
      } catch (error) {
        console.error('Logout error:', error)
      } finally {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_info')
        
        toast.add({
          severity: 'info',
          summary: 'Выход',
          detail: 'Вы успешно вышли из системы',
          life: 3000
        })
        
        router.push('/login')
      }
    }

    const onPageChange = (event) => {
      const value = event.value
      if (value === 'chat') {
        router.push('/chat')
      } else if (value === 'files') {
        router.push('/files')
      } else if (value === 'data') {
        router.push('/data')
      } else if (value === 'images') {
        router.push('/images')
      }
    }

    // Отслеживание изменений роута
    watch(route, (newRoute) => {
      const path = newRoute.path
      if (path.includes('/chat')) {
        selectedPage.value = 'chat'
      } else if (path.includes('/files')) {
        selectedPage.value = 'files'
      } else if (path.includes('/data')) {
        selectedPage.value = 'data'
      } else if (path.includes('/images')) {
        selectedPage.value = 'images'
      }
    })

    // Устанавливаем активную страницу при загрузке
    onMounted(() => {
      loadUserInfo()
      
      const currentPath = route.path
      if (currentPath.includes('/files')) {
        selectedPage.value = 'files'
      } else if (currentPath.includes('/data')) {
        selectedPage.value = 'data'
      } else if (currentPath.includes('/images')) {
        selectedPage.value = 'images'
      } else {
        selectedPage.value = 'chat'
      }
    })

    // Подхватываем userInfo сразу после успешной авторизации
    watch(isAuthenticated, (authed) => {
      if (authed) {
        loadUserInfo()
      } else {
        userInfo.value = { username: '', role: 'support' }
      }
    })

    return {
      selectedPage,
      pageOptions,
      onPageChange,
      isAuthenticated,
      userInfo,
      getRoleLabel,
      logout
    }
  }
}

</script>

<style>
#app {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-height: 100vh;
  background: var(--surface-ground);
}

body {
  margin: 0;
  padding: 0;
  background: var(--surface-ground);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  backdrop-filter: blur(8px);
  background: rgba(var(--surface-0), 0.95);
}

.dark-mode .app-header {
  background: rgba(var(--surface-900), 0.95);
}

.app-content {
  min-height: calc(100vh - 80px);
}

.page-switcher {
  background: var(--surface-50);
  border-radius: 12px;
  padding: 4px;
  border: 1px solid var(--surface-200);
}

.dark-mode .page-switcher {
  background: var(--surface-800);
  border-color: var(--surface-700);
}

/* Улучшенные стили для SelectButton */
.page-switcher .p-selectbutton-button {
  border-radius: 8px !important;
  padding: 0.75rem 1.5rem !important;
  font-weight: 500 !important;
  transition: all 0.2s ease !important;
  border: none !important;
  background: transparent !important;
  color: var(--text-color-secondary) !important;
}

.page-switcher .p-selectbutton-button:hover {
  background: var(--surface-100) !important;
  color: var(--text-color) !important;
}

.dark-mode .page-switcher .p-selectbutton-button:hover {
  background: var(--surface-700) !important;
}

.page-switcher .p-selectbutton-button.p-highlight {
  background: var(--primary-color) !important;
  color: var(--primary-color-text) !important;
  box-shadow: 0 2px 8px rgba(var(--primary-500), 0.3) !important;
}

.page-switcher .p-selectbutton-button.p-highlight:hover {
  background: var(--primary-600) !important;
}
</style>
