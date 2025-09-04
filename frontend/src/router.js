import { createRouter, createWebHistory } from 'vue-router'
import ChatPage from './pages/ChatPage.vue'
import FilesPage from './pages/FilesPage.vue'
import DataPage from './pages/DataPage.vue'
import ImagesPage from './pages/ImagesPage.vue'
import LoginPage from './pages/LoginPage.vue'

// Функция проверки авторизации
const isAuthenticated = () => {
  const token = localStorage.getItem('access_token')
  return !!token
}

// Guard для защищенных маршрутов
const authGuard = (to, from, next) => {
  if (isAuthenticated()) {
    next()
  } else {
    next('/login')
  }
}

// Guard для страницы логина
const loginGuard = (to, from, next) => {
  if (isAuthenticated()) {
    next('/chat')
  } else {
    next()
  }
}

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginPage,
    beforeEnter: loginGuard
  },
  {
    path: '/',
    redirect: '/chat'
  },
  {
    path: '/chat',
    name: 'Chat',
    component: ChatPage,
    beforeEnter: authGuard
  },
  {
    path: '/files',
    name: 'Files',
    component: FilesPage,
    beforeEnter: authGuard
  },
  {
    path: '/data',
    name: 'Data',
    component: DataPage,
    beforeEnter: authGuard
  },
  {
    path: '/images',
    name: 'Images',
    component: ImagesPage,
    beforeEnter: authGuard
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
