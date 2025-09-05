<template>
  <div class="chat-page">
    <!-- Основной чат контейнер -->
    <div class="chat-container">
      <!-- Область сообщений -->
      <ScrollPanel class="messages-scroll" ref="messagesContainer">
        <div class="messages-content">
          <div
            v-for="(message, index) in messages"
            :key="index"
            :class="['message-wrapper', message.type]"
          >
            <div class="message-bubble">
              <!-- Сообщение пользователя -->
              <div v-if="message.type === 'user'" class="user-message">
                <div class="message-avatar">
                  <i class="pi pi-user"></i>
                </div>
                <div class="message-content">
                  <div class="message-text">{{ message.text }}</div>
                </div>
              </div>
              
              <!-- Сообщение ИИ -->
              <div v-else class="ai-message">
                <div class="message-avatar">
                  <i class="pi pi-sparkles"></i>
                </div>
                <div class="message-content">
                  <!-- SQL запрос если есть -->
                  <div v-if="message.sql" class="sql-block mb-3">
                    <div class="sql-header">
                      <i class="pi pi-code"></i>
                      <span>SQL запрос</span>
                    </div>
                    <div class="sql-code">{{ message.sql }}</div>
                  </div>
                  
                  <!-- Результаты в виде таблицы -->
                  <!-- Единичное значение (например, COUNT) -->
                  <div v-if="isSingleValue(message.results)" class="text-result">
                    {{ formatSingleValue(message.results) }}
                  </div>

                  <!-- Массив результатов в виде таблицы -->
                  <div v-else-if="message.results && Array.isArray(message.results) && message.results.length > 0" class="results-table-container">
                    <div class="table-scroll-wrapper">
                      <DataTable
                        :value="message.results"
                        :paginator="message.results.length > 5"
                        :rows="5"
                        class="modern-table"
                        responsiveLayout="scroll"
                        :scrollable="true"
                        scrollHeight="400px"
                      >
                        <Column
                          v-for="col in Object.keys(message.results[0] || {})"
                          :key="col"
                          :field="col"
                          :header="col"
                          :sortable="true"
                          :style="{ minWidth: '120px' }"
                        />
                      </DataTable>
                    </div>
                  </div>
                  
                  <!-- Текстовый результат -->
                  <div v-else-if="message.results" class="text-result">
                    {{ Array.isArray(message.results) ? message.results[0]?.message || 'Запрос выполнен' : message.results }}
                  </div>
                  
                  <!-- Обычное текстовое сообщение -->
                  <div v-else-if="message.text" class="message-text">
                    {{ message.text }}
                  </div>
                  
                  <!-- Ошибка -->
                  <div v-if="message.error" class="error-message">
                    <i class="pi pi-exclamation-triangle"></i>
                    <span>{{ message.error }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Индикатор загрузки -->
          <div v-if="isLoading" class="loading-message">
            <div class="message-wrapper ai">
              <div class="message-bubble">
                <div class="ai-message">
                  <div class="message-avatar">
                    <i class="pi pi-sparkles"></i>
                  </div>
                  <div class="message-content">
                    <div class="typing-indicator">
                      <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                      <span class="typing-text">Обрабатываю запрос...</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </ScrollPanel>
    </div>

    <!-- Поле ввода внизу -->
    <div class="input-area">
      <div class="input-container">
        <div class="input-wrapper">
          <Textarea
            v-model="currentQuery"
            placeholder="Введите запрос на естественном языке..."
            autoResize
            :rows="1"
            class="chat-input"
            @keydown.enter.exact.prevent="sendQuery"
            @keydown.enter.shift.exact="addNewLine"
            :disabled="isLoading"
            variant="outlined"
            fluid
          />
          <Button
            :icon="isLoading ? 'pi pi-spinner pi-spin' : 'pi pi-send'"
            class="send-button"
            @click="sendQuery"
            :disabled="isLoading || !currentQuery.trim()"
            size="small"
            rounded
          />
        </div>
        <div class="input-footer">
          <div class="input-footer-row">
            <small class="text-muted">
              Нажмите Enter для отправки, Shift+Enter для новой строки
            </small>
            <Button
              label="Очистить историю"
              text
              size="small"
              @click="clearHistory"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, nextTick, onMounted } from 'vue'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ScrollPanel from 'primevue/scrollpanel'
