<template>
  <div class="images-page">
    <!-- Хлебные крошки -->
    <div class="grid">
      <div class="col-12">
        <Card>
          <template #content>
            <Breadcrumb :model="breadcrumbItems" class="mb-3">
              <template #item="{ item, props }">
                <a href="#" @click.prevent="navigateBreadcrumb(item)" v-bind="props.action">
                  <span class="text-primary font-semibold">{{ item.label }}</span>
                </a>
              </template>
            </Breadcrumb>
          </template>
        </Card>
      </div>
    </div>

    <!-- Панель инструментов -->
    <div class="grid">
      <div class="col-12">
        <Card>
          <template #content>
            <div class="flex flex-wrap align-items-center justify-content-between gap-3">
              <div class="flex align-items-center gap-2">
                <Button
                  icon="pi pi-folder-plus"
                  label="Создать папку"
                  @click="showCreateFolderDialog = true"
                  size="small"
                />
                <Button
                  icon="pi pi-upload"
                  label="Загрузить изображения"
                  @click="showUploadDialog = true"
                  size="small"
                />
                <Button
                  icon="pi pi-file-upload"
                  label="Загрузить ZIP"
                  @click="showZipUploadDialog = true"
                  size="small"
                />
              </div>
              
              <div class="flex align-items-center gap-2">
                <div class="flex align-items-center gap-1">
                  <Button
                    icon="pi pi-th-large"
                    @click="viewMode = 'grid'"
                    :class="{ 'p-button-secondary': viewMode !== 'grid' }"
                    size="small"
                    text
                  />
                  <Button
                    icon="pi pi-list"
                    @click="viewMode = 'list'"
                    :class="{ 'p-button-secondary': viewMode !== 'list' }"
                    size="small"
                    text
                  />
                </div>
                <InputText
                  v-model="searchQuery"
                  placeholder="Поиск..."
                  class="w-12rem"
                  size="small"
                >
                  <template #prefix>
                    <i class="pi pi-search" />
                  </template>
                </InputText>
              </div>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <!-- Содержимое папок и файлов -->
    <div class="grid">
      <div class="col-12">
        <Card>
          <template #content>
            <!-- Режим сетки -->
            <div v-if="viewMode === 'grid'" class="grid">
              <!-- Кнопка "Назад" -->
              <div v-if="currentPath !== '/'" class="col-6 md:col-4 lg:col-3 xl:col-2">
                <div 
                  class="folder-item p-3 border-round cursor-pointer hover:bg-primary-50 transition-colors"
                  @click="goBack"
                >
                  <div class="text-center">
                    <i class="pi pi-arrow-left text-4xl text-600 mb-2"></i>
                    <div class="text-sm font-medium">Назад</div>
                  </div>
                </div>
              </div>

              <!-- Папки -->
              <div 
                v-for="folder in filteredFolders" 
                :key="folder.id"
                class="col-6 md:col-4 lg:col-3 xl:col-2"
              >
                <div 
                  class="folder-item p-3 border-round cursor-pointer hover:bg-primary-50 transition-colors"
                  @click="openFolder(folder)"
                  @contextmenu="showContextMenu($event, folder, 'folder')"
                >
                  <div class="text-center">
                    <i class="pi pi-folder text-4xl text-orange-500 mb-2"></i>
                    <div class="text-sm font-medium">{{ folder.name }}</div>
                    <div class="text-xs text-500">{{ folder.itemCount }} элементов</div>
                  </div>
                </div>
              </div>

              <!-- Изображения -->
              <div 
                v-for="image in filteredImages" 
                :key="image.id"
                class="col-6 md:col-4 lg:col-3 xl:col-2"
              >
                <div 
                  class="image-item p-3 border-round cursor-pointer hover:bg-primary-50 transition-colors"
                  @click="openImage(image)"
                  @contextmenu="showContextMenu($event, image, 'image')"
                >
                  <div class="text-center">
                    <div class="image-thumbnail mb-2">
                      <img 
                        :src="image.thumbnailUrl || image.url" 
                        :alt="image.name"
                        class="w-full h-full object-cover border-round"
                        @error="handleImageError"
                      />
                    </div>
                    <div class="text-sm font-medium">{{ image.name }}</div>
                    <div class="text-xs text-500">{{ formatFileSize(image.size) }}</div>
                  </div>
                </div>
              </div>

              <!-- Пустая папка -->
              <div v-if="filteredFolders.length === 0 && filteredImages.length === 0" class="col-12">
                <div class="text-center p-6 text-500">
                  <i class="pi pi-folder-open text-6xl mb-3"></i>
                  <div class="text-xl mb-2">Папка пуста</div>
                  <div>Загрузите изображения или создайте новую папку</div>
                </div>
              </div>
            </div>

            <!-- Режим списка -->
            <DataTable v-else :value="allItems" :loading="loading" class="p-datatable-sm">
              <template #empty>
                <div class="text-center p-4">
                  <i class="pi pi-folder-open text-4xl text-500 mb-3"></i>
                  <div>Папка пуста</div>
                </div>
              </template>

              <Column field="icon" header="" style="width: 3rem">
                <template #body="{ data }">
                  <i v-if="data.type === 'folder'" class="pi pi-folder text-orange-500"></i>
                  <img v-else :src="data.thumbnailUrl || data.url" class="w-2rem h-2rem object-cover border-round" />
                </template>
              </Column>

              <Column field="name" header="Название" sortable>
                <template #body="{ data }">
                  <span 
                    class="cursor-pointer hover:text-primary"
                    @click="data.type === 'folder' ? openFolder(data) : openImage(data)"
                  >
                    {{ data.name }}
                  </span>
                </template>
              </Column>

              <Column field="size" header="Размер" sortable>
                <template #body="{ data }">
                  <span v-if="data.type === 'image'">{{ formatFileSize(data.size) }}</span>
                  <span v-else>{{ data.itemCount }} элементов</span>
                </template>
              </Column>

              <Column field="updatedAt" header="Изменено" sortable>
                <template #body="{ data }">
                  {{ formatDate(data.updatedAt) }}
                </template>
              </Column>

              <Column header="Действия" style="width: 8rem">
                <template #body="{ data }">
                  <Button
                    icon="pi pi-ellipsis-v"
                    text
                    size="small"
                    @click="showContextMenu($event, data, data.type)"
                  />
                </template>
              </Column>
            </DataTable>
          </template>
        </Card>
      </div>
    </div>
  </div>

  <!-- Диалог создания папки -->
  <Dialog 
    v-model:visible="showCreateFolderDialog" 
    modal 
    header="Создать папку" 
    :style="{ width: '400px' }"
  >
    <div class="flex flex-column gap-3">
      <div>
        <label for="folderName" class="block text-900 font-medium mb-2">Название папки</label>
        <InputText
          id="folderName"
          v-model="newFolderName"
          placeholder="Введите название..."
          class="w-full"
          @keyup.enter="createFolder"
        />
      </div>
    </div>
    
    <template #footer>
      <Button label="Отмена" text @click="showCreateFolderDialog = false" />
      <Button 
        label="Создать" 
        @click="createFolder" 
        :disabled="!newFolderName.trim()"
      />
    </template>
  </Dialog>

  <!-- Диалог загрузки изображений -->
  <Dialog 
    v-model:visible="showUploadDialog" 
    modal 
    header="Загрузить изображения" 
    :style="{ width: '500px' }"
  >
    <FileUpload
      ref="imageUpload"
      mode="advanced"
      multiple
      accept="image/*"
      @select="onImageSelect"
      @upload="onImageUpload"
      @clear="onImageClear"
    >
      <template #empty>
        <div class="text-center">
          <i class="pi pi-cloud-upload text-4xl text-400"></i>
          <div class="text-600 mt-2">Перетащите изображения сюда или нажмите для выбора</div>
        </div>
      </template>
    </FileUpload>
    
    <template #footer>
      <Button label="Отмена" text @click="showUploadDialog = false" />
      <Button 
        label="Загрузить" 
        @click="uploadImages" 
        :disabled="selectedImages.length === 0"
        :loading="uploading"
      />
    </template>
  </Dialog>

  <!-- Диалог загрузки ZIP -->
  <Dialog 
    v-model:visible="showZipUploadDialog" 
    modal 
    header="Загрузить ZIP архив" 
    :style="{ width: '500px' }"
  >
    <FileUpload
      ref="zipUpload"
      mode="basic"
      accept=".zip"
      chooseLabel="Выбрать ZIP файл"
      @select="onZipSelect"
    />
    
    <template #footer>
      <Button label="Отмена" text @click="showZipUploadDialog = false" />
      <Button 
        label="Загрузить" 
        @click="uploadZip" 
        :disabled="!selectedZipFile"
        :loading="uploading"
      />
    </template>
  </Dialog>

  <!-- Контекстное меню -->
  <ContextMenu ref="contextMenu" :model="contextMenuItems" />

  <!-- Диалог просмотра изображения -->
  <Dialog 
    v-model:visible="showImageDialog" 
    modal 
    :header="selectedImageForView?.name" 
    :style="{ width: '80vw', height: '80vh' }"
    maximizable
  >
    <div v-if="selectedImageForView" class="text-center">
      <img 
        :src="selectedImageForView.url" 
        :alt="selectedImageForView.name"
        class="max-w-full max-h-full"
      />
    </div>
  </Dialog>

  <!-- Диалог переименования -->
  <Dialog 
    v-model:visible="showRenameDialog" 
    modal 
    header="Переименовать" 
    :style="{ width: '400px' }"
  >
    <div class="flex flex-column gap-3">
      <div>
        <label for="newItemName" class="block text-900 font-medium mb-2">
          Новое название {{ itemToRename?.type === 'folder' ? 'папки' : 'файла' }}
        </label>
        <InputText
          id="newItemName"
          v-model="newItemName"
          placeholder="Введите новое название..."
          class="w-full"
          @keyup.enter="confirmRename"
        />
      </div>
    </div>
    
    <template #footer>
      <Button label="Отмена" text @click="showRenameDialog = false" />
      <Button 
        label="Переименовать" 
        @click="confirmRename" 
        :disabled="!newItemName.trim()"
      />
    </template>
  </Dialog>

  <!-- Диалог подтверждения удаления -->
  <Dialog 
    v-model:visible="showDeleteDialog" 
    modal 
    header="Подтверждение удаления" 
    :style="{ width: '400px' }"
  >
    <div class="flex align-items-center gap-3 mb-3">
      <i class="pi pi-exclamation-triangle text-orange-500 text-2xl"></i>
      <div>
        <div class="font-medium text-900 mb-1">
          Вы уверены, что хотите удалить 
          {{ itemToDelete?.type === 'folder' ? 'папку' : 'изображение' }}
          "{{ itemToDelete?.name }}"?
        </div>
        <div class="text-600 text-sm" v-if="itemToDelete?.type === 'folder'">
          Будут удалены все файлы внутри папки. Это действие нельзя отменить.
        </div>
        <div class="text-600 text-sm" v-else>
          Это действие нельзя отменить.
        </div>
      </div>
    </div>
    
    <template #footer>
      <Button label="Отмена" text @click="showDeleteDialog = false" />
      <Button 
        label="Удалить" 
        severity="danger"
        @click="confirmDelete"
      />
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dialog from 'primevue/dialog'
import FileUpload from 'primevue/fileupload'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ContextMenu from 'primevue/contextmenu'
import Breadcrumb from 'primevue/breadcrumb'
import apiService from '../services/apiService'

