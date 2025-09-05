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
                
                <!-- Инструменты множественного выбора -->
                <div v-if="selectedItems.length > 0" class="flex align-items-center gap-2 ml-3">
                  <Divider layout="vertical" />
                  <span class="text-sm text-600">Выбрано: {{ selectedItems.length }}</span>
                  <Button
                    icon="pi pi-trash"
                    label="Удалить выбранные"
                    @click="confirmBulkDelete"
                    severity="danger"
                    size="small"
                  />
                  <Button
                    icon="pi pi-times"
                    label="Снять выделение"
                    @click="clearSelection"
                    text
                    size="small"
                  />
                </div>
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
            <div v-if="viewMode === 'grid'" ref="gridContainer" class="grid-container" @mousedown="startSelectionRectangle">
              <div class="grid">
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
                  :ref="el => setItemRef(el, folder, 'folder')"
                >
                  <div 
                    class="selectable-item folder-item p-3 border-round cursor-pointer transition-colors"
                    :class="{ 
                      'bg-primary-100 border-primary': isSelected(folder, 'folder'),
                      'hover:bg-primary-50': !isSelected(folder, 'folder')
                    }"
                    @click="handleItemClick(folder, 'folder', $event)"
                    @contextmenu="showContextMenu($event, folder, 'folder')"
                    @dragstart="handleDragStart($event, folder, 'folder')"
                    @dragover="handleDragOver"
                    @drop="handleDrop($event, folder)"
                    draggable="true"
                  >
                    <div class="text-center">
                      <div class="relative">
                        <i class="pi pi-folder text-4xl text-orange-500 mb-2"></i>
                        <div 
                          v-if="isSelected(folder, 'folder')" 
                          class="selection-indicator"
                        >
                          ✓
                        </div>
                      </div>
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
                  :ref="el => setItemRef(el, image, 'image')"
                >
                  <div 
                    class="selectable-item image-item p-3 border-round cursor-pointer transition-colors"
                    :class="{ 
                      'bg-primary-100 border-primary': isSelected(image, 'image'),
                      'hover:bg-primary-50': !isSelected(image, 'image')
                    }"
                    @click="handleItemClick(image, 'image', $event)"
                    @contextmenu="showContextMenu($event, image, 'image')"
                    @dragstart="handleDragStart($event, image, 'image')"
                    draggable="true"
                  >
                    <div class="text-center">
                      <div class="relative">
                        <div class="image-thumbnail mb-2">
                          <img 
                            :src="image.thumbnailUrl || image.url" 
                            :alt="image.name"
                            class="w-full h-full object-cover border-round"
                            @error="handleImageError"
                          />
                        </div>
                        <div 
                          v-if="isSelected(image, 'image')" 
                          class="selection-indicator"
                        >
                          ✓
                        </div>
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
              
              <!-- Прямоугольник выделения -->
              <div
                v-if="selectionRectangle.active"
                class="selection-rectangle"
                :style="selectionRectangleStyle"
              ></div>
            </div>

            <!-- Режим списка -->
            <DataTable v-else :value="allItems" :loading="loading" class="p-datatable-sm" :selection="selectedItems" @selection-change="onSelectionChange" selectionMode="multiple">
              <template #empty>
                <div class="text-center p-4">
                  <i class="pi pi-folder-open text-4xl text-500 mb-3"></i>
                  <div>Папка пуста</div>
                </div>
              </template>

              <Column selectionMode="multiple" headerStyle="width: 3rem"></Column>

              <Column field="icon" header="" style="width: 3rem">
                <template #body="{ data }">
                  <i v-if="data.type === 'folder'" class="pi pi-folder text-orange-500"></i>
                  <img v-else-if="data.type === 'image'" :src="data.thumbnailUrl || data.url" class="w-2rem h-2rem object-cover border-round" />
                  <i v-else class="pi pi-arrow-left"></i>
                </template>
              </Column>

              <Column field="name" header="Название" sortable>
                <template #body="{ data }">
                  <span 
                    class="cursor-pointer hover:text-primary"
                    @click="handleTableItemClick(data)"
                  >
                    {{ data.name }}
                  </span>
                </template>
              </Column>

              <Column field="size" header="Размер" sortable>
                <template #body="{ data }">
                  <span v-if="data.type === 'image'">{{ formatFileSize(data.size) }}</span>
                  <span v-else-if="data.type === 'folder'">{{ data.itemCount }} элементов</span>
                  <span v-else>—</span>
                </template>
              </Column>

              <Column field="updatedAt" header="Изменено" sortable>
                <template #body="{ data }">
                  <span v-if="data.updatedAt">{{ formatDate(data.updatedAt) }}</span>
                  <span v-else>—</span>
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
    
    <!-- Статусная панель -->
    <div v-if="(filteredFolders.length > 0 || filteredImages.length > 0) && viewMode === 'grid'" class="grid">
      <div class="col-12">
        <Card>
          <template #content>
            <div class="flex align-items-center justify-content-between text-sm text-600">
              <div class="flex align-items-center gap-4">
                <span>
                  {{ filteredFolders.length }} папок, {{ filteredImages.length }} изображений
                </span>
                <span v-if="selectedItems.value.length > 0">
                  • Выбрано {{ selectedItems.value.length }} элементов
                </span>
              </div>
              <div v-if="selectedItems.value.length > 0" class="flex align-items-center gap-2">
                <Button
                  label="Выбрать все"
                  @click="selectAll"
                  text
                  size="small"
                  class="p-0"
                />
                <span class="text-300">•</span>
                <Button
                  label="Снять выделение"
                  @click="clearSelection"
                  text
                  size="small"
                  class="p-0"
                />
              </div>
            </div>
          </template>
        </Card>
      </div>
    </div>
  </div>

  <!-- Диалог подтверждения множественного удаления -->
  <Dialog 
    v-model:visible="showBulkDeleteDialog" 
    modal 
    header="Подтверждение удаления" 
    :style="{ width: '400px' }"
  >
    <div class="flex align-items-center gap-3 mb-3">
      <i class="pi pi-exclamation-triangle text-orange-500 text-2xl"></i>
      <div>
        <div class="font-medium text-900 mb-1">
          Вы уверены, что хотите удалить {{ selectedItems.length }} элементов?
        </div>
        <div class="text-600 text-sm">
          Это действие нельзя отменить.
        </div>
      </div>
    </div>
    
    <template #footer>
      <Button label="Отмена" text @click="showBulkDeleteDialog = false" />
      <Button 
        label="Удалить" 
        severity="danger"
        @click="performBulkDelete"
        :loading="deletingItems"
      />
    </template>
  </Dialog>

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
    <div class="flex flex-column gap-3">
      <div class="flex align-items-center gap-2">
        <Checkbox 
          v-model="checkDuplicates" 
          inputId="checkDuplicates" 
          binary
        />
        <label for="checkDuplicates" class="text-sm">Проверять и заменять дубликаты</label>
      </div>
      
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
    </div>
    
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
    :style="{ width: '600px' }"
    :closable="!uploading"
    :closeOnEscape="!uploading"
  >
    <div class="flex flex-column gap-3">
      <FileUpload
        ref="zipUpload"
        mode="basic"
        accept=".zip"
        chooseLabel="Выбрать ZIP файл"
        @select="onZipSelect"
        :disabled="uploading"
      />
      
      <!-- Информация о лимитах -->
      <div class="text-xs text-500 mt-2 mb-3">
        <i class="pi pi-info-circle mr-1"></i>
        Максимум: 2GB архив, 10,000 файлов (только изображения)
      </div>
      
      <!-- Прогресс загрузки -->
      <div v-if="uploading" class="flex flex-column gap-2">
        <div class="flex align-items-center justify-content-between">
          <span class="text-sm font-medium">Загрузка и обработка архива...</span>
          <span v-if="uploadProgress.total > 0" class="text-sm text-600">
            {{ uploadProgress.processed }} из {{ uploadProgress.total }} файлов
          </span>
        </div>
        
        <ProgressBar 
          :value="uploadProgress.total > 0 ? (uploadProgress.processed / uploadProgress.total) * 100 : null"
          :showValue="false"
          class="h-1rem"
        />
        
        <div class="text-xs text-600">
          <div v-if="uploadProgress.uploaded > 0" class="text-green-600">
            ✓ Загружено: {{ uploadProgress.uploaded }}
          </div>
          <div v-if="uploadProgress.failed > 0" class="text-red-600">
            ✗ Ошибок: {{ uploadProgress.failed }}
          </div>
        </div>
      </div>
    </div>
    
    <template #footer>
      <Button 
        label="Отмена" 
        text 
        @click="cancelZipUpload" 
        :disabled="uploading && !canCancelUpload"
      />
      <Button 
        label="Загрузить" 
        @click="uploadZip" 
        :disabled="!selectedZipFile || uploading"
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
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
import ProgressBar from 'primevue/progressbar'
import Checkbox from 'primevue/checkbox'
import Divider from 'primevue/divider'
import apiService from '../services/apiService'