import apiService from '../services/apiService'

export default {
  name: 'ChatPage',
  components: {
    Textarea,
    Button,
    DataTable,
    Column,
    ScrollPanel
  },
  setup() {
    const messages = ref([])
    const currentQuery = ref('')
    const isLoading = ref(false)
    const messagesContainer = ref(null)

    // Ключ хранения истории чата для текущего пользователя
    const getStorageKey = () => {
      try {
        const userInfo = JSON.parse(localStorage.getItem('user_info') || 'null')
        const username = userInfo?.username || userInfo?.login || 'guest'
        return `chat_history_${username}`
      } catch {
        return 'chat_history_guest'
      }
    }

    // Сохраняем последние 10 сообщений (с небольшим превью результатов)
    const saveHistory = () => {
      const MAX_ROWS = 50
      const MAX_COLS = 50
      const lightMessages = messages.value.slice(-10).map(m => {
        const item = {
          type: m.type,
          text: m.text || '',
          sql: m.sql || '',
          error: m.error || ''
        }
        if (Array.isArray(m.results) && m.results.length > 0) {
          // Сохраняем урезанную копию результатов
          const sliced = m.results.slice(0, MAX_ROWS).map(row => {
            if (row && typeof row === 'object') {
              const entries = Object.entries(row).slice(0, MAX_COLS)
              return Object.fromEntries(entries)
            }
            return row
          })
          item.results = sliced
        }
        return item
      })
      localStorage.setItem(getStorageKey(), JSON.stringify(lightMessages))
    }

  // Загружаем историю из localStorage (fallback)
  const loadLocalHistory = () => {
      try {
        const raw = localStorage.getItem(getStorageKey())
        if (!raw) return []
        const arr = JSON.parse(raw)
        return Array.isArray(arr) ? arr.slice(-10) : []
      } catch {
        return []
      }
    }

    const clearHistory = async () => {
  localStorage.removeItem(getStorageKey())
  // Пытаемся очистить серверную историю (не блокируем и не показываем ошибку)
  apiService.clearChatHistory().catch(() => {})
      messages.value = [
        {
          type: 'ai',
          text:
            'Привет! Я ИИ-ассистент для работы с базой данных очков. Задайте вопрос на естественном языке, и я помогу вам найти нужную информацию. Например: "Найди солнцезащитные очки Gucci" или "Покажи все женские оправы Ray-Ban".'
        }
      ]
      await nextTick()
      await scrollToBottom()
    }

    const sendQuery = async () => {
      if (!currentQuery.value.trim() || isLoading.value) return

      const query = currentQuery.value.trim()
      messages.value.push({ type: 'user', text: query })
      currentQuery.value = ''
      isLoading.value = true
  saveHistory()
  // Отправляем сообщение пользователя в серверную историю (не блокируем UX)
  apiService.addChatMessage({ role: 'user', text: query }).catch(() => {})

      try {
        // Собираем историю предыдущих запросов пользователя (последние 3)
        const userMessages = messages.value
          .filter(msg => msg.type === 'user')
          .map(msg => msg.text)
          .slice(-3) // Берем последние 3

        const response = await apiService.sendChatQuery(query, userMessages)
        messages.value.push({
          type: 'ai',
          sql: response.data.sql,
          results: response.data.results,
          error: response.data.error
        })
        saveHistory()
        // Сохраняем ответ ИИ на сервере
        const aiPayload = {
          role: 'ai',
          sql: response.data.sql || undefined,
          text: (!response.data.sql && Array.isArray(response.data.results)) ? (response.data.results[0]?.message || 'Запрос выполнен') : undefined,
          error: response.data.error || undefined,
          results: Array.isArray(response.data.results) && response.data.results.length > 0 ? response.data.results : undefined
        }
        apiService.addChatMessage(aiPayload).catch(() => {})
      } catch (error) {
        messages.value.push({
          type: 'ai',
          error: 'Ошибка при обработке запроса'
        })
        saveHistory()
        apiService.addChatMessage({ role: 'ai', error: 'Ошибка при обработке запроса' }).catch(() => {})
      } finally {
        isLoading.value = false
        await scrollToBottom()
      }
    }

    const addNewLine = () => {
      currentQuery.value += '\n'
    }

    // Детектируем и форматируем 1x1 результат (например COUNT)
    const isSingleValue = (results) => {
      if (!Array.isArray(results) || results.length !== 1) return false
      const row = results[0]
      if (!row || typeof row !== 'object') return false
      const keys = Object.keys(row)
      return keys.length === 1
    }

    const formatSingleValue = (results) => {
      if (!isSingleValue(results)) return ''
      const row = results[0]
      const key = Object.keys(row)[0]
      return row[key]
    }

    const scrollToBottom = async () => {
      await nextTick()
      if (messagesContainer.value) {
        const scrollPanel = messagesContainer.value.$el
        const content = scrollPanel.querySelector('.p-scrollpanel-content')
        if (content) {
          content.scrollTop = content.scrollHeight
        }
      }
    }

    onMounted(async () => {
      // Пытаемся загрузить историю с сервера
      let loaded = false
      try {
        const { data } = await apiService.getChatHistory(10)
        if (Array.isArray(data) && data.length > 0) {
          messages.value = data.map(item => ({
            type: item.role,
            text: item.text || undefined,
            sql: item.sql || undefined,
            error: item.error || undefined,
            results: Array.isArray(item.results) ? item.results : undefined
          }))
          // Попробуем дополнить отсутствующие results из локального кеша
          const local = loadLocalHistory()
          if (Array.isArray(local) && local.length) {
            for (let i = 0; i < messages.value.length; i++) {
              const m = messages.value[i]
              if (m.type === 'ai' && m.sql && (!Array.isArray(m.results) || m.results.length === 0)) {
                // ищем похожее сообщение по sql в локальном кеше, начиная с конца
                for (let j = local.length - 1; j >= 0; j--) {
                  const lm = local[j]
                  if (lm.type === 'ai' && lm.sql === m.sql && Array.isArray(lm.results) && lm.results.length > 0) {
                    m.results = lm.results
                    break
                  }
                }
              }
            }
          }
          loaded = true
          saveHistory() // синхронизируем локальный кеш
        }
      } catch (e) {}

      if (!loaded) {
        const restored = loadLocalHistory()
        if (restored.length > 0) {
          messages.value = restored
        } else {
          messages.value.push({
            type: 'ai',
            text:
              'Привет! Я ИИ-ассистент для работы с базой данных очков. Задайте вопрос на естественном языке, и я помогу вам найти нужную информацию. Например: "Найди солнцезащитные очки Gucci" или "Покажи все женские оправы Ray-Ban".'
          })
        }
      }
      await nextTick()
      await scrollToBottom()
    })

    return {
      messages,
      currentQuery,
      isLoading,
      messagesContainer,
      sendQuery,
      addNewLine,
  clearHistory,
  isSingleValue,
  formatSingleValue
    }
  }
}
</script>

