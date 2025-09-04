<template>
  <Dialog
    :visible="visible"
    modal
    header="Экспорт данных"
    :style="{ width: '50rem' }"
    :closable="true"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="p-fluid">
      <!-- Выбор брендов -->
      <div class="field mb-4">
        <label for="brands" class="block text-900 font-medium mb-2">Выберите бренды</label>
        <MultiSelect
          id="brands"
          v-model="selectedBrands"
          :options="brandOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Выберите бренды"
          filter
          :maxSelectedLabels="3"
          display="chip"
          class="w-full"
          :invalid="!selectedBrands || selectedBrands.length === 0"
        >
          <template #option="slotProps">
            <div class="flex align-items-center">
              <span>{{ slotProps.option.label }}</span>
            </div>
          </template>
        </MultiSelect>
        <small v-if="!selectedBrands || selectedBrands.length === 0" class="p-error">
          Необходимо выбрать хотя бы один бренд
        </small>
      </div>

      <!-- Список колонок -->
      <div class="field mb-4">
        <label class="block text-900 font-medium mb-2">Колонки для экспорта</label>
        <div class="grid">
          <div 
            v-for="column in availableColumns" 
            :key="column.field"
            class="col-12 md:col-6 mb-2"
          >
            <div class="flex align-items-center">
              <Checkbox
                v-model="selectedColumns"
                :inputId="column.field"
                :value="column"
                class="mr-2"
              />
              <div class="flex align-items-center flex-1">
                <Checkbox
                  v-model="columnFilters"
                  :inputId="`filter_${column.field}`"
                  :value="column.field"
                  class="mr-2"
                />
                <label 
                  :for="column.field" 
                  class="cursor-pointer select-none"
                  :class="{ 'font-semibold': columnFilters.includes(column.field) }"
                >
                  {{ columnFilters.includes(column.field) ? '@' : '' }}{{ column.header }}
                </label>
              </div>
            </div>
          </div>
        </div>
        <small v-if="!selectedColumns || selectedColumns.length === 0" class="p-error">
          Необходимо выбрать хотя бы одну колонку
        </small>
      </div>

      <!-- Опция экспорта с изображениями -->
      <div class="field mb-4">
        <div class="flex align-items-center">
          <Checkbox
            v-model="includeImages"
            inputId="include_images"
            :binary="true"
            class="mr-2"
          />
          <label for="include_images" class="cursor-pointer select-none">
            Экспортировать с изображениями (ZIP архив)
          </label>
        </div>
        <small class="text-600">
          Без изображений: data.xlsx | С изображениями: архив с data.xlsx + папка media
        </small>
      </div>

      <!-- Предварительный просмотр -->
      <div v-if="selectedBrands && selectedBrands.length > 0 && selectedColumns && selectedColumns.length > 0" class="field mb-4">
        <div class="surface-100 border-round p-3">
          <h6 class="mt-0">Предварительный просмотр:</h6>
          <p class="mb-2">
            <strong>Бренды:</strong> {{ selectedBrands.join(', ') }}
          </p>
          <p class="mb-2">
            <strong>Колонки:</strong> {{ selectedColumns.length }} выбрано
          </p>
          <p class="mb-2">
            <strong>Формат:</strong> {{ includeImages ? 'ZIP архив с изображениями' : 'Excel файл' }}
          </p>
          <div class="mt-2">
            <strong>Названия колонок:</strong>
            <div class="flex flex-wrap gap-1 mt-1">
              <Tag 
                v-for="column in selectedColumns" 
                :key="column.field"
                :value="(columnFilters.includes(column.field) ? '@' : '') + column.header"
                :severity="columnFilters.includes(column.field) ? 'info' : 'secondary'"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-content-between">
        <Button
          label="Отмена"
          icon="pi pi-times"
          class="p-button-text"
          @click="closeDialog"
        />
        <Button
          label="Экспортировать"
          icon="pi pi-download"
          class="p-button-primary"
          :loading="exporting"
          :disabled="!canExport"
          @click="performExport"
        />
      </div>
    </template>
  </Dialog>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import Dialog from 'primevue/dialog'
import MultiSelect from 'primevue/multiselect'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import apiService from '@/services/apiService'

