<template>
  <div class="files-page">
    <div class="grid">
      <div class="col-12">
        <Card>
          <template #title>
            <div class="flex align-items-center">
              <i class="pi pi-upload mr-2"></i>
              Загрузка файлов
            </div>
          </template>

          <template #content>
            <div class="upload-section mb-4">
              <h2 class="text-900 mb-3">Загрузка Excel файла с данными очков</h2>
              <FileUpload
                ref="excelUpload"
                mode="basic"
                accept=".xlsx,.xls"
                :maxFileSize="50000000"
                chooseLabel="Выбрать Excel файл"
                cancelLabel="Отмена"
                @select="onExcelSelect"
              />
              <div v-if="selectedExcelFile" class="mt-3">
                <p class="text-sm text-600">Выбран файл: {{ selectedExcelFile.name }}</p>
                <Button label="Импортировать Excel" @click="onExcelUpload" :loading="isUploadingExcel" />
              </div>
              <small class="text-500 mt-1 block">
                Максимальный размер: 50MB. Поддерживаемые форматы: .xlsx, .xls
              </small>
            </div>
          </template>
        </Card>
      </div>

            <!-- Маппинг колонок -->
      <div v-if="excelData.columns" class="col-12">
        <ColumnMapper
          :columns="excelData.columns"
          :initial-mapping="excelData.mapping"
          :sample-data="excelData.sample_data"
          :structure-info="excelData.structure_info"
          :extracted-images="excelData.extracted_images"
          :is-loading="isConfirming"
          @mapping-changed="onMappingChanged"
          @apply-mappings="onApplyMappings"
        />
      </div>

      <!-- Модальное окно с результатами загрузки -->
      <Dialog 
        v-model:visible="showResultsModal" 
        modal 
        header="Результаты импорта"
        :style="{ width: '50rem' }"
        :breakpoints="{ '1199px': '75vw', '575px': '90vw' }"
      >
        <div v-if="confirmationResults">
          <div class="grid mb-4">
            <div class="col-12 md:col-6">
              <div class="surface-100 p-4 border-round-md text-center">
                <div class="flex align-items-center justify-content-center mb-3">
                  <i class="pi pi-plus-circle text-green-500 text-2xl mr-2"></i>
                  <span class="font-semibold text-lg">Новые товары</span>
                </div>
                <span class="text-3xl font-bold text-green-600">{{ confirmationResults.inserted }}</span>
              </div>
            </div>
            <div class="col-12 md:col-6">
              <div class="surface-100 p-4 border-round-md text-center">
                <div class="flex align-items-center justify-content-center mb-3">
                  <i class="pi pi-refresh text-blue-500 text-2xl mr-2"></i>
                  <span class="font-semibold text-lg">Обновленные товары</span>
                </div>
                <span class="text-3xl font-bold text-blue-600">{{ confirmationResults.updated }}</span>
              </div>
            </div>
          </div>
          
          <div class="mb-4">
            <Message severity="success" :closable="false">
              <i class="pi pi-check-circle mr-2"></i>
              {{ confirmationResults.summary }}
            </Message>
          </div>

          <div v-if="confirmationResults.errors.length > 0" class="mb-4">
            <h4 class="text-orange-600 mb-3 flex align-items-center">
              <i class="pi pi-exclamation-triangle mr-2"></i>
              Предупреждения валидации (показаны первые 10):
            </h4>
            <div class="surface-50 p-3 border-round-md border-left-3 border-orange-500 max-h-20rem overflow-y-auto">
              <ul class="list-none p-0 m-0">
                <li v-for="error in confirmationResults.errors" :key="error" class="text-orange-700 mb-1 text-sm">
                  <i class="pi pi-info-circle mr-2"></i>
                  {{ error }}
                </li>
              </ul>
            </div>
          </div>
        </div>
        
        <template #footer>
          <Button 
            label="Закрыть" 
            icon="pi pi-times" 
            @click="closeResultsModal"
            severity="secondary"
          />
          <Button 
            label="Импортировать ещё файлы" 
            icon="pi pi-upload" 
            @click="startNewImport"
          />
        </template>
      </Dialog>
    </div>
    <!-- Toast для уведомлений -->
    <Toast />
  </div>
</template>

<script>
import { ref, reactive, nextTick } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import FileUpload from 'primevue/fileupload'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import Toast from 'primevue/toast'
import apiService from '../services/apiService'
import ColumnMapper from '../components/ColumnMapper.vue'