<style scoped>
.chat-page {
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  background: var(--surface-ground);
  max-width: 1200px;
  margin: 0 auto;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  overflow-x: hidden; /* Запрещаем горизонтальный скролл у контейнера чата */
}

.messages-scroll {
  flex: 1;
  width: 100%;
  height: 100%;
  overflow-x: hidden; /* Горизонтальная прокрутка только внутри таблиц */
}

.messages-content {
  padding: 2rem 1rem 1rem;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
  overflow-x: hidden; /* Не даем сообщениям расширять страницу по X */
}

.message-wrapper {
  margin-bottom: 2rem;
  display: flex;
  flex-direction: column;
}

.message-wrapper.user {
  align-items: flex-end;
}

.message-wrapper.ai {
  align-items: flex-start;
}

.message-bubble {
  max-width: 100%;
  width: 100%;
}

/* Сообщения пользователя */
.user-message {
  display: flex;
  gap: 0.75rem;
  flex-direction: row-reverse;
  max-width: 80%;
  margin-left: auto;
}

.user-message .message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.user-message .message-content {
  /* Яркий фон и контрастный текст, чтобы не было "белое на белом" */
  background: var(--primary-600, #3b82f6) !important;
  color: #ffffff !important;
  padding: 1rem 1.25rem;
  border-radius: 1.5rem 1.5rem 0.5rem 1.5rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.user-message .message-text {
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  color: #ffffff !important; /* Гарантируем читаемость текста в пузыре пользователя */
}

/* Сообщения ИИ */
.ai-message {
  display: flex;
  gap: 0.75rem;
  max-width: 100%;
}

.ai-message .message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--blue-500), var(--purple-500));
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.875rem;
  flex-shrink: 0;
  margin-top: 0.25rem;
}

