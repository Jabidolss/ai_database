<template>
  <div class="data-editor">
    <Card>
      <template #title>
        <div class="flex align-items-center justify-content-between w-full">
          <div class="flex align-items-center">
            <i class="pi pi-table mr-2"></i>
            Управление очками
          </div>
          <div class="flex gap-2">
            <Button
              label="Обновить"
              icon="pi pi-refresh"
              class="p-button-secondary"
              @click="loadProducts"
            />
            <Button
              label="Экспорт"
              icon="pi pi-download"
              class="p-button-success"
              @click="showExportDialog = true"
            />
          </div>
        </div>
      </template>

      <template #content>
        <!-- Фильтры -->
        <div class="filters-section mb-4">
          <div class="grid">
            <div class="col-12 md:col-3">
              <label class="block text-900 font-medium mb-2">Бренд</label>
              <Dropdown
                v-model="filters.brand"
                :options="brandOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Все бренды"
                :showClear="true"
                class="w-full"
                @change="applyFilters"
              />
            </div>
            <div class="col-12 md:col-3">
              <label class="block text-900 font-medium mb-2">Категория (Бренд)</label>
              <Dropdown
                v-model="filters.category"
                :options="categoryOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Все категории"
                :showClear="true"
                class="w-full"
                @change="applyFilters"
              />
            </div>
            <div class="col-12 md:col-3">
              <label class="block text-900 font-medium mb-2">Цвет</label>
              <Dropdown
                v-model="filters.color"
                :options="colorOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Все цвета"
                :showClear="true"
                class="w-full"
                @change="applyFilters"
              />
            </div>
            <div class="col-12 md:col-4">
              <label class="block text-900 font-medium mb-2">Поиск</label>
              <InputText
                v-model="filters.search"
                placeholder="Поиск по названию..."
                class="w-full"
                @input="debouncedSearch"
              />
            </div>
          </div>
        </div>

        <!-- Таблица товаров -->
        <DataTable
          :value="products"
          :paginator="true"
          :rows="50"
          :loading="loading"
          :totalRecords="totalRecords"
          :lazy="true"
          @page="onPage"
          @sort="onSort"
          selectionMode="single"
          :metaKeySelection="false"
          dataKey="id"
          class="p-datatable-sm"
          editMode="cell"
          @cell-edit-complete="onCellEditComplete"
          @row-select="onRowSelect"
          paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
          :rowsPerPageOptions="[25, 50, 100]"
          currentPageReportTemplate="Показано {first} - {last} из {totalRecords} товаров"
        >
          <template #empty>
            <div class="text-center py-4">
              <i class="pi pi-info-circle text-4xl text-300 mb-3"></i>
              <p class="text-500">Нет данных для отображения</p>
            </div>
          </template>

          <Column selectionMode="single" headerStyle="width: 3rem"></Column>

          <Column field="id" header="ID" :sortable="true" style="width: 80px">
            <template #body="slotProps">
              <span class="font-monospace">{{ slotProps.data.id }}</span>
            </template>
          </Column>

          <Column field="part_number" header="Номер детали" :sortable="true" style="min-width: 150px">
            <template #editor="{ data, field }">
              <InputText v-model="data[field]" class="w-full" />
            </template>
          </Column>

          <Column field="part_name" header="Название" :sortable="true" style="min-width: 200px">
            <template #editor="{ data, field }">
              <InputText v-model="data[field]" class="w-full" />
            </template>
          </Column>

          <Column field="brand" header="Бренд" :sortable="true" style="min-width: 120px">
            <template #editor="{ data, field }">
              <InputText v-model="data[field]" class="w-full" />
            </template>
          </Column>

          <Column field="category" header="Категория" :sortable="true" style="min-width: 120px">
            <template #editor="{ data, field }">
              <InputText v-model="data[field]" class="w-full" />
            </template>
          </Column>

          <Column field="color" header="Цвет" :sortable="true" style="min-width: 100px">
            <template #editor="{ data, field }">
              <InputText v-model="data[field]" class="w-full" />
            </template>
          </Column>

          <Column field="size" header="Размер" :sortable="true" style="min-width: 100px">
            <template #editor="{ data, field }">
              <InputText v-model="data[field]" class="w-full" />
            </template>
          </Column>

          <Column field="year" header="Год" :sortable="true" style="width: 80px">
            <template #editor="{ data, field }">
              <InputNumber v-model="data[field]" :min="1900" :max="2030" />
            </template>
          </Column>

          <Column field="images" header="Изображения" style="min-width: 150px">
            <template #body="slotProps">
              <div v-if="slotProps.data.images" class="images-preview">
                <div
                  v-for="image in slotProps.data.images.split(',')"
                  :key="image"
                  class="image-item"
                >
                  <img :src="image" alt="Товар" class="product-image" @click="openImageModal(image)" />
                </div>
              </div>
              <span v-else class="text-500">Нет изображений</span>
            </template>
          </Column>

          <Column header="Действия" style="width: 120px">
            <template #body="slotProps">
              <div class="flex gap-1">
                <Button
                  icon="pi pi-pencil"
                  class="p-button-rounded p-button-text p-button-info"
                  @click="editProduct(slotProps.data)"
                  v-tooltip.top="'Редактировать'"
                />
                <Button
                  icon="pi pi-trash"
                  class="p-button-rounded p-button-text p-button-danger"
                  @click="confirmDelete(slotProps.data)"
                  v-tooltip.top="'Удалить'"
                />
              </div>
            </template>
          </Column>
        </DataTable>

        <!-- Диалог редактирования товара -->
        <Dialog
          v-model:visible="editDialogVisible"
          modal
          header="Редактирование товара"
          :style="{ width: '50rem' }"
          :closable="true"
        >
          <div v-if="selectedProduct" class="p-fluid">
            <div class="grid">
              <div class="col-12 md:col-6">
                <label class="block text-900 font-medium mb-2">Номер детали</label>
                <InputText v-model="selectedProduct.part_number" />
              </div>
              <div class="col-12 md:col-6">
                <label class="block text-900 font-medium mb-2">Название</label>
                <InputText v-model="selectedProduct.part_name" />
              </div>
              <div class="col-12 md:col-6">
                <label class="block text-900 font-medium mb-2">Бренд</label>
                <InputText v-model="selectedProduct.brand" />
              </div>
              <div class="col-12 md:col-6">
                <label class="block text-900 font-medium mb-2">Категория</label>
                <InputText v-model="selectedProduct.category" />
              </div>
              <div class="col-12 md:col-6">
                <label class="block text-900 font-medium mb-2">Цвет</label>
                <InputText v-model="selectedProduct.color" />
              </div>
              <div class="col-12 md:col-6">
                <label class="block text-900 font-medium mb-2">Размер</label>
                <InputText v-model="selectedProduct.size" />
              </div>
              <div class="col-12 md:col-6">
                <label class="block text-900 font-medium mb-2">Год</label>
                <InputNumber v-model="selectedProduct.year" :min="1900" :max="2030" />
              </div>
              <div class="col-12">
                <label class="block text-900 font-medium mb-2">Изображения (URL через запятую)</label>
                <Textarea v-model="selectedProduct.images" :autoResize="true" rows="3" />
              </div>
            </div>
          </div>

          <template #footer>
            <Button
              label="Отмена"
              icon="pi pi-times"
              class="p-button-text"
              @click="editDialogVisible = false"
            />
            <Button
              label="Сохранить"
              icon="pi pi-check"
              class="p-button-primary"
              :loading="saving"
              @click="saveProduct"
            />
          </template>
        </Dialog>

        <!-- Диалог подтверждения удаления -->
        <Dialog
          v-model:visible="deleteDialogVisible"
          modal
          header="Подтверждение удаления"
          :style="{ width: '30rem' }"
        >
          <p>Вы действительно хотите удалить товар "{{ selectedProduct?.part_name }}"?</p>

          <template #footer>
            <Button
              label="Отмена"
              icon="pi pi-times"
              class="p-button-text"
              @click="deleteDialogVisible = false"
            />
            <Button
              label="Удалить"
              icon="pi pi-trash"
              class="p-button-danger"
              :loading="deleting"
              @click="deleteProduct"
            />
          </template>
        </Dialog>

        <!-- Диалог просмотра изображения -->
        <Dialog
          v-model:visible="imageDialogVisible"
          modal
          :header="'Изображение товара'"
          :style="{ width: 'auto' }"
          :closable="true"
        >
          <img v-if="selectedImage" :src="selectedImage" alt="Товар" class="modal-image" />
        </Dialog>

        <!-- Диалог экспорта -->
        <ExportDialog v-model:visible="showExportDialog" />
      </template>
    </Card>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import ExportDialog from './ExportDialog.vue'