// Реактивные данные
const toast = useToast()
const viewMode = ref('grid')
const searchQuery = ref('')
const currentPath = ref('/')
const loading = ref(false)
const checkDuplicates = ref(true)

// Данные папок и файлов
const folders = ref([])
const images = ref([])

// Система множественного выбора
const selectedItems = ref([])
const selectionRectangle = ref({
  active: false,
  startX: 0,
  startY: 0,
  currentX: 0,
  currentY: 0
})
const itemRefs = ref({})
const draggedItems = ref([])
const gridContainer = ref(null)

// Диалоги
const showCreateFolderDialog = ref(false)
const showUploadDialog = ref(false)
const showZipUploadDialog = ref(false)
const showImageDialog = ref(false)
const showRenameDialog = ref(false)
const showDeleteDialog = ref(false)
const showBulkDeleteDialog = ref(false)

// Формы
const newFolderName = ref('')
const selectedImages = ref([])
const selectedZipFile = ref(null)
const selectedImageForView = ref(null)
const uploading = ref(false)
const deletingItems = ref(false)
const itemToRename = ref(null)
const newItemName = ref('')
const itemToDelete = ref(null)

// Прогресс загрузки ZIP
const uploadProgress = ref({
  total: 0,
  processed: 0,
  uploaded: 0,
  failed: 0
})
const canCancelUpload = ref(false)

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

