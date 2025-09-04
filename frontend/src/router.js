import { createRouter, createWebHistory } from 'vue-router'
import ChatPage from './pages/ChatPage.vue'
import FilesPage from './pages/FilesPage.vue'
import DataPage from './pages/DataPage.vue'
import ImagesPage from './pages/ImagesPage.vue'

const routes = [
  {
    path: '/',
    redirect: '/chat'
  },
  {
    path: '/chat',
    name: 'Chat',
    component: ChatPage
  },
  {
    path: '/files',
    name: 'Files',
    component: FilesPage
  },
  {
    path: '/data',
    name: 'Data',
    component: DataPage
  },
  {
    path: '/images',
    name: 'Images',
    component: ImagesPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