import { useToast } from 'primevue/usetoast'
import apiService from '../services/apiService'

export default {
  name: 'DataEditor',
  components: {
    Card,
    DataTable,
    Column,
    Button,
    InputText,
    InputNumber,
    Dropdown,
    Dialog,
    Textarea,
    ExportDialog
  },
  setup() {
    const toast = useToast()
    const products = ref([])
    const loading = ref(false)
    const totalRecords = ref(0)
    const selectedProduct = ref(null)
    const editDialogVisible = ref(false)
    const deleteDialogVisible = ref(false)
    const imageDialogVisible = ref(false)
    const showExportDialog = ref(false)
    const selectedImage = ref('')
    const saving = ref(false)
    const deleting = ref(false)

    const filters = reactive({
      brand: null,
      category: null,
      color: null,
      search: '',
      page: 0,
      size: 50,
      sortField: null,
      sortOrder: null
    })

    const brandOptions = ref([])
    const categoryOptions = ref([])
    const colorOptions = ref([])

    const loadFilterOptions = async () => {
      try {
        const response = await apiService.getFilterOptions()
        const data = response.data
        
        brandOptions.value = data.brands.map(item => ({ label: item, value: item }))
        categoryOptions.value = data.categories.map(item => ({ label: item, value: item }))
        colorOptions.value = data.colors.map(item => ({ label: item, value: item }))
      } catch (error) {
        console.error('Error loading filter options:', error)
      }
    }

    const loadProducts = async () => {
      loading.value = true
      try {
        const params = {
          brand: filters.brand,
          category: filters.category,
          color: filters.color,
          search: filters.search,
          limit: filters.size,
          offset: filters.page * filters.size
        }

        if (filters.sortField) {
          params.sort_field = filters.sortField
          params.sort_order = filters.sortOrder === 1 ? 'asc' : 'desc'
        }

        const response = await apiService.getProducts(params)
        
        // Обновляем данные с учетом новой структуры ответа
        if (response.data.products) {
          products.value = response.data.products
          totalRecords.value = response.data.total_count
        } else {
          // Поддержка старого формата для совместимости
          products.value = response.data
          totalRecords.value = response.data.length
        }
      } catch (error) {
        console.error('Error loading products:', error)
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось загрузить товары',
          life: 3000
        })
      } finally {
        loading.value = false
      }
    }

    const updateFilterOptions = (data) => {
      // Удаляем эту функцию, так как теперь используем отдельный API endpoint
    }

    const applyFilters = () => {
      filters.page = 0
      loadProducts()
    }

    const debouncedSearch = (() => {
      let timeout
      return () => {
        clearTimeout(timeout)
        timeout = setTimeout(() => {
          applyFilters()
        }, 500)
      }
    })()

    const onPage = (event) => {
      filters.page = event.page
      filters.size = event.rows
      loadProducts()
    }

    const onSort = (event) => {
      filters.sortField = event.sortField
      filters.sortOrder = event.sortOrder
      loadProducts()
    }

    const onRowSelect = (event) => {
      selectedProduct.value = { ...event.data }
    }

    const onCellEditComplete = async (event) => {
      const { data, newValue, field } = event
      if (newValue !== data[field]) {
        try {
          await apiService.updateProduct(data.id, { [field]: newValue })
          toast.add({
            severity: 'success',
            summary: 'Успешно',
            detail: 'Данные обновлены',
            life: 2000
          })
          loadProducts()
        } catch (error) {
          toast.add({
            severity: 'error',
            summary: 'Ошибка',
            detail: 'Не удалось обновить данные',
            life: 3000
          })
        }
      }
    }

    const editProduct = (product) => {
      selectedProduct.value = { ...product }
      editDialogVisible.value = true
    }

    const saveProduct = async () => {
      if (!selectedProduct.value) return

      saving.value = true
      try {
        await apiService.updateProduct(selectedProduct.value.id, selectedProduct.value)
        editDialogVisible.value = false
        loadProducts()
        toast.add({
          severity: 'success',
          summary: 'Успешно',
          detail: 'Товар обновлен',
          life: 2000
        })
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось сохранить изменения',
          life: 3000
        })
      } finally {
        saving.value = false
      }
    }

    const confirmDelete = (product) => {
      selectedProduct.value = product
      deleteDialogVisible.value = true
    }

    const deleteProduct = async () => {
      if (!selectedProduct.value) return

      deleting.value = true
      try {
        await apiService.deleteProduct(selectedProduct.value.id)
        deleteDialogVisible.value = false
        loadProducts()
        toast.add({
          severity: 'success',
          summary: 'Успешно',
          detail: 'Товар удален',
          life: 2000
        })
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось удалить товар',
          life: 3000
        })
      } finally {
        deleting.value = false
      }
    }

    const openImageModal = (imageUrl) => {
      selectedImage.value = imageUrl
      imageDialogVisible.value = true
    }

    onMounted(() => {
      loadFilterOptions()
      loadProducts()
    })

    return {
      products,
      loading,
      totalRecords,
      selectedProduct,
      editDialogVisible,
      deleteDialogVisible,
      imageDialogVisible,
      showExportDialog,
      selectedImage,
      saving,
      deleting,
      filters,
      brandOptions,
      categoryOptions,
      colorOptions,
      loadProducts,
      applyFilters,
      debouncedSearch,
      onPage,
      onSort,
      onRowSelect,
      onCellEditComplete,
      editProduct,
      saveProduct,
      confirmDelete,
      deleteProduct,
      openImageModal
    }
  }
}
</script>

<style scoped>
.data-editor {
  max-width: 1400px;
  margin: 0 auto;
}

.filters-section {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.images-preview {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.image-item {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #e9ecef;
}

.product-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
  transition: transform 0.2s;
}

.product-image:hover {
  transform: scale(1.1);
}

.modal-image {
  max-width: 100%;
  max-height: 500px;
  object-fit: contain;
}

.font-monospace {
  font-family: 'Courier New', monospace;
}

/* Стили для таблицы без скролла */
:deep(.p-datatable) {
  overflow: visible;
}

:deep(.p-datatable .p-datatable-tbody > tr > td) {
  padding: 0.75rem 0.5rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

:deep(.p-datatable .p-datatable-thead > tr > th) {
  padding: 0.75rem 0.5rem;
  white-space: nowrap;
}

/* Компактные стили для таблицы */
:deep(.p-datatable-sm .p-datatable-tbody > tr > td) {
  padding: 0.5rem 0.25rem;
  font-size: 0.875rem;
}

:deep(.p-datatable-sm .p-datatable-thead > tr > th) {
  padding: 0.5rem 0.25rem;
  font-size: 0.875rem;
}
</style>