export default {
  name: 'FilesPage',
  components: {
    Card,
    FileUpload,
    DataTable,
    Column,
    Button,
    Dropdown,
    Message,
    Dialog,
    Toast,
    ColumnMapper
  },
  setup() {
    const toast = useToast()
    const excelUpload = ref()
    const excelData = reactive({ 
      columns: null, 
      mapping: {}, 
      sample_data: [],
      structure_info: null,
      extracted_images: {}
    })
    const sampleData = ref([])
    const confirmationResults = ref(null)
    const isConfirming = ref(false)
    const selectedExcelFile = ref(null)
    const isUploadingExcel = ref(false)
    const showResultsModal = ref(false)

    const dbFields = [
      { label: 'Название производителя', value: 'manufacturer_name' },
      { label: 'Номер детали', value: 'part_number' },
      { label: 'Название детали', value: 'part_name' },
      { label: 'Категория', value: 'category' },
      { label: 'Тип', value: 'type' },
      { label: 'Размер', value: 'size' },
      { label: 'Цвет', value: 'color' },
      { label: 'Бренд', value: 'brand' },
      { label: 'Производитель', value: 'producer' },
      { label: 'Пол', value: 'gender' },
      { label: 'Ширина', value: 'width' },
      { label: 'Высота', value: 'height' },
      { label: 'Возраст', value: 'age' },
      { label: 'Форма', value: 'shape' },
      { label: 'Год', value: 'year' },
      { label: 'Изображения', value: 'images' }
    ]

    const onExcelSelect = (event) => {
      selectedExcelFile.value = event.files[0]
    }

    const onExcelUpload = async () => {
      if (!selectedExcelFile.value) return

      isUploadingExcel.value = true
      try {
        const response = await apiService.uploadExcel(selectedExcelFile.value)
        excelData.columns = response.data.columns
        excelData.mapping = response.data.mapping
        excelData.sample_data = response.data.sample_data
        excelData.structure_info = response.data.structure_info
        excelData.extracted_images = response.data.extracted_images
      } catch (error) {
        console.error('Ошибка загрузки Excel:', error)
        toast.add({
          severity: 'error',
          summary: 'Ошибка загрузки',
          detail: 'Не удалось загрузить Excel файл: ' + (error.response?.data?.detail || error.message),
          life: 5000
        })
      } finally {
        isUploadingExcel.value = false
      }
    }

    const onMappingChange = (item, event) => {
      excelData.mapping[item.excelColumn] = event.value
    }

    const onCellEditComplete = (event) => {
      const { data, newValue, field } = event
      if (field === 'dbField') {
        data.dbField = newValue
        excelData.mapping[data.excelColumn] = newValue
      }
    }

    const addMapping = () => {
      mappingList.value.push({
        excelColumn: '',
        dbField: '',
        id: Math.random()
      })
    }

    const removeMapping = (item) => {
      const index = mappingList.value.findIndex(m => m.id === item.id)
      if (index > -1) {
        mappingList.value.splice(index, 1)
        delete excelData.mapping[item.excelColumn]
      }
    }

    const cancelMapping = () => {
      excelData.columns = null
      excelData.mapping = {}
      mappingList.value = []
      selectedExcelFile.value = null
    }

    const confirmMapping = async () => {
      if (!selectedExcelFile.value) return

      isConfirming.value = true
      try {
        // Фильтруем пустые маппинги
        const cleanMapping = {}
        Object.entries(excelData.mapping).forEach(([key, value]) => {
          if (value && value.trim()) {
            cleanMapping[key] = value
          }
        })

        const response = await apiService.confirmMapping(selectedExcelFile.value, cleanMapping)
        confirmationResults.value = response.data

        // Очищаем после успешной загрузки
        cancelMapping()
      } catch (error) {
        console.error('Ошибка подтверждения маппинга:', error)
      } finally {
        isConfirming.value = false
      }
    }

    const onMappingChanged = (change) => {
      if (change.clearAll) {
        Object.keys(excelData.mapping).forEach(key => {
          delete excelData.mapping[key]
        })
      } else {
        excelData.mapping[change.excelColumn] = change.dbField
      }
    }

    const onApplyMappings = async (finalMapping) => {
      if (!selectedExcelFile.value) {
        console.error('Файл не выбран')
        return
      }

      console.log('Начинаем применение маппинга...', finalMapping)
      isConfirming.value = true
      
      try {
        const response = await apiService.confirmMapping(selectedExcelFile.value, finalMapping)
        console.log('Получен ответ от сервера:', response)
        
        // Проверяем что ответ корректный
        if (response && response.data) {
          confirmationResults.value = response.data
          console.log('Результаты сохранены:', confirmationResults.value)

          // Показываем toast с успехом
          toast.add({
            severity: 'success',
            summary: 'Импорт завершен',
            detail: response.data.summary || 'Данные успешно импортированы',
            life: 5000
          })

          // Принудительное обновление Vue
          await nextTick()
          
          // Показываем модальное окно с результатами
          showResultsModal.value = true
          console.log('Модальное окно показано:', showResultsModal.value)

          // Очищаем форму маппинга только после показа результатов
          excelData.columns = null
          excelData.mapping = {}
          sampleData.value = []
          selectedExcelFile.value = null
        } else {
          console.error('Некорректный ответ сервера:', response)
          throw new Error('Сервер вернул некорректный ответ')
        }
      } catch (error) {
        console.error('Ошибка подтверждения маппинга:', error)
        
        // Показываем toast с ошибкой
        let errorMessage = 'Неизвестная ошибка'
        if (error.code === 'ECONNABORTED') {
          errorMessage = 'Запрос занимает слишком много времени. Проверьте логи сервера - данные могут быть обработаны.'
        } else if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail
        } else if (error.message) {
          errorMessage = error.message
        }
        
        toast.add({
          severity: 'error',
          summary: 'Ошибка импорта',
          detail: errorMessage,
          life: 10000
        })
      } finally {
        isConfirming.value = false
      }
    }

    const closeResultsModal = () => {
      showResultsModal.value = false
      confirmationResults.value = null
    }

    const startNewImport = () => {
      showResultsModal.value = false
      confirmationResults.value = null
      // Фокус на выбор файла
      if (excelUpload.value) {
        excelUpload.value.$el.querySelector('input[type="file"]')?.click()
      }
    }

    return {
      excelUpload,
      excelData,
      sampleData,
      confirmationResults,
      isConfirming,
      dbFields,
      selectedExcelFile,
      isUploadingExcel,
      showResultsModal,
      onExcelSelect,
      onExcelUpload,
      onMappingChanged,
      onApplyMappings,
      closeResultsModal,
      startNewImport
    }
  }
}
</script>

<style scoped>
.files-page {
  max-width: 1200px;
  margin: 0 auto;
}

.upload-section {
  padding: 1rem;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  background: #f8f9fa;
}

.mapping-table {
  margin-top: 1rem;
}

.mapping-actions {
  border-top: 1px solid #e9ecef;
  padding-top: 1rem;
}
</style>