.ai-message .message-content {
  background: var(--surface-0);
  border: 1px solid var(--surface-200);
  padding: 1.25rem;
  border-radius: 1.5rem 1.5rem 1.5rem 0.5rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  flex: 1;
  overflow: hidden; /* Контент ИИ не должен раздвигать пузырь */
}

.dark-mode .ai-message .message-content {
  background: var(--surface-800);
  border-color: var(--surface-700);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.message-text {
  line-height: 1.6;
  color: var(--text-color);
  white-space: pre-wrap;
  word-break: break-word;
}

/* SQL блок */
.sql-block {
  background: var(--surface-50);
  border: 1px solid var(--surface-200);
  border-radius: 0.75rem;
  overflow: hidden;
  margin-bottom: 1rem;
}

.dark-mode .sql-block {
  background: var(--surface-900);
  border-color: var(--surface-700);
}

.sql-header {
  background: var(--surface-100);
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-color-secondary);
  border-bottom: 1px solid var(--surface-200);
}

.dark-mode .sql-header {
  background: var(--surface-800);
  border-color: var(--surface-700);
}

.sql-code {
  padding: 1rem;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--text-color);
  white-space: pre-wrap;
  word-break: break-all;
}

/* Таблица результатов */
.results-table-container {
  margin-top: 1rem;
  max-width: 100%;
  overflow: hidden; /* Контейнер остается размера чата */
  border-radius: 0.75rem;
  border: 1px solid var(--surface-200);
  background: var(--surface-0);
}

.dark-mode .results-table-container {
  border-color: var(--surface-700);
  background: var(--surface-800);
}

