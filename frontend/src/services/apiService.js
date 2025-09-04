import axios from 'axios'

const API_BASE_URL = process.env.VUE_APP_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Добавляем токен авторизации к каждому запросу
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Перехватчик ошибок и обработка 401
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error)
    
    // Если 401 - токен недействителен, перенаправляем на логин
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

export default {
  // Авторизация
  async login(credentials) {
    const response = await api.post('/auth/login', credentials)
    return response.data
  },

  async getCurrentUser() {
    const response = await api.get('/auth/me')
    return response.data
  },

  async changePassword(passwordData) {
    const response = await api.post('/auth/change-password', passwordData)
    return response.data
  },

  async logout() {
    const response = await api.post('/auth/logout')
    return response.data
  },

  // Продукты
  getProducts(params = {}) {
    return api.get('/products', { params })
  },

  getFilterOptions() {
    return api.get('/products/filter-options')
  },

  createProduct(product) {
    return api.post('/products', product)
  },

  updateProduct(id, product) {
    return api.put(`/products/${id}`, product)
  },

  deleteProduct(id) {
    return api.delete(`/products/${id}`)
  },

  // Чат
  sendChatQuery(query, history = []) {
    return api.post('/chat/query', { query, history })
  },

  generateReport(query, history = []) {
    return api.post('/chat/generate-report', { query, history })
  },

  // Загрузка файлов
  uploadExcel(file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/excel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  uploadImages(file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/images', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  confirmMapping(file, mapping) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('mapping_data', JSON.stringify({ mapping }))
    return api.post('/upload/confirm-mapping', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // Экспорт данных
  exportProducts(exportData) {
    return api.post('/products/export', exportData, { responseType: 'blob' })
  },

  // Получение колонок БД
  getProductColumns() {
    return api.get('/products/columns')
  },

  // Настройки маппинга
  getMappingSettings() {
    return api.get('/mapping-settings').then(response => response.data)
  },

  createMappingSetting(data) {
    return api.post('/mapping-settings', data).then(response => response.data)
  },

  updateMappingSetting(id, data) {
    return api.put(`/mapping-settings/${id}`, data).then(response => response.data)
  },

  deleteMappingSetting(id) {
    return api.delete(`/mapping-settings/${id}`).then(response => response.data)
  },

  // Управление изображениями и папками
  getImagesAndFolders(path = '/') {
    return api.get('/images/browse', { params: { path } }).then(response => response.data)
  },

  createFolder(parentPath, name) {
    return api.post('/images/folders', { parentPath, name }).then(response => response.data)
  },

  deleteFolder(folderPath) {
    return api.delete('/images/folders', { data: { path: folderPath } }).then(response => response.data)
  },

  renameFolder(oldPath, newName) {
    return api.put('/images/folders/rename', { oldPath, newName }).then(response => response.data)
  },

  uploadImagesToFolder(folderPath, images) {
    const formData = new FormData()
    formData.append('folderPath', folderPath)
    images.forEach((image, index) => {
      formData.append(`images`, image)
    })
    return api.post('/images/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(response => response.data)
  },

  uploadZipToFolder(folderPath, zipFile) {
    const formData = new FormData()
    formData.append('folderPath', folderPath)
    formData.append('zipFile', zipFile)
    return api.post('/images/upload-zip', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(response => response.data)
  },

  deleteImage(imagePath) {
    return api.delete('/images/delete', { data: { path: imagePath } }).then(response => response.data)
  },

  renameImage(oldPath, newName) {
    return api.put('/images/rename', { oldPath, newName }).then(response => response.data)
  },

  exportMappingSettings() {
    return api.get('/mapping-settings/export').then(response => response.data)
  },

  createDefaultMappingSettings() {
    return api.post('/mapping-settings/bulk-create').then(response => response.data)
  },

  // Восстановление базы данных
  restoreDatabase() {
    return api.post('/restore-database')
  }
}