// Реактивные данные
const toast = useToast()
const viewMode = ref('grid')
const searchQuery = ref('')
const currentPath = ref('/')
const loading = ref(false)

// Данные папок и файлов
const folders = ref([])
const images = ref([])

// Диалоги
const showCreateFolderDialog = ref(false)
const showUploadDialog = ref(false)
const showZipUploadDialog = ref(false)
const showImageDialog = ref(false)
const showRenameDialog = ref(false)
const showDeleteDialog = ref(false)

// Формы
const newFolderName = ref('')
const selectedImages = ref([])
const selectedZipFile = ref(null)
const selectedImageForView = ref(null)
const uploading = ref(false)
const itemToRename = ref(null)
const newItemName = ref('')
const itemToDelete = ref(null)

// Контекстное меню
const contextMenu = ref()
const contextMenuItems = ref([])

// Хлебные крошки
const breadcrumbItems = computed(() => {
  const items = [{ label: 'Корневая папка', path: '/' }]
  if (currentPath.value !== '/') {
    const parts = currentPath.value.split('/').filter(Boolean)
    parts.forEach((part, idx) => {
      const path = '/' + parts.slice(0, idx + 1).join('/')
      items.push({ label: part, path })
    })
  }
  return items
})

const navigateBreadcrumb = (item) => {
  if (item?.path != null) {
    currentPath.value = item.path
    loadData()
  }
}

