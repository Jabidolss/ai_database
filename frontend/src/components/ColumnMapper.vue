<template>
  <div class="column-mapper">
    <Card>
      <template #title>
        <div class="flex align-items-center">
          <i class="pi pi-sitemap mr-2"></i>
          Маппинг колонок Excel
        </div>
      </template>

      <template #content>
        <div v-if="!columns || columns.length === 0" class="empty-state">
          <div class="text-center py-4">
            <i class="pi pi-file-excel text-4xl text-green-400 mb-3"></i>
            <h4 class="text-600 mb-2">Файл не загружен</h4>
            <p class="text-500">Загрузите Excel файл для настройки маппинга колонок</p>
          </div>
        </div>

        <div v-else>
          <!-- Информация о структуре файла -->
          <div v-if="structureInfo" class="structure-info mb-4">
            <Card>
              <template #title>
                <div class="flex align-items-center">
                  <i class="pi pi-info-circle mr-2"></i>
                  Структура файла
                </div>
              </template>
              <template #content>
                <div class="grid">
                  <div class="col-12 md:col-3">
                    <div class="stat-card">
                      <div class="stat-number text-blue-600">{{ structureInfo.header_row + 1 }}</div>
                      <div class="stat-label">Строка заголовков</div>
                    </div>
                  </div>
                  <div class="col-12 md:col-3">
                    <div class="stat-card">
                      <div class="stat-number text-green-600">{{ structureInfo.total_rows }}</div>
                      <div class="stat-label">Всего строк</div>
                    </div>
                  </div>
                  <div class="col-12 md:col-3">
                    <div class="stat-card">
                      <div class="stat-number text-purple-600">{{ structureInfo.total_columns }}</div>
                      <div class="stat-label">Всего колонок</div>
                    </div>
                  </div>
                  <div class="col-12 md:col-3">
                    <div class="stat-card">
                      <div class="stat-number" :class="structureInfo.has_images ? 'text-orange-600' : 'text-gray-500'">
                        <i :class="structureInfo.has_images ? 'pi pi-image' : 'pi pi-times'"></i>
                      </div>
                      <div class="stat-label">Изображения</div>
                    </div>
                  </div>
                </div>
                
                <!-- Показываем извлеченные изображения если есть -->
                <div v-if="extractedImages && Object.keys(extractedImages).length > 0" class="mt-4">
                  <h3 class="text-900 mb-3">Извлеченные изображения ({{ Object.keys(extractedImages).length }})</h3>
                  <div class="image-preview-grid">
                    <div 
                      v-for="(imageData, imageName) in extractedImages" 
                      :key="imageName"
                      class="image-preview-item"
                    >
                      <img 
                        :src="`data:image/jpeg;base64,${imageData}`" 
                        :alt="imageName"
                        class="preview-image"
                      />
                      <div class="image-name">{{ imageName }}</div>
                    </div>
                  </div>
                </div>
              </template>
            </Card>
          </div>

          <!-- Примеры данных -->
          <div v-if="sampleData && sampleData.length > 0" class="sample-data mb-4">
            <Card>
              <template #title>
                <div class="flex align-items-center">
                  <i class="pi pi-eye mr-2"></i>
                  Предварительный просмотр данных
                </div>
              </template>
              <template #content>
                <DataTable 
                  :value="sampleData" 
                  class="p-datatable-sm"
                  :scrollable="true"
                  scrollHeight="200px"
                >
                  <Column 
                    v-for="column in Object.keys(sampleData[0] || {})" 
                    :key="column"
                    :field="column" 
                    :header="column"
                    style="min-width: 150px"
                  >
                    <template #body="slotProps">
                      <span class="sample-data-cell">
                        {{ formatSampleValue(slotProps.data[column]) }}
                      </span>
                    </template>
                  </Column>
                </DataTable>
              </template>
            </Card>
          </div>

          <div class="mapping-info mb-4">
            <Message severity="info" :closable="false">
              <div class="flex align-items-start">
                <i class="pi pi-info-circle mr-2 mt-1"></i>
                <div>
                  <strong>ИИ предложил маппинг колонок.</strong>
                  <br>
                  Проверьте соответствия и скорректируйте при необходимости.
                  Незамаппенные колонки будут пропущены при импорте.
                </div>
              </div>
            </Message>
          </div>

          <div class="mapping-stats mb-3">
            <div class="grid">
              <div class="col-12 md:col-4">
                <div class="stat-card">
                  <div class="stat-number text-green-600">{{ mappedCount }}</div>
                  <div class="stat-label">Определено</div>
                </div>
              </div>
              <div class="col-12 md:col-4">
                <div class="stat-card">
                  <div class="stat-number text-orange-600">{{ unmappedCount }}</div>
                  <div class="stat-label">Ненайдено</div>
                </div>
              </div>
              <div class="col-12 md:col-4">
                <div class="stat-card">
                  <div class="stat-number text-blue-600">{{ totalColumns }}</div>
                  <div class="stat-label">Всего колонок</div>
                </div>
              </div>
            </div>
          </div>

          <div class="mapping-table">
            <DataTable
              :value="mappingItems"
              :paginator="false"
              class="p-datatable-sm mapping-table-full"
              :scrollable="false"
            >
              <Column field="excelColumn" header="Колонка Excel" style="min-width: 200px">
                <template #body="slotProps">
                  <div class="excel-column">
                    <i class="pi pi-file-excel text-green-500 mr-2"></i>
                    <strong>{{ slotProps.data.excelColumn }}</strong>
                    <Badge
                      v-if="slotProps.data.sampleData"
                      :value="slotProps.data.sampleData"
                      severity="info"
                      class="ml-2"
                    />
                  </div>
                </template>
              </Column>

              <Column field="dbField" header="Поле базы данных" style="min-width: 200px">
                <template #body="slotProps">
                  <Dropdown
                    v-model="slotProps.data.dbField"
                    :options="dbFields"
                    optionLabel="label"
                    optionValue="value"
                    placeholder="Выберите поле БД"
                    :showClear="true"
                    class="w-full"
                    @change="onMappingChange(slotProps.data, $event)"
                  >
                    <template #option="slotProps">
                      <div class="db-field-option">
                        <i :class="getFieldIcon(slotProps.option.value)" class="mr-2"></i>
                        <span>{{ slotProps.option.label }}</span>
                        <Badge
                          v-if="slotProps.option.type"
                          :value="slotProps.option.type"
                          severity="secondary"
                          class="ml-auto"
                        />
                      </div>
                    </template>
                  </Dropdown>
                </template>
              </Column>

              <Column header="Тип данных" style="width: 120px">
                <template #body="slotProps">
                  <Badge
                    v-if="slotProps.data.dbField"
                    :value="getFieldType(slotProps.data.dbField)"
                    :severity="getTypeSeverity(slotProps.data.dbField)"
                  />
                  <span v-else class="text-500">-</span>
                </template>
              </Column>

              <Column header="Статус" style="width: 120px">
                <template #body="slotProps">
                  <Badge
                    :value="slotProps.data.dbField ? 'Определено' : 'Ненайдено'"
                    :severity="slotProps.data.dbField ? 'success' : 'warning'"
                  />
                </template>
              </Column>

              <Column header="Действия" style="width: 100px">
                <template #body="slotProps">
                  <Button
                    icon="pi pi-trash"
                    class="p-button-rounded p-button-text p-button-danger"
                    @click="removeMapping(slotProps.data)"
                    v-tooltip.top="'Удалить маппинг'"
                  />
                </template>
              </Column>
            </DataTable>
          </div>

          <div class="mapping-actions mt-4 flex justify-content-between align-items-center">
            <div class="flex gap-2">
              <Button
                label="Настройки маппинга"
                icon="pi pi-cog"
                class="p-button-secondary"
                @click="showMappingSettings"
              />
              <Button
                label="Добавить маппинг"
                icon="pi pi-plus"
                class="p-button-secondary"
                @click="addCustomMapping"
              />
              <Button
                label="Очистить все"
                icon="pi pi-times"
                class="p-button-secondary p-button-outlined"
                @click="clearAllMappings"
              />
            </div>

            <div class="flex gap-2">
              <Button
                label="Предпросмотр"
                icon="pi pi-eye"
                class="p-button-info"
                @click="showPreview"
              />
              <Button
                label="Применить"
                icon="pi pi-check"
                class="p-button-success"
                :disabled="!hasValidMappings || isLoading"
                :loading="isLoading"
                @click="applyMappings"
              />
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Диалог предпросмотра -->
    <Dialog
      v-model:visible="previewDialogVisible"
      modal
      header="Предпросмотр данных"
      :style="{ width: '80rem' }"
      :closable="true"
    >
      <div v-if="previewData.length > 0">
        <div class="mb-3">
          <small class="text-600">Показаны первые 5 строк данных</small>
        </div>
        <DataTable
          :value="previewData"
          :scrollable="true"
          scrollHeight="300px"
          class="p-datatable-sm"
        >
          <Column
            v-for="col in previewColumns"
            :key="col"
            :field="col"
            :header="col"
            style="min-width: 120px"
          />
        </DataTable>
      </div>
      <div v-else class="text-center py-4">
        <p class="text-500">Нет данных для предпросмотра</p>
      </div>
    </Dialog>

    <!-- Диалог настроек маппинга -->
    <MappingSettings
      v-model="mappingSettingsVisible"
      @settings-updated="onMappingSettingsUpdated"
    />
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Badge from 'primevue/badge'
import MappingSettings from './MappingSettings.vue'