// Стили для прямоугольника выделения
const selectionRectangleStyle = computed(() => {
  if (!selectionRectangle.value.active) return {}
  
  const left = Math.min(selectionRectangle.value.startX, selectionRectangle.value.currentX)
  const top = Math.min(selectionRectangle.value.startY, selectionRectangle.value.currentY)
  const width = Math.abs(selectionRectangle.value.currentX - selectionRectangle.value.startX)
  const height = Math.abs(selectionRectangle.value.currentY - selectionRectangle.value.startY)
  
  return {
    position: 'absolute',
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
    border: '1px dashed var(--primary-color)',
    backgroundColor: 'rgba(var(--primary-color-rgb), 0.1)',
    pointerEvents: 'none',
    zIndex: 1000
  }
})

// Методы множественного выбора
const setItemRef = (el, item, type) => {
  if (el) {
    itemRefs.value[`${type}-${item.id}`] = el
  }
}

const isSelected = (item, type) => {
  return selectedItems.value.some(selected => 
    selected.id === item.id && selected.type === type
  )
}

const toggleSelection = (item, type) => {
  const index = selectedItems.value.findIndex(selected => 
    selected.id === item.id && selected.type === type
  )
  
  if (index >= 0) {
    selectedItems.value.splice(index, 1)
  } else {
    selectedItems.value.push({ ...item, type })
  }
}

const clearSelection = () => {
  selectedItems.value = []
}

const selectRange = (item, type) => {
  if (selectedItems.value.length === 0) {
    toggleSelection(item, type)
    return
  }
  
  const lastSelected = selectedItems.value[selectedItems.value.length - 1]
  const allItems = [
    ...filteredFolders.value.map(f => ({ ...f, type: 'folder' })),
    ...filteredImages.value.map(i => ({ ...i, type: 'image' }))
  ]
  
  const startIndex = allItems.findIndex(i => 
    i.id === lastSelected.id && lastSelected.type === (i.type || 'image')
  )
  const endIndex = allItems.findIndex(i => 
    i.id === item.id && type === (i.type || 'image')
  )
  
  if (startIndex >= 0 && endIndex >= 0) {
    const start = Math.min(startIndex, endIndex)
    const end = Math.max(startIndex, endIndex)
    
    for (let i = start; i <= end; i++) {
      const currentItem = allItems[i]
      const currentType = currentItem.type || 'image'
      if (!isSelected(currentItem, currentType)) {
        selectedItems.value.push({ ...currentItem, type: currentType })
      }
    }
  }
}

