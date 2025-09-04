<template>
  <div id="app" class="min-h-screen">
    <!-- Современный хедер с переключателем -->
    <header class="app-header p-4 border-b border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900">
      <div class="flex justify-content-between align-items-center max-w-4xl mx-auto">
        <h1 class="m-0 text-xl font-bold text-surface-900 dark:text-surface-0">
          AI База Данных Очков
        </h1>
        
        <!-- Переключатель страниц -->
        <SelectButton 
          v-model="selectedPage" 
          :options="pageOptions" 
          option-label="label"
          option-value="value"
          @change="onPageChange"
          class="page-switcher"
        />
      </div>
    </header>

    <div class="app-content">
      <router-view />
    </div>

    <Toast />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SelectButton from 'primevue/selectbutton'
import Toast from 'primevue/toast'

export default {
  name: 'App',
  components: {
    SelectButton,
    Toast
  },
  setup() {
    const router = useRouter()
    const route = useRoute()
    const selectedPage = ref('chat')

    const pageOptions = ref([
      {
        label: 'Чат',
        value: 'chat',
        icon: 'pi pi-comments'
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

    const onPageChange = (event) => {
      const value = event.value
      if (value === 'chat') {
        router.push('/chat')
      } else if (value === 'data') {
        router.push('/data')
      } else if (value === 'images') {
        router.push('/images')
      }
    }

    // Устанавливаем активную страницу при загрузке
    onMounted(() => {
      const currentPath = route.path
      if (currentPath.includes('/data')) {
        selectedPage.value = 'data'
      } else if (currentPath.includes('/images')) {
        selectedPage.value = 'images'
      } else {
        selectedPage.value = 'chat'
      }
    })

    return {
      selectedPage,
      pageOptions,
      onPageChange
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