.table-scroll-wrapper {
  max-height: 400px;
  overflow: auto; /* Горизонтальная и вертикальная прокрутка только внутри */
  position: relative;
  width: 100%;
  display: block;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.modern-table {
  border-radius: 0;
  border: none;
  width: max-content; /* Таблица может быть шире контейнера */
  min-width: 100%;   /* но не уже контейнера, чтобы не было схлопывания */
}

/* Внутренний контейнер PrimeVue таблицы не должен раздвигать чат */
.table-scroll-wrapper .p-datatable-table-container {
  width: max-content;
  min-width: 100%;
}

/* Стили скроллбара для таблицы */
.table-scroll-wrapper::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.table-scroll-wrapper::-webkit-scrollbar-track {
  background: var(--surface-100);
  border-radius: 4px;
}

.table-scroll-wrapper::-webkit-scrollbar-thumb {
  background: var(--surface-400);
  border-radius: 4px;
}

.table-scroll-wrapper::-webkit-scrollbar-thumb:hover {
  background: var(--surface-500);
}

.table-scroll-wrapper::-webkit-scrollbar-corner {
  background: var(--surface-100);
}

.dark-mode .table-scroll-wrapper::-webkit-scrollbar-track {
  background: var(--surface-700);
}

.dark-mode .table-scroll-wrapper::-webkit-scrollbar-thumb {
  background: var(--surface-600);
}

.dark-mode .table-scroll-wrapper::-webkit-scrollbar-thumb:hover {
  background: var(--surface-500);
}

.dark-mode .table-scroll-wrapper::-webkit-scrollbar-corner {
  background: var(--surface-700);
}

/* Текстовый результат */
.text-result {
  background: var(--green-50);
  border: 1px solid var(--green-200);
  color: var(--green-700);
  padding: 1rem;
  border-radius: 0.75rem;
  font-weight: 500;
}

.dark-mode .text-result {
  background: var(--green-900);
  border-color: var(--green-700);
  color: var(--green-200);
}

/* Ошибка */
.error-message {
  background: var(--red-50);
  border: 1px solid var(--red-200);
  color: var(--red-700);
  padding: 1rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
}

.dark-mode .error-message {
  background: var(--red-900);
  border-color: var(--red-700);
  color: var(--red-200);
}

/* Индикатор набора текста */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.typing-dots {
  display: flex;
  gap: 0.25rem;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-color);
  animation: typing 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

.typing-text {
  color: var(--text-color-secondary);
  font-style: italic;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Область ввода */
.input-area {
  background: var(--surface-0);
  border-top: 1px solid var(--surface-200);
  padding: 1.5rem;
  backdrop-filter: blur(8px);
  background: rgba(var(--surface-0), 0.95);
}

.dark-mode .input-area {
  background: rgba(var(--surface-900), 0.95);
  border-color: var(--surface-700);
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
  background: var(--surface-50);
  border: 2px solid var(--surface-200);
  border-radius: 1.5rem;
  padding: 0.5rem;
  transition: all 0.2s ease;
}

.dark-mode .input-wrapper {
  background: var(--surface-800);
  border-color: var(--surface-700);
}

.input-wrapper:focus-within {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(var(--primary-500), 0.1);
}

.chat-input {
  flex: 1;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0.75rem 1rem !important;
  font-size: 1rem !important;
  line-height: 1.5 !important;
  resize: none !important;
  max-height: 120px;
  min-height: 48px;
  color: #1f2937 !important; /* Темно-серый цвет текста */
  background-color: #ffffff !important; /* Белый фон */
}

.chat-input::placeholder {
  color: #6b7280 !important; /* Серый цвет для placeholder */
  opacity: 0.7;
}

.dark-mode .chat-input {
  color: #e5e7eb !important; /* Светлый цвет для темной темы */
  background-color: #374151 !important; /* Темный фон для темной темы */
}

.dark-mode .chat-input::placeholder {
  color: #9ca3af !important; /* Светло-серый для placeholder в темной теме */
}

.chat-input:focus {
  outline: none !important;
  box-shadow: none !important;
}

.send-button {
  width: 40px;
  height: 40px;
  border-radius: 50% !important;
  background: var(--primary-color) !important;
  border: none !important;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.send-button:enabled:hover {
  background: var(--primary-600) !important;
  transform: scale(1.05);
}

.send-button:disabled {
  background: var(--surface-300) !important;
  color: var(--surface-500) !important;
  cursor: not-allowed;
}

.dark-mode .send-button:disabled {
  background: var(--surface-600) !important;
  color: var(--surface-400) !important;
}

.input-footer {
  margin-top: 0.5rem;
  text-align: center;
}

.text-muted {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.input-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Мобильная адаптивность */
@media (max-width: 768px) {
  .messages-content {
    padding: 1rem 0.75rem;
  }
  
  .user-message,
  .ai-message {
    max-width: 100%;
  }
  
  .input-area {
    padding: 1rem;
  }
  
  .message-bubble {
    width: 100%;
  }
}

/* Скрытие скроллбара для Chrome, Safari */
.messages-scroll ::-webkit-scrollbar {
  width: 6px;
}

.messages-scroll ::-webkit-scrollbar-track {
  background: transparent;
}

.messages-scroll ::-webkit-scrollbar-thumb {
  background: var(--surface-400);
  border-radius: 3px;
}

.messages-scroll ::-webkit-scrollbar-thumb:hover {
  background: var(--surface-500);
}

.dark-mode .messages-scroll ::-webkit-scrollbar-thumb {
  background: var(--surface-600);
}

.dark-mode .messages-scroll ::-webkit-scrollbar-thumb:hover {
  background: var(--surface-500);
}
</style>
             