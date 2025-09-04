<template>
  <div class="data-page">
    <div class="page-header mb-4">
      <div class="flex align-items-center justify-content-between">
        <div>
          <h1 class="text-900 mb-1">Управление очками</h1>
          <p class="text-600 mb-0">Просмотр, редактирование и управление базой данных очков</p>
        </div>
        <div class="flex gap-2">
          <Button
            label="Добавить очки"
            icon="pi pi-plus"
            class="p-button-primary"
            @click="showAddDialog = true"
          />
          <Button
            label="Импорт из Excel"
            icon="pi pi-upload"
            class="p-button-secondary"
            @click="goToFiles"
          />
          <Button
            label="Настройки маппинга"
            icon="pi pi-cog"
            class="p-button-outlined p-button-secondary"
            @click="showMappingSettings = true"
          />
          <Button
            label="Восстановить БД"
            icon="pi pi-refresh"
            class="p-button-danger p-button-outlined"
            @click="showRestoreDialog = true"
          />
        </div>
      </div>
    </div>

    <!-- Компонент редактора данных -->
    <DataEditor ref="dataEditor" />

    <!-- Диалог добавления товара -->
    <Dialog
      v-model:visible="showAddDialog"
      modal
      header="Добавление новых очков"
      :style="{ width: '50rem' }"
      :closable="true"
    >
      <div class="p-fluid">
        <div class="grid">
          <div class="col-12 md:col-6">
            <label class="block text-900 font-medium mb-2">Номер детали *</label>
            <InputText v-model="newProduct.part_number" :class="{ 'p-invalid': errors.part_number }" />
            <small v-if="errors.part_number" class="p-error">{{ errors.part_number }}</small>
          </div>
          <div class="col-12 md:col-6">
            <label class="block text-900 font-medium mb-2">Название</label>
            <InputText v-model="newProduct.part_name" />
          </div>
          <div class="col-12 md:col-6">
            <label class="block text-900 font-medium mb-2">Бренд</label>
            <InputText v-model="newProduct.brand" />
          </div>
          <div class="col-12 md:col-6">
            <label class="block text-900 font-medium mb-2">Категория</label>
            <InputText v-model="newProduct.category" />
          </div>
          <div class="col-12 md:col-6">
            <label class="block text-900 font-medium mb-2">Цвет</label>
            <InputText v-model="newProduct.color" />
          </div>
          <div class="col-12 md:col-6">
            <label class="block text-900 font-medium mb-2">Размер</label>
            <InputText v-model="newProduct.size" />
          </div>
          <div class="col-12 md:col-6">
            <label class="block text-900 font-medium mb-2">Год</label>
            <InputNumber v-model="newProduct.year" :min="1900" :max="2030" />
          </div>
          <div class="col-12 md:col-6">
            <label class="block text-900 font-medium mb-2">Ширина</label>
            <InputNumber v-model="newProduct.width" suffix=" см" />
          </div>
          <div class="col-12 md:col-6">
            <label class="block text-900 font-medium mb-2">Высота</label>
            <InputNumber v-model="newProduct.height" suffix=" см" />
          </div>
          <div class="col-12">
            <label class="block text-900 font-medium mb-2">Изображения (URL через запятую)</label>
            <Textarea v-model="newProduct.images" :autoResize="true" rows="3" placeholder="https://example.com/image1.jpg, https://example.com/image2.jpg" />
          </div>
        </div>
      </div>

      <template #footer>
        <Button
          label="Отмена"
          icon="pi pi-times"
          class="p-button-text"
          @click="cancelAdd"
        />
        <Button
          label="Добавить"
          icon="pi pi-plus"
          class="p-button-primary"
          :loading="adding"
          @click="addProduct"
        />
      </template>
    </Dialog>

    <!-- Диалог экспорта -->
    <Dialog
      v-model:visible="showExportDialog"
      modal
      header="Экспорт данных"
      :style="{ width: '40rem' }"
      :closable="true"
    >
      <div class="p-fluid">
        <div class="field mb-4">
          <label class="block text-900 font-medium mb-2">Формат экспорта</label>
          <div class="flex gap-3">
            <div class="flex align-items-center">
              <RadioButton v-model="exportFormat" inputId="excel" value="excel" />
              <label for="excel" class="ml-2">Excel (.xlsx)</label>
            </div>
            <div class="flex align-items-center">
              <RadioButton v-model="exportFormat" inputId="csv" value="csv" />
              <label for="csv" class="ml-2">CSV</label>
            </div>
          </div>
        </div>

        <div class="field mb-4">
          <label class="block text-900 font-medium mb-2">Выберите колонки для экспорта</label>
          <div class="grid">
            <div
              v-for="column in availableColumns"
              :key="column.value"
              class="col-12 md:col-6"
            >
              <div class="flex align-items-center">
                <Checkbox
                  v-model="selectedColumns"
                  :inputId="column.value"
                  :value="column.value"
                />
                <label :for="column.value" class="ml-2">{{ column.label }}</label>
              </div>
            </div>
          </div>
        </div>

        <div class="field">
          <label class="block text-900 font-medium mb-2">Фильтры</label>
          <div class="grid">
            <div class="col-12 md:col-6">
              <Dropdown
                v-model="exportFilters.brand"
                :options="brandOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Бренд"
                :showClear="true"
                class="w-full"
              />
            </div>
            <div class="col-12 md:col-6">
              <Dropdown
                v-model="exportFilters.category"
                :options="categoryOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Категория"
                :showClear="true"
                class="w-full"
              />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <Button
          label="Отмена"
          icon="pi pi-times"
          class="p-button-text"
          @click="showExportDialog = false"
        />
        <Button
          label="Экспортировать"
          icon="pi pi-download"
          class="p-button-primary"
          :loading="exporting"
          @click="performExport"
        />
      </template>
    </Dialog>

    <!-- Диалог настроек маппинга -->
    <MappingSettings
      v-model="showMappingSettings"
      @settings-updated="onMappingSettingsUpdated"
    />

    <!-- Диалог подтверждения восстановления БД -->
    <Dialog
      v-model:visible="showRestoreDialog"
      modal
      header="Подтверждение восстановления"
      :style="{ width: '30rem' }"
      :closable="true"
    >
      <div class="p-fluid">
        <p class="text-900 mb-4">
          Вы уверены, что хотите восстановить базу данных из последнего бэкапа?
          Все текущие изменения будут потеряны.
        </p>
        <div class="flex justify-content-end gap-2">
          <Button
            label="Отмена"
            icon="pi pi-times"
            class="p-button-text"
            @click="showRestoreDialog = false"
          />
          <Button
            label="Восстановить"
            icon="pi pi-refresh"
            class="p-button-danger"
            @click="performRestore"
          />
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import RadioButton from 'primevue/radiobutton'
import Checkbox from 'primevue/checkbox'
import Dropdown from 'primevue/dropdown'
import DataEditor from '../components/DataEditor.vue'
import MappingSettings from '../components/MappingSettings.vue'
import apiService from '../services/apiService'