export default {
  name: 'ColumnMapper',
  components: {
    Card,
    DataTable,
    Column,
    Button,
    Dropdown,
    Dialog,
    Message,
    Badge,
    MappingSettings
  },
  props: {
    columns: {
      type: Array,
      default: () => []
    },
    initialMapping: {
      type: Object,
      default: () => ({})
    },
    sampleData: {
      type: Array,
      default: () => []
    },
    structureInfo: {
      type: Object,
      default: () => null
    },
    extractedImages: {
      type: Object,
      default: () => ({})
    },
    isLoading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['mapping-changed', 'apply-mappings'],
  setup(props, { emit }) {
    const toast = useToast()
    const mappingItems = ref([])
    const previewDialogVisible = ref(false)
    const previewData = ref([])
    const previewColumns = ref([])
    const mappingSettingsVisible = ref(false)

    const dbFields = [
      { label: 'Название производителя', value: 'manufacturer_name', type: 'VARCHAR' },
      { label: 'Номер детали', value: 'part_number', type: 'VARCHAR' },
      { label: 'Название детали', value: 'part_name', type: 'VARCHAR' },
      { label: 'Категория', value: 'category', type: 'VARCHAR' },
      { label: 'Тип', value: 'type', type: 'VARCHAR' },
      { label: 'Размер', value: 'size', type: 'VARCHAR' },
      { label: 'Цвет', value: 'color', type: 'VARCHAR' },
      { label: 'Бренд', value: 'brand', type: 'VARCHAR' },
      { label: 'Производитель', value: 'producer', type: 'VARCHAR' },
      { label: 'Пол', value: 'gender', type: 'VARCHAR' },
      { label: 'Ширина', value: 'width', type: 'NUMERIC' },
      { label: 'Высота', value: 'height', type: 'NUMERIC' },
      { label: 'Возраст', value: 'age', type: 'VARCHAR' },
      { label: 'Форма', value: 'shape', type: 'VARCHAR' },
      { label: 'Год', value: 'year', type: 'INTEGER' },
      { label: 'Изображения', value: 'images', type: 'TEXT' }
    ]

    const mappedCount = computed(() => {
      return mappingItems.value.filter(item => item.dbField).length
    })

    const unmappedCount = computed(() => {
      return mappingItems.value.filter(item => !item.dbField).length
    })

    const totalColumns = computed(() => {
      return mappingItems.value.length
    })

    const hasValidMappings = computed(() => {
      return mappingItems.value.some(item => item.dbField)
    })

    const initializeMappings = () => {
      if (props.columns && props.columns.length > 0) {
        mappingItems.value = props.columns.map(col => ({
          excelColumn: col,
          dbField: props.initialMapping[col] || '',
          sampleData: getSampleData(col)
        }))
      }
    }

    const getSampleData = (column) => {
      if (props.sampleData && props.sampleData.length > 0) {
        const sampleRow = props.sampleData[0]
        return sampleRow[column] ? String(sampleRow[column]).substring(0, 20) + '...' : ''
      }
      return ''
    }

    const onMappingChange = (item, event) => {
      item.dbField = event.value
      emit('mapping-changed', {
        excelColumn: item.excelColumn,
        dbField: item.dbField
      })
    }

    const addCustomMapping = () => {
      mappingItems.value.push({
        excelColumn: `Колонка ${mappingItems.value.length + 1}`,
        dbField: '',
        sampleData: ''
      })
    }

    const removeMapping = (item) => {
      const index = mappingItems.value.findIndex(m => m.excelColumn === item.excelColumn)
      if (index > -1) {
        mappingItems.value.splice(index, 1)
        emit('mapping-changed', {
          excelColumn: item.excelColumn,
          dbField: ''
        })
      }
    }

    const clearAllMappings = () => {
      mappingItems.value.forEach(item => {
        item.dbField = ''
      })
      emit('mapping-changed', { clearAll: true })
    }

    const showPreview = () => {
      if (props.sampleData && props.sampleData.length > 0) {
        previewData.value = props.sampleData.slice(0, 5)
        previewColumns.value = Object.keys(props.sampleData[0])
        previewDialogVisible.value = true
      } else {
        toast.add({
          severity: 'warn',
          summary: 'Предупреждение',
          detail: 'Нет данных для предпросмотра',
          life: 3000
        })
      }
    }

    const applyMappings = () => {
      const finalMapping = {}
      mappingItems.value.forEach(item => {
        if (item.dbField) {
          finalMapping[item.excelColumn] = item.dbField
        }
      })

      emit('apply-mappings', finalMapping)
    }

    const getFieldIcon = (fieldValue) => {
      const iconMap = {
        manufacturer_name: 'pi pi-building',
        part_number: 'pi pi-hashtag',
        part_name: 'pi pi-tag',
        category: 'pi pi-folder',
        type: 'pi pi-cog',
        size: 'pi pi-expand',
        color: 'pi pi-palette',
        brand: 'pi pi-star',
        producer: 'pi pi-industry',
        gender: 'pi pi-users',
        width: 'pi pi-arrows-h',
        height: 'pi pi-arrows-v',
        age: 'pi pi-calendar',
        shape: 'pi pi-shape',
        year: 'pi pi-calendar-plus',
        images: 'pi pi-images'
      }
      return iconMap[fieldValue] || 'pi pi-circle'
    }

    const getFieldType = (fieldValue) => {
      const field = dbFields.find(f => f.value === fieldValue)
      return field ? field.type : ''
    }

    const formatSampleValue = (value) => {
      if (value === null || value === undefined) {
        return '—'
      }
      
      const strValue = String(value)
      if (strValue.length > 50) {
        return strValue.substring(0, 50) + '...'
      }
      
      return strValue
    }

    const getTypeSeverity = (fieldValue) => {
      const type = getFieldType(fieldValue)
      switch (type) {
        case 'VARCHAR': return 'info'
        case 'TEXT': return 'success'
        case 'NUMERIC': return 'warning'
        case 'INTEGER': return 'help'
        default: return 'secondary'
      }
    }

    const showMappingSettings = () => {
      mappingSettingsVisible.value = true
    }

    const onMappingSettingsUpdated = () => {
      toast.add({
        severity: 'success',
        summary: 'Успешно',
        detail: 'Настройки маппинга обновлены. Они будут использоваться при следующей загрузке файлов.',
        life: 5000
      })
    }

    watch(() => props.columns, initializeMappings, { immediate: true })
    watch(() => props.initialMapping, initializeMappings)

    return {
      mappingItems,
      previewDialogVisible,
      previewData,
      previewColumns,
      dbFields,
      mappedCount,
      unmappedCount,
      totalColumns,
      hasValidMappings,
      mappingSettingsVisible,
      onMappingChange,
      addCustomMapping,
      removeMapping,
      clearAllMappings,
      showPreview,
      applyMappings,
      getFieldIcon,
      getFieldType,
      getTypeSeverity,
      formatSampleValue,
      showMappingSettings,
      onMappingSettingsUpdated
    }
  }
}
</script>

<style scoped>
.column-mapper {
  max-width: 1200px;
  margin: 0 auto;
}

.empty-state {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mapping-stats {
  margin-bottom: 1rem;
}

.stat-card {
  background: white;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  text-align: center;
}

.stat-number {
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.stat-label {
  color: #6c757d;
  font-size: 0.9rem;
}

.mapping-table {
  margin-top: 1rem;
}

.excel-column {
  display: flex;
  align-items: center;
}

.db-field-option {
  display: flex;
  align-items: center;
  width: 100%;
}

.mapping-actions {
  border-top: 1px solid #e9ecef;
  padding-top: 1rem;
}

.image-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.image-preview-item {
  text-align: center;
}

.preview-image {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 8px;
  border: 2px solid #e9ecef;
  transition: border-color 0.3s;
}

.preview-image:hover {
  border-color: #007bff;
}

.image-name {
  font-size: 0.8rem;
  color: #6c757d;
  margin-top: 0.5rem;
  word-break: break-word;
}

.sample-data-cell {
  font-family: monospace;
  font-size: 0.9rem;
}

.structure-info .stat-card {
  text-align: center;
  padding: 1rem;
}

/* Стили для полноразмерной таблицы маппинга */
.mapping-table-full {
  width: 100% !important;
}

.mapping-table-full .p-datatable-wrapper {
  border-radius: 8px;
  overflow: visible !important;
}

.mapping-table-full .p-datatable-table {
  width: 100% !important;
}

/* Убираем фиксированную высоту для полного отображения всех строк */
.mapping-table-full .p-datatable-scrollable-body {
  max-height: none !important;
  overflow: visible !important;
}

/* Стили для лучшего отображения строк */
.mapping-table-full .p-datatable-tbody > tr {
  border-bottom: 1px solid var(--surface-200);
}

.mapping-table-full .p-datatable-tbody > tr:last-child {
  border-bottom: none;
}

/* Адаптивный отступ для таблицы */
.mapping-table {
  margin-bottom: 2rem;
}
</style>