const handleItemClick = (item, type, event) => {
  if (event.ctrlKey || event.metaKey) {
    // Ctrl/Cmd клик - переключаем выделение
    toggleSelection(item, type)
  } else if (event.shiftKey && selectedItems.value.length > 0) {
    // Shift клик - выделяем диапазон
    selectRange(item, type)
  } else {
    // Обычный клик
    if (isSelected(item, type) && selectedItems.value.length > 1) {
      // Если элемент выделен и есть множественное выделение - оставляем выделение
      return
    } else if (selectedItems.value.length === 0 || !event.shiftKey) {
      // Очищаем выделение и действуем как обычно
      clearSelection()
      if (type === 'folder') {
        openFolder(item)
      } else {
        openImage(item)
      }
    }
  }
}

const handleCheckboxChange = (item, type, event) => {
  event.stopPropagation()
  toggleSelection(item, type)
}

const handleTableItemClick = (data) => {
  if (data.type === 'back') {
    goBack()
  } else if (data.type === 'folder') {
    openFolder(data)
  } else {
    openImage(data)
  }
}

const onSelectionChange = (event) => {
  selectedItems.value = event.value || []
}

// Методы выделения прямоугольником
const startSelectionRectangle = (event) => {
  if (event.target.closest('.selectable-item') || event.button !== 0) return
  
  event.preventDefault()
  // Контейнер, внутри которого рисуем прямоугольник
  const container = gridContainer.value // .grid-container через ref
  if (!container) return
  
  const rect = container.getBoundingClientRect()
  const scrollTop = container.scrollTop || 0
  const scrollLeft = container.scrollLeft || 0
  
  selectionRectangle.value = {
    active: true,
    startX: event.clientX - rect.left + scrollLeft,
    startY: event.clientY - rect.top + scrollTop,
    currentX: event.clientX - rect.left + scrollLeft,
    currentY: event.clientY - rect.top + scrollTop
  }
  
  if (!event.ctrlKey && !event.metaKey) {
    clearSelection()
  }
  
  document.addEventListener('mousemove', updateSelectionRectangle)
  document.addEventListener('mouseup', endSelectionRectangle)
}

const updateSelectionRectangle = (event) => {
  if (!selectionRectangle.value.active) return
  
  // Используем тот же контейнер, что и при старте (через ref)
  const container = gridContainer.value
  if (!container) return
  
  const rect = container.getBoundingClientRect()
  const scrollTop = container.scrollTop || 0
  const scrollLeft = container.scrollLeft || 0
  
  selectionRectangle.value.currentX = event.clientX - rect.left + scrollLeft
  selectionRectangle.value.currentY = event.clientY - rect.top + scrollTop
  
  // Проверяем пересечения с элементами
  const rectLeft = Math.min(selectionRectangle.value.startX, selectionRectangle.value.currentX)
  const rectTop = Math.min(selectionRectangle.value.startY, selectionRectangle.value.currentY)
  const rectRight = Math.max(selectionRectangle.value.startX, selectionRectangle.value.currentX)
  const rectBottom = Math.max(selectionRectangle.value.startY, selectionRectangle.value.currentY)
  
  // Проверяем каждый элемент
  Object.keys(itemRefs.value).forEach(key => {
    const element = itemRefs.value[key]
    if (!element) return
    
  const elementRect = element.getBoundingClientRect()
  const elementLeft = elementRect.left - rect.left
  const elementTop = elementRect.top - rect.top
  const elementRight = elementRect.right - rect.left
  const elementBottom = elementRect.bottom - rect.top
    
    // Проверяем пересечение
    if (rectLeft < elementRight && rectRight > elementLeft &&
        rectTop < elementBottom && rectBottom > elementTop) {
      
      // Находим соответствующий элемент данных
      const [type, id] = key.split('-')
      const item = type === 'folder' 
        ? folders.value.find(f => f.id === id)
        : images.value.find(i => i.id === id)
      
      if (item && !isSelected(item, type)) {
        selectedItems.value.push({ ...item, type })
      }
    }
  })
}

const endSelectionRectangle = () => {
  selectionRectangle.value.active = false
  document.removeEventListener('mousemove', updateSelectionRectangle)
  document.removeEventListener('mouseup', endSelectionRectangle)
}

