<template>
  <div class="login-page">
    <div class="login-container">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 mb-2">
          Авторизация
        </h1>
        <p class="text-surface-600 dark:text-surface-400">
          AI База Данных Очков
        </p>
      </div>

      <form @submit.prevent="onSubmit" class="login-form">
        <!-- Поле имени -->
        <div class="input-container">
          <InputText
            id="username"
            v-model="username"
            type="text"
            placeholder="Имя пользователя"
            :invalid="!!errors.username"
            autofocus
            class="login-input"
          />
          <small v-if="errors.username" class="error-message">
            {{ errors.username }}
          </small>
        </div>

        <!-- Поле пароля -->
        <div class="input-container">
          <Password
            id="password"
            v-model="password"
            placeholder="Пароль"
            :invalid="!!errors.password"
            :feedback="false"
            toggleMask
            class="login-input"
          />
          <small v-if="errors.password" class="error-message">
            {{ errors.password }}
          </small>
        </div>

        <!-- Общая ошибка -->
        <div v-if="generalError" class="error-container">
          <Message severity="error" :closable="false">
            {{ generalError }}
          </Message>
        </div>

        <!-- Кнопка входа -->
        <Button
          type="submit"
          label="Вход"
          :loading="loading"
          class="login-button"
        />
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import apiService from '../services/apiService'

// Локальная регистрация компонентов PrimeVue
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'

const router = useRouter()
const toast = useToast()

// Реактивные данные
const username = ref('')
const password = ref('')
const loading = ref(false)
const generalError = ref('')

// Ошибки валидации
const errors = reactive({
  username: '',
  password: ''
})

// Валидация формы
const validateForm = () => {
  errors.username = ''
  errors.password = ''
  
  let isValid = true

  if (!username.value.trim()) {
    errors.username = 'Логин обязателен для заполнения'
    isValid = false
  }

  if (!password.value.trim()) {
    errors.password = 'Пароль обязателен для заполнения'
    isValid = false
  } else if (password.value.length < 3) {
    errors.password = 'Пароль должен содержать минимум 3 символа'
    isValid = false
  }

  return isValid
}

// Обработка отправки формы
const onSubmit = async () => {
  generalError.value = ''
  
  if (!validateForm()) {
    return
  }

  loading.value = true

  try {
    const response = await apiService.login({
      username: username.value,
      password: password.value
    })

    // Сохраняем токен
    localStorage.setItem('access_token', response.access_token)
    
    toast.add({
      severity: 'success',
      summary: 'Успех',
      detail: 'Успешная авторизация',
      life: 3000
    })

    // Получаем информацию о пользователе
    const userInfo = await apiService.getCurrentUser()
    localStorage.setItem('user_info', JSON.stringify(userInfo))

    // Перенаправляем на главную страницу
    router.push('/chat')
    
  } catch (error) {
    console.error('Login error:', error)
    
    if (error.response?.status === 401) {
      generalError.value = 'Неверный логин или пароль'
    } else {
      generalError.value = 'Произошла ошибка при входе. Попробуйте снова.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Обертка страницы: центрирование по вертикали и горизонтали */
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: var(--surface-ground);
}

.login-container {
  width: 100%;
  max-width: 400px;
  padding: 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.dark-mode .login-container {
  background: rgb(31, 41, 55);
}

.login-form {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
}

.input-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.login-input {
  width: 300px;
  height: 48px;
  font-size: 16px;
}

:deep(.p-inputtext) {
  width: 300px !important;
  height: 48px !important;
  font-size: 16px !important;
  text-align: center;
}

:deep(.p-password) {
  width: 300px !important;
}

:deep(.p-password .p-inputtext) {
  width: 100% !important;
  height: 48px !important;
  font-size: 16px !important;
  text-align: center;
}

.login-button {
  width: 150px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  margin-top: 0.5rem;
}

:deep(.p-button) {
  width: 150px !important;
  height: 48px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
}

.error-message {
  color: #ef4444;
  font-size: 12px;
  margin-top: 4px;
  text-align: center;
}

.error-container {
  width: 100%;
  text-align: center;
}

/* Медиа-запросы для адаптивности */
@media (max-width: 480px) {
  .login-container {
    max-width: 90%;
    padding: 1.5rem;
  }
  
  .login-input,
  :deep(.p-inputtext),
  :deep(.p-password) {
    width: 250px !important;
  }
  
  .login-button,
  :deep(.p-button) {
    width: 125px !important;
  }
}
</style>