export default {
  name: 'ExportDialog',
  components: {
    Dialog,
    MultiSelect,
    Checkbox,
    Button,
    Tag
  },
  emits: ['update:visible'],
  props: {
    visible: {
      type: Boolean,
      default: false
    }
  },
  setup(props, { emit }) {
    const toast = useToast()
    
    // Реактивные данные
  const selectedBrands = ref([])
  const selectedColumns = ref([])
  const columnFilters = ref([])
    const includeImages = ref(false)
    const exporting = ref(false)
    
    // Опции для компонентов
    const brandOptions = ref([])
    const availableColumns = ref([])

    // Вычисляемые свойства
    const canExport = computed(() => {
      return selectedBrands.value && selectedBrands.value.length > 0 &&
             selectedColumns.value && selectedColumns.value.length > 0
    })

    // Методы
    const loadBrandOptions = async () => {
      try {
        const response = await apiService.getFilterOptions()
        brandOptions.value = response.data.brands.map(brand => ({
          label: brand,
          value: brand
        }))
      } catch (error) {
        console.error('Ошибка загрузки брендов:', error)
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось загрузить список брендов',
          life: 3000
        })
      }
    }

    const loadAvailableColumns = async () => {
      try {
        const response = await apiService.getProductColumns()
        availableColumns.value = response.data.columns

        // Предвыбор колонок в нужном порядке (совпадает с бэкендом)
        const desiredOrder = [
          'images',
          'manufacturer_name',
          'part_number',
          'part_name',
          'description',
          'category',
          'type',
          'size',
          'color',
          'brand',
          'producer',
          'gender',
          'width',
          'height',
          'age',
          'shape',
          'year'
        ]

        const byField = Object.fromEntries(availableColumns.value.map(c => [c.field, c]))
        selectedColumns.value = desiredOrder
          .map(f => byField[f])
          .filter(Boolean)

        // По умолчанию включаем чекбоксы для '@' для всех выбранных колонок
        columnFilters.value = selectedColumns.value.map(c => c.field)
      } catch (error) {
        console.error('Ошибка загрузки колонок:', error)
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось загрузить список колонок',
          life: 3000
        })
      }
    }

    const performExport = async () => {
      if (!canExport.value) {
        toast.add({
          severity: 'warn',
          summary: 'Предупреждение',
          detail: 'Выберите бренды и колонки для экспорта',
          life: 3000
        })
        return
      }

      exporting.value = true
      try {
        // Подготовка данных для экспорта
        const exportData = {
          brands: selectedBrands.value,
          columns: selectedColumns.value.map(col => ({
            field: col.field,
            display_name: (columnFilters.value.includes(col.field) ? '@' : '') + col.header
          })),
          include_images: includeImages.value
        }

        const response = await apiService.exportProducts(exportData)

        // Создание blob и скачивание файла
        const blob = new Blob([response.data], {
          type: includeImages.value ? 'application/zip' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        
        const filename = includeImages.value 
          ? `export_with_images_${new Date().toISOString().split('T')[0]}.zip`
          : `data_${new Date().toISOString().split('T')[0]}.xlsx`
        
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)

        toast.add({
          severity: 'success',
          summary: 'Успешно',
          detail: `Файл ${filename} экспортирован`,
          life: 3000
        })

        closeDialog()
      } catch (error) {
        console.error('Ошибка экспорта:', error)
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось экспортировать данные',
          life: 3000
        })
      } finally {
        exporting.value = false
      }
    }

    const closeDialog = () => {
      emit('update:visible', false)
      // Сброс формы
      selectedBrands.value = []
      selectedColumns.value = []
      columnFilters.value = []
      includeImages.value = false
    }

    // Инициализация
    onMounted(() => {
      loadBrandOptions()
      loadAvailableColumns()
    })

    // Watcher для обновления данных при открытии диалога
    watch(() => props.visible, (newValue) => {
      if (newValue) {
        loadBrandOptions()
        loadAvailableColumns()
      }
    })

    return {
      selectedBrands,
      selectedColumns,
      columnFilters,
      includeImages,
      exporting,
      brandOptions,
      availableColumns,
      canExport,
      performExport,
      closeDialog
    }
  }
}
</script>

<style scoped>
.field {
  margin-bottom: 1.5rem;
}

.p-error {
  color: #e24c4c;
  font-size: 0.875rem;
}
</style>