// Методы drag & drop
const handleDragStart = (event, item, type) => {
  if (!isSelected(item, type)) {
    clearSelection()
    selectedItems.value.push({ ...item, type })
  }
  
  draggedItems.value = [...selectedItems.value]
  event.dataTransfer.effectAllowed = 'move'
}

const handleDragOver = (event) => {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

const handleDrop = (event, targetFolder) => {
  event.preventDefault()
  if (draggedItems.value.length > 0) {
    moveItemsToFolder(draggedItems.value, targetFolder.path)
  }
  draggedItems.value = []
}

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
    const result = await apiService.uploadImagesToFolder(currentPath.value, selectedImages.value, checkDuplicates.value)
    
    let message = result.message
    if (result.replaced_duplicates > 0) {
      toast.add({
        severity: 'info',
        summary: 'Дубликаты заменены',
        detail: `${result.replaced_duplicates} дубликатов было заменено новыми файлами`
      })
    }
    
    toast.add({
      severity: 'success',
      summary: 'Успех',
      detail: message
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
  // Сброс прогресса
  uploadProgress.value = {
    total: 0,
    processed: 0,
    uploaded: 0,
    failed: 0
  }
}

const uploadZip = async () => {
  if (!selectedZipFile.value) return
  
  uploading.value = true
  canCancelUpload.value = false
  
  // Сброс прогресса
  uploadProgress.value = {
    total: 0,
    processed: 0,
    uploaded: 0,
    failed: 0
  }
  
  try {
    const result = await apiService.uploadZipToFolder(currentPath.value, selectedZipFile.value)
    
    // Обновляем прогресс на основе результата
    uploadProgress.value.total = result.uploaded.length + result.failed.length
    uploadProgress.value.processed = result.uploaded.length + result.failed.length
    uploadProgress.value.uploaded = result.uploaded.length
    uploadProgress.value.failed = result.failed.length
    
    const successMsg = result.message || `Загружено ${result.uploaded.length} из ${result.uploaded.length + result.failed.length} файлов`
    
    toast.add({
      severity: result.failed.length === 0 ? 'success' : 'warn',
      summary: result.failed.length === 0 ? 'Успех' : 'Частично загружено',
      detail: successMsg,
      life: 5000
    })
    
    if (result.failed.length > 0) {
      console.warn('Не удалось загрузить файлы:', result.failed)
    }
    
    selectedZipFile.value = null
    showZipUploadDialog.value = false
    loadData()
  } catch (error) {
    console.error('Ошибка загрузки ZIP:', error)
    const errorMsg = error.response?.data?.detail || error.message || 'Не удалось загрузить ZIP архив'
    toast.add({
      severity: 'error',
      summary: 'Ошибка',
      detail: errorMsg,
      life: 7000
    })
  } finally {
    uploading.value = false
    canCancelUpload.value = false
  }
}

const cancelZipUpload = () => {
  if (!uploading.value) {
    showZipUploadDialog.value = false
    selectedZipFile.value = null
    uploadProgress.value = {
      total: 0,
      processed: 0,
      uploaded: 0,
      failed: 0
    }
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const showContextMenu = (event, item, type) => {
  const items = []
  
  // Добавляем тип к элементу для последующего использования
  const itemWithType = { ...item, type }
  
  // Если элемент не выделен, но есть множественное выделение - очищаем его
  if (!isSelected(item, type) && selectedItems.value.length > 0) {
    clearSelection()
  }
  
  // Если элемент не выделен - выделяем его
  if (!isSelected(item, type)) {
    selectedItems.value.push(itemWithType)
  }
  
  // Контекстное меню для множественного выделения
  if (selectedItems.value.length > 1) {
    items.push(
      { 
        label: `Удалить выбранные (${selectedItems.value.length})`, 
        icon: 'pi pi-trash', 
        command: () => confirmBulkDelete() 
      },
      { separator: true },
      { 
        label: 'Снять выделение', 
        icon: 'pi pi-times', 
        command: () => clearSelection() 
      }
    )
  } else {
    // Контекстное меню для одного элемента
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

// Методы множественных операций
const confirmBulkDelete = () => {
  showBulkDeleteDialog.value = true
}

const performBulkDelete = async () => {
  deletingItems.value = true
  try {
    const paths = selectedItems.value.map(item => item.path)
    const result = await apiService.bulkDeleteItems(paths)
    
    toast.add({
      severity: 'success',
      summary: 'Успех',
      detail: result.message
    })
    
    if (result.failed.length > 0) {
      toast.add({
        severity: 'warn',
        summary: 'Предупреждение',
        detail: `Не удалось удалить ${result.failed.length} элементов`
      })
    }
    
    clearSelection()
    showBulkDeleteDialog.value = false
    loadData()
  } catch (error) {
    console.error('Ошибка множественного удаления:', error)
    toast.add({
      severity: 'error',
      summary: 'Ошибка',
      detail: 'Не удалось удалить элементы'
    })
  } finally {
    deletingItems.value = false
  }
}

const moveItemsToFolder = async (items, targetPath) => {
  try {
    const sourcePaths = items.map(item => item.path)
    const result = await apiService.moveItems(sourcePaths, targetPath)
    
    toast.add({
      severity: 'success',
      summary: 'Успех',
      detail: result.message
    })
    
    if (result.failed.length > 0) {
      toast.add({
        severity: 'warn',
        summary: 'Предупреждение',
        detail: `Не удалось переместить ${result.failed.length} элементов`
      })
    }
    
    clearSelection()
    loadData()
  } catch (error) {
    console.error('Ошибка перемещения:', error)
    toast.add({
      severity: 'error',
      summary: 'Ошибка',
      detail: 'Не удалось переместить элементы'
    })
  }
}

const formatDate = (date) => {
  return new Date(date).toLocaleString('ru-RU')
}

const handleImageError = (event) => {
  event.target.src = '/placeholder-image.png' // Заглушка
}

onMounted(() => {
  loadData()
  
  // Добавляем обработчики клавиатурных сочетаний
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

const handleKeydown = (event) => {
  // Игнорируем если фокус на элементах ввода
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) {
    return
  }
  
  switch (event.key) {
    case 'Delete':
    case 'Backspace':
      if (selectedItems.value.length > 0) {
        event.preventDefault()
        if (selectedItems.value.length === 1) {
          deleteItem(selectedItems.value[0])
        } else {
          confirmBulkDelete()
        }
      }
      break
      
    case 'a':
    case 'A':
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault()
        selectAll()
      }
      break
      
    case 'Escape':
      if (selectedItems.value.length > 0) {
        event.preventDefault()
        clearSelection()
      }
      break
  }
}

const selectAll = () => {
  clearSelection()
  filteredFolders.value.forEach(folder => {
    selectedItems.value.push({ ...folder, type: 'folder' })
  })
  filteredImages.value.forEach(image => {
    selectedItems.value.push({ ...image, type: 'image' })
  })
}
</script>

<style scoped>
.images-page {
  padding: 1rem;
  position: relative;
}

.folder-item,
.image-item {
  border: 1px solid var(--surface-border);
  transition: all 0.2s;
  position: relative;
  user-select: none;
}

.selectable-item {
  cursor: pointer;
}

.selectable-item.bg-primary-100 {
  border-color: var(--primary-color);
  background: var(--primary-50);
}

.folder-item:hover:not(.bg-primary-100),
.image-item:hover:not(.bg-primary-100) {
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

.selection-indicator {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  background: #10b981;
  border: 2px solid white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  z-index: 10;
  color: white;
  font-size: 14px;
  font-weight: bold;
}

.selection-rectangle {
  position: absolute;
  border: 2px solid var(--primary-500);
  background: rgba(var(--primary-500), 0.15);
  pointer-events: none;
  z-index: 1000;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

/* Drag and drop styles */
.selectable-item[draggable="true"]:hover {
  cursor: grab;
}

.selectable-item[draggable="true"]:active {
  cursor: grabbing;
}

/* Анимации */
.folder-item,
.image-item {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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

/* Responsive improvements */
@media (max-width: 768px) {
  .images-page {
    padding: 0.5rem;
  }
  
  .selection-indicator {
    top: 4px;
    right: 4px;
    width: 20px;
    height: 20px;
  }
}

/* Контейнер сетки как контекст позиционирования для прямоугольника */
.grid-container {
  position: relative;
  width: 100%;
  min-height: 400px;
}
</style>