// Фильтрованные данные
const filteredFolders = computed(() => {
  if (!searchQuery.value) return folders.value
  
  return folders.value.filter(folder => 
    folder.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const filteredImages = computed(() => {
  if (!searchQuery.value) return images.value
  
  return images.value.filter(image => 
    image.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const allItems = computed(() => {
  const items = []
  
  if (currentPath.value !== '/') {
    items.push({
      type: 'back',
      name: '...',
      icon: 'pi pi-arrow-left'
    })
  }
  
  filteredFolders.value.forEach(folder => {
    items.push({ ...folder, type: 'folder' })
  })
  
  filteredImages.value.forEach(image => {
    items.push({ ...image, type: 'image' })
  })
  
  return items
})

// Методы
const loadData = async () => {
  loading.value = true
  console.log('🔄 Загружаем данные для пути:', currentPath.value)
  
  try {
    const response = await apiService.getImagesAndFolders(currentPath.value)
    console.log('✅ Ответ API:', response)
    folders.value = response.folders || []
    images.value = response.images || []
    console.log('📁 Папки:', folders.value.length, '🖼️ Изображения:', images.value.length)
  } catch (error) {
    console.error('❌ Ошибка загрузки данных:', error)
    
    toast.add({
      severity: 'error',
      summary: 'Ошибка',
      detail: 'Не удалось загрузить данные'
    })
    
    // Очищаем данные при ошибке
    folders.value = []
    images.value = []
  } finally {
    loading.value = false
    console.log('✨ Загрузка завершена')
  }
}

const openFolder = (folder) => {
  currentPath.value = folder.path
  loadData()
}

const goBack = () => {
  const pathParts = currentPath.value.split('/').filter(part => part)
  pathParts.pop()
  currentPath.value = pathParts.length > 0 ? '/' + pathParts.join('/') : '/'
  loadData()
}

const openImage = (image) => {
  selectedImageForView.value = image
  showImageDialog.value = true
}

const createFolder = async () => {
  if (!newFolderName.value.trim()) return
  
  try {
    await apiService.createFolder(currentPath.value, newFolderName.value.trim())
    toast.add({
      severity: 'success',
      summary: 'Успех',
      detail: 'Папка создана'
    })
    newFolderName.value = ''
    showCreateFolderDialog.value = false
    loadData()
  } catch (error) {
    console.error('Ошибка создания папки:', error)
    toast.add({
      severity: 'error',
      summary: 'Ошибка',
      detail: 'Не удалось создать папку'
    })
  }
}

const onImageSelect = (event) => {
  selectedImages.value = event.files
}

const onImageClear = () => {
  selectedImages.value = []
}

const uploadImages = async () => {
  if (selectedImages.value.length === 0) return
  
  uploading.value = true
  try {
    await apiService.uploadImagesToFolder(currentPath.value, selectedImages.value)
    toast.add({
      severity: 'success',
      summary: 'Успех',
      detail: `Загружено ${selectedImages.value.length} изображений`
    })
    selectedImages.value = []
    showUploadDialog.value = false
    loadData()
  } catch (error) {
    console.error('Ошибка загрузки изображений:', error)
    toast.add({
      severity: 'error',
      summary: 'Ошибка',
      detail: 'Не удалось загрузить изображения'
    })
  } finally {
    uploading.value = false
  }
}

const onZipSelect = (event) => {
  selectedZipFile.value = event.files[0]
}

const uploadZip = async () => {
  if (!selectedZipFile.value) return
  
  uploading.value = true
  try {
    await apiService.uploadZipToFolder(currentPath.value, selectedZipFile.value)
    toast.add({
      severity: 'success',
      summary: 'Успех',
      detail: 'ZIP архив загружен'
    })
    selectedZipFile.value = null
    showZipUploadDialog.value = false
    loadData()
  } catch (error) {
    console.error('Ошибка загрузки ZIP:', error)
    toast.add({
      severity: 'error',
      summary: 'Ошибка',
      detail: 'Не удалось загрузить ZIP архив'
    })
  } finally {
    uploading.value = false
  }
}

const showContextMenu = (event, item, type) => {
  const items = []
  
  // Добавляем тип к элементу для последующего использования
  const itemWithType = { ...item, type }
  
  if (type === 'folder') {
    items.push(
      { label: 'Открыть', icon: 'pi pi-folder-open', command: () => openFolder(itemWithType) },
      { label: 'Переименовать', icon: 'pi pi-pencil', command: () => renameItem(itemWithType) },
      { separator: true },
      { label: 'Удалить', icon: 'pi pi-trash', command: () => deleteItem(itemWithType) }
    )
  } else if (type === 'image') {
    items.push(
      { label: 'Просмотр', icon: 'pi pi-eye', command: () => openImage(itemWithType) },
      { label: 'Скачать', icon: 'pi pi-download', command: () => downloadImage(itemWithType) },
      { label: 'Переименовать', icon: 'pi pi-pencil', command: () => renameItem(itemWithType) },
      { separator: true },
      { label: 'Удалить', icon: 'pi pi-trash', command: () => deleteItem(itemWithType) }
    )
  }
  
  contextMenuItems.value = items
  contextMenu.value.show(event)
}

const renameItem = (item) => {
  itemToRename.value = item
  newItemName.value = item.name
  showRenameDialog.value = true
}

const confirmRename = async () => {
  if (!itemToRename.value || !newItemName.value.trim()) return
  
  try {
    if (itemToRename.value.type === 'folder') {
      await apiService.renameFolder(itemToRename.value.path, newItemName.value.trim())
      toast.add({
        severity: 'success',
        summary: 'Успех',
        detail: 'Папка переименована'
      })
    } else {
      await apiService.renameImage(itemToRename.value.path, newItemName.value.trim())
      toast.add({
        severity: 'success',
        summary: 'Успех',
        detail: 'Изображение переименовано'
      })
    }
    
    showRenameDialog.value = false
    itemToRename.value = null
    newItemName.value = ''
    loadData()
  } catch (error) {
    console.error('Ошибка переименования:', error)
    toast.add({
      severity: 'error',
      summary: 'Ошибка',
      detail: 'Не удалось переименовать'
    })
  }
}

const deleteItem = (item) => {
  itemToDelete.value = item
  showDeleteDialog.value = true
}

const confirmDelete = async () => {
  if (!itemToDelete.value) return
  
  try {
    if (itemToDelete.value.type === 'folder') {
      await apiService.deleteFolder(itemToDelete.value.path)
      toast.add({
        severity: 'success',
        summary: 'Успех',
        detail: 'Папка удалена'
      })
    } else {
      await apiService.deleteImage(itemToDelete.value.path)
      toast.add({
        severity: 'success',
        summary: 'Успех',
        detail: 'Изображение удалено'
      })
    }
    
    showDeleteDialog.value = false
    itemToDelete.value = null
    loadData()
  } catch (error) {
    console.error('Ошибка удаления:', error)
    toast.add({
      severity: 'error',
      summary: 'Ошибка',
      detail: 'Не удалось удалить'
    })
  }
}

const downloadImage = (image) => {
  const link = document.createElement('a')
  link.href = image.url
  link.download = image.name
  link.click()
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (date) => {
  return new Date(date).toLocaleString('ru-RU')
}

const handleImageError = (event) => {
  event.target.src = '/placeholder-image.png' // Заглушка
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.images-page {
  padding: 1rem;
}

.folder-item,
.image-item {
  border: 1px solid var(--surface-border);
  transition: all 0.2s;
}

.folder-item:hover,
.image-item:hover {
  border-color: var(--primary-color);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.image-thumbnail {
  border: 1px solid var(--surface-border);
  border-radius: 4px;
  overflow: hidden;
  width: 100%;
  height: 6rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-thumbnail img {
  transition: transform 0.2s;
}

.image-item:hover .image-thumbnail img {
  transform: scale(1.05);
}

:deep(.p-fileupload-content) {
  border: 2px dashed var(--surface-border);
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
}

:deep(.p-fileupload-content:hover) {
  border-color: var(--primary-color);
}
</style>