export default {
  name: 'DataPage',
  components: {
    Dialog,
    Button,
    InputText,
    InputNumber,
    Textarea,
    RadioButton,
    Checkbox,
    Dropdown,
    DataEditor,
    MappingSettings
  },
  setup() {
    const router = useRouter()
    const toast = useToast()
    const dataEditor = ref()
    const showAddDialog = ref(false)
    const showExportDialog = ref(false)
    const showMappingSettings = ref(false)
    const showRestoreDialog = ref(false)
    const adding = ref(false)
    const exporting = ref(false)

    const newProduct = reactive({
      part_number: '',
      part_name: '',
      brand: '',
      category: '',
      color: '',
      size: '',
      year: null,
      width: null,
      height: null,
      images: ''
    })

    const errors = reactive({})

    const exportFormat = ref('excel')
    const selectedColumns = ref([
      'id', 'part_number', 'part_name', 'brand', 'category', 'color', 'size', 'year'
    ])

    const exportFilters = reactive({
      brand: null,
      category: null
    })

    const availableColumns = [
      { label: 'ID', value: 'id' },
      { label: 'Номер детали', value: 'part_number' },
      { label: 'Название', value: 'part_name' },
      { label: 'Бренд', value: 'brand' },
      { label: 'Категория', value: 'category' },
      { label: 'Цвет', value: 'color' },
      { label: 'Размер', value: 'size' },
      { label: 'Год', value: 'year' },
      { label: 'Ширина', value: 'width' },
      { label: 'Высота', value: 'height' },
      { label: 'Изображения', value: 'images' }
    ]

    const brandOptions = ref([])
    const categoryOptions = ref([])

    const goToFiles = () => {
      router.push('/files')
    }

    const validateProduct = () => {
      errors.part_number = !newProduct.part_number.trim() ? 'Номер детали обязателен' : ''
      return !Object.values(errors).some(error => error)
    }

    const addProduct = async () => {
      if (!validateProduct()) return

      adding.value = true
      try {
        // Очистка от пустых значений
        const productData = {}
        Object.keys(newProduct).forEach(key => {
          if (newProduct[key] !== null && newProduct[key] !== '') {
            productData[key] = newProduct[key]
          }
        })

        await apiService.createProduct(productData)
        showAddDialog.value = false
        resetNewProduct()

        // Обновляем таблицу
        if (dataEditor.value) {
          dataEditor.value.loadProducts()
        }

        toast.add({
          severity: 'success',
          summary: 'Успешно',
          detail: 'Товар добавлен',
          life: 3000
        })
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось добавить товар',
          life: 3000
        })
      } finally {
        adding.value = false
      }
    }

    const cancelAdd = () => {
      showAddDialog.value = false
      resetNewProduct()
    }

    const resetNewProduct = () => {
      Object.keys(newProduct).forEach(key => {
        if (typeof newProduct[key] === 'string') {
          newProduct[key] = ''
        } else {
          newProduct[key] = null
        }
      })
      Object.keys(errors).forEach(key => {
        errors[key] = ''
      })
    }

    const performExport = async () => {
      if (selectedColumns.value.length === 0) {
        toast.add({
          severity: 'warn',
          summary: 'Предупреждение',
          detail: 'Выберите хотя бы одну колонку',
          life: 3000
        })
        return
      }

      exporting.value = true
      try {
        // TODO: Реализовать экспорт через API
        const exportData = {
          format: exportFormat.value,
          columns: selectedColumns.value,
          filters: exportFilters
        }

        console.log('Экспорт данных:', exportData)

        toast.add({
          severity: 'info',
          summary: 'Информация',
          detail: 'Функционал экспорта будет реализован в ближайшее время',
          life: 3000
        })

        showExportDialog.value = false
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось выполнить экспорт',
          life: 3000
        })
      } finally {
        exporting.value = false
      }
    }

    const loadFilterOptions = async () => {
      try {
        const response = await apiService.getProducts({ limit: 1000 })
        const brands = new Set()
        const categories = new Set()

        response.data.forEach(product => {
          if (product.brand) brands.add(product.brand)
          if (product.category) categories.add(product.category)
        })

        brandOptions.value = Array.from(brands).map(item => ({ label: item, value: item }))
        categoryOptions.value = Array.from(categories).map(item => ({ label: item, value: item }))
      } catch (error) {
        console.error('Ошибка загрузки опций фильтров:', error)
      }
    }

    const onMappingSettingsUpdated = () => {
      toast.add({
        severity: 'success',
        summary: 'Успешно',
        detail: 'Настройки маппинга обновлены. Они будут использоваться при следующей загрузке Excel файлов.',
        life: 5000
      })
    }

    const performRestore = async () => {
      try {
        const response = await apiService.restoreDatabase()
        toast.add({
          severity: 'success',
          summary: 'Успешно',
          detail: response.data.message,
          life: 5000
        })
        showRestoreDialog.value = false
        // Перезагрузка страницы для обновления данных
        window.location.reload()
      } catch (error) {
        console.error('Ошибка восстановления:', error)
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось восстановить базу данных',
          life: 5000
        })
      }
    }

    onMounted(() => {
      loadFilterOptions()
    })

    return {
      dataEditor,
      showAddDialog,
      showExportDialog,
      showMappingSettings,
      showRestoreDialog,
      adding,
      exporting,
      newProduct,
      errors,
      exportFormat,
      selectedColumns,
      exportFilters,
      availableColumns,
      brandOptions,
      categoryOptions,
      goToFiles,
      addProduct,
      cancelAdd,
      performExport,
      performRestore,
      onMappingSettingsUpdated
    }
  }
}
</script>

<style scoped>
.data-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem;
}

.page-header {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.field {
  margin-bottom: 1.5rem;
}
</style>
