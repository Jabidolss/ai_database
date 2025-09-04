<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Настройки маппинга колонок"
    :style="{ width: '80vw', height: '80vh' }"
    :maximizable="true"
    @update:visible="onDialogClose"
    class="mapping-settings-dialog"
  >
    <div class="mapping-settings-container">
      <div class="toolbar mb-4">
        <div class="flex justify-content-between align-items-center">
          <div>
            <h1 class="text-900 mb-1">Правила маппинга для колонок базы данных</h1>
            <p class="text-600 mt-1 mb-0">
              Добавляйте ключевые слова для автоматического определения соответствий колонок Excel
            </p>
          </div>
          <div class="flex gap-2">
            <Button
              label="Сбросить по умолчанию"
              icon="pi pi-refresh"
              severity="secondary"
              @click="loadDefaultSettings"
              :loading="isResetting"
            />
            <Button
              label="Сохранить все"
              icon="pi pi-save"
              @click="saveAllSettings"
              :loading="isSaving"
            />
          </div>
        </div>
      </div>

      <div class="settings-grid">
        <DataTable
          ref="dataTable"
          :value="mappingSettings"
          :paginator="false"
          class="p-datatable-sm adaptive-table"
          :scrollable="true"
          scrollHeight="flex"
        >
          <Column field="db_column" header="Колонка БД" style="width: 200px">
            <template #body="slotProps">
              <div class="flex align-items-center">
                <i :class="getFieldIcon(slotProps.data.db_column)" class="mr-2"></i>
                <div>
                  <strong class="field-label">{{ getFieldLabel(slotProps.data.db_column) }}</strong>
                  <div class="text-xs text-600 field-description">{{ slotProps.data.db_column }}</div>
                </div>
              </div>
            </template>
          </Column>

          <Column field="excel_patterns" header="Ключевые слова" style="min-width: 400px">
            <template #body="slotProps">
              <div class="patterns-display">
                <Chip
                  v-for="(pattern, index) in slotProps.data.excel_patterns"
                  :key="index"
                  :label="pattern"
                  class="mr-1 mb-1"
                  :removable="false"
                />
                <div v-if="slotProps.data.excel_patterns.length === 0" class="text-500">
                  <i class="pi pi-info-circle mr-1"></i>
                  Нет ключевых слов
                </div>
              </div>
            </template>
          </Column>

          <Column header="Действия" style="width: 120px">
            <template #body="slotProps">
              <div class="flex gap-1">
                <Button
                  icon="pi pi-pencil"
                  size="small"
                  @click="openPatternEditor(slotProps.data)"
                  title="Редактировать ключевые слова"
                />
                <Button
                  icon="pi pi-times"
                  size="small"
                  severity="danger"
                  @click="clearPatterns(slotProps.data)"
                  title="Очистить все ключевые слова"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-content-end">
        <Button
          label="Закрыть"
          icon="pi pi-times"
          @click="closeDialog"
        />
      </div>
    </template>
  </Dialog>

  <!-- Диалог редактирования ключевых слов -->
  <Dialog
    v-model:visible="editPatternDialog"
    modal
    :header="`Редактирование: ${editingColumnLabel}`"
    :style="{ width: '600px' }"
  >
    <div class="p-4">
      <label for="patterns-input" class="block text-sm font-medium mb-2">
        Ключевые слова (через запятую):
      </label>
      <InputText
        id="patterns-input"
        v-model="editingPatterns"
        class="w-full"
        placeholder="Введите ключевые слова через запятую..."
        @keyup.enter="savePatterns"
      />
      <small class="text-500 mt-1 block">
        Пример: название, наименование, продукт, товар
      </small>
    </div>
    
    <template #footer>
      <div class="flex justify-content-end gap-2">
        <Button
          label="Отмена"
          icon="pi pi-times"
          severity="secondary"
          @click="cancelPatternEdit"
        />
        <Button
          label="Сохранить"
          icon="pi pi-check"
          @click="savePatterns"
          :loading="isSavingPattern"
        />
      </div>
    </template>
  </Dialog>
</template>

<script>
import { ref, reactive, watch, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Chip from 'primevue/chip'
import apiService from '@/services/apiService'

export default {
  name: 'MappingSettings',
  components: {
    Dialog,
    DataTable,
    Column,
    Button,
    InputText,
    Chip
  },
  props: {
    modelValue: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue', 'settings-updated'],
  setup(props, { emit }) {
    const toast = useToast()
    const dataTable = ref()
    const visible = ref(props.modelValue)
    const mappingSettings = ref([])
    const editingRows = reactive({})
    const newPattern = ref('')
    const isSaving = ref(false)
    const isResetting = ref(false)
    const isLoading = ref(false)
    
    // Переменные для диалога редактирования паттернов
    const editPatternDialog = ref(false)
    const editingPatterns = ref('')
    const editingColumnData = ref(null)
    const editingColumnLabel = ref('')
    const isSavingPattern = ref(false)

    // Определения полей БД
    const dbFieldDefinitions = {
      manufacturer_name: { label: 'Название производителя', icon: 'pi pi-building' },
      part_number: { label: 'Номер детали', icon: 'pi pi-hashtag' },
      part_name: { label: 'Название детали', icon: 'pi pi-tag' },
      category: { label: 'Категория', icon: 'pi pi-folder' },
      type: { label: 'Тип', icon: 'pi pi-cog' },
      size: { label: 'Размер', icon: 'pi pi-expand' },
      color: { label: 'Цвет', icon: 'pi pi-palette' },
      brand: { label: 'Бренд', icon: 'pi pi-star' },
      producer: { label: 'Производитель', icon: 'pi pi-industry' },
      gender: { label: 'Пол', icon: 'pi pi-users' },
      width: { label: 'Ширина', icon: 'pi pi-arrows-h' },
      height: { label: 'Высота', icon: 'pi pi-arrows-v' },
      age: { label: 'Возраст', icon: 'pi pi-calendar' },
      shape: { label: 'Форма', icon: 'pi pi-shape' },
      year: { label: 'Год', icon: 'pi pi-calendar-plus' },
      images: { label: 'Изображения', icon: 'pi pi-images' }
    }

    const getFieldLabel = (dbColumn) => {
      return dbFieldDefinitions[dbColumn]?.label || dbColumn
    }

    const getFieldIcon = (dbColumn) => {
      return dbFieldDefinitions[dbColumn]?.icon || 'pi pi-circle'
    }

    const loadMappingSettings = async () => {
      try {
        isLoading.value = true
        const settings = await apiService.getMappingSettings()
        
        // Создаем настройки для всех колонок БД
        const allColumns = Object.keys(dbFieldDefinitions)
        mappingSettings.value = allColumns.map(column => {
          const existing = settings.find(s => s.db_column === column)
          return {
            db_column: column,
            excel_patterns: existing ? existing.excel_patterns : [],
            id: existing ? existing.id : null
          }
        })
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось загрузить настройки маппинга',
          life: 5000
        })
      } finally {
        isLoading.value = false
      }
    }

    const saveAllSettings = async () => {
      try {
        isSaving.value = true
        
        for (const setting of mappingSettings.value) {
          if (setting.excel_patterns.length > 0) {
            if (setting.id) {
              await apiService.updateMappingSetting(setting.id, {
                excel_patterns: setting.excel_patterns
              })
            } else {
              const created = await apiService.createMappingSetting({
                db_column: setting.db_column,
                excel_patterns: setting.excel_patterns
              })
              setting.id = created.id
            }
          }
        }

        toast.add({
          severity: 'success',
          summary: 'Успешно',
          detail: 'Настройки маппинга сохранены',
          life: 3000
        })

        emit('settings-updated')
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось сохранить настройки',
          life: 5000
        })
      } finally {
        isSaving.value = false
      }
    }

    const loadDefaultSettings = async () => {
      try {
        isResetting.value = true
        await apiService.createDefaultMappingSettings()
        await loadMappingSettings()
        
        toast.add({
          severity: 'success',
          summary: 'Успешно',
          detail: 'Настройки по умолчанию загружены',
          life: 3000
        })
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось загрузить настройки по умолчанию',
          life: 5000
        })
      } finally {
        isResetting.value = false
      }
    }

    const addPattern = (setting) => {
      if (newPattern.value?.trim()) {
        if (!setting.excel_patterns.includes(newPattern.value.trim())) {
          setting.excel_patterns.push(newPattern.value.trim())
          newPattern.value = ''
        }
      }
    }

    const removePattern = (setting, index) => {
      setting.excel_patterns.splice(index, 1)
    }

    const clearPatterns = async (setting) => {
      setting.excel_patterns = []
      // Автосохранение после очистки
      await saveSingleSetting(setting)
    }

    // Новые функции для диалога редактирования паттернов
    const openPatternEditor = (data) => {
      editingColumnData.value = data
      editingColumnLabel.value = getFieldLabel(data.db_column)
      editingPatterns.value = data.excel_patterns.join(', ')
      editPatternDialog.value = true
    }

    const savePatterns = async () => {
      if (!editingColumnData.value) return
      
      try {
        isSavingPattern.value = true
        
        // Преобразуем строку в массив, убирая пустые элементы
        const patterns = editingPatterns.value
          .split(',')
          .map(p => p.trim())
          .filter(p => p.length > 0)
        
        editingColumnData.value.excel_patterns = patterns
        
        await saveSingleSetting(editingColumnData.value)
        
        editPatternDialog.value = false
        
        toast.add({
          severity: 'success',
          summary: 'Сохранено',
          detail: `Ключевые слова для ${editingColumnLabel.value} обновлены`,
          life: 3000
        })
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Ошибка',
          detail: 'Не удалось сохранить ключевые слова',
          life: 5000
        })
      } finally {
        isSavingPattern.value = false
      }
    }

    const cancelPatternEdit = () => {
      editPatternDialog.value = false
      editingPatterns.value = ''
      editingColumnData.value = null
      editingColumnLabel.value = ''
    }

    const saveSingleSetting = async (setting) => {
      if (setting.excel_patterns.length > 0) {
        if (setting.id) {
          await apiService.updateMappingSetting(setting.id, {
            excel_patterns: setting.excel_patterns
          })
        } else {
          const created = await apiService.createMappingSetting({
            db_column: setting.db_column,
            excel_patterns: setting.excel_patterns
          })
          setting.id = created.id
        }
      } else if (setting.id) {
        // Если нет паттернов, удаляем настройку
        await apiService.deleteMappingSetting(setting.id)
        setting.id = null
      }
    }

    const closeDialog = () => {
      visible.value = false
    }

    const onDialogClose = (value) => {
      visible.value = value
      emit('update:modelValue', value)
    }

    watch(() => props.modelValue, (newValue) => {
      visible.value = newValue
      if (newValue) {
        loadMappingSettings()
      }
    })

    onMounted(() => {
      if (visible.value) {
        loadMappingSettings()
      }
    })

    return {
      dataTable,
      visible,
      mappingSettings,
      newPattern,
      isSaving,
      isResetting,
      isLoading,
      editPatternDialog,
      editingPatterns,
      editingColumnLabel,
      isSavingPattern,
      getFieldLabel,
      getFieldIcon,
      loadMappingSettings,
      saveAllSettings,
      loadDefaultSettings,
      addPattern,
      removePattern,
      clearPatterns,
      openPatternEditor,
      savePatterns,
      cancelPatternEdit,
      closeDialog,
      onDialogClose
    }
  }
}
</script>

<style scoped>
.mapping-settings-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.settings-grid {
  flex: 1;
  overflow: hidden;
}

.patterns-display {
  min-height: 40px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.pattern-editor {
  width: 100%;
}

.patterns-list {
  max-height: 150px;
  overflow-y: auto;
}

.pattern-item {
  margin-bottom: 0.25rem;
}

:deep(.p-datatable .p-datatable-tbody > tr > td) {
  padding: 0.75rem 0.5rem;
}

:deep(.p-chip) {
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem;
}

/* Адаптивность для полноэкранного режима */
.mapping-settings-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.settings-grid {
  flex: 1;
  overflow: hidden;
  min-height: 0; /* Важно для правильной работы flex */
}

.adaptive-table {
  height: 100%;
}

:deep(.adaptive-table .p-datatable-wrapper) {
  height: 100% !important;
}

:deep(.adaptive-table .p-datatable-scrollable-body) {
  max-height: calc(100vh - 300px) !important; /* Вычитаем место для header и footer */
  min-height: 400px !important;
}

/* Для полноэкранного режима */
:deep(.p-dialog-maximized .adaptive-table .p-datatable-scrollable-body) {
  max-height: calc(100vh - 200px) !important; /* Больше места в полноэкранном режиме */
}

/* Дополнительные стили для полноэкранного диалога */
:deep(.p-dialog-maximized) {
  margin: 0 !important;
}

:deep(.p-dialog-maximized .p-dialog-content) {
  height: calc(100vh - 120px) !important;
  max-height: calc(100vh - 120px) !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
}

:deep(.p-dialog-maximized .mapping-settings-container) {
  height: 100% !important;
  max-height: 100% !important;
}

:deep(.p-dialog-maximized .settings-grid) {
  flex: 1 !important;
  height: 100% !important;
  overflow: hidden !important;
}

:deep(.p-dialog-maximized .adaptive-table) {
  height: 100% !important;
}

:deep(.p-dialog-maximized .adaptive-table .p-datatable) {
  height: 100% !important;
  display: flex !important;
  flex-direction: column !important;
}

:deep(.p-dialog-maximized .adaptive-table .p-datatable-wrapper) {
  flex: 1 !important;
  overflow: hidden !important;
}

/* Принудительное использование шрифта Inter для всех элементов */
.mapping-settings-dialog :deep(*) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* Исключение для иконок */
.mapping-settings-dialog :deep(i), 
.mapping-settings-dialog :deep(.pi), 
.mapping-settings-dialog :deep([class^="pi-"]), 
.mapping-settings-dialog :deep([class*=" pi-"]) {
  font-family: 'primeicons' !important;
  font-style: normal !important;
  font-weight: normal !important;
}

/* Специфичные стили для элементов таблицы */
.mapping-settings-dialog :deep(.p-datatable) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.mapping-settings-dialog :deep(.p-datatable th) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  font-weight: 600 !important;
}

.mapping-settings-dialog :deep(.p-datatable td) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.mapping-settings-dialog :deep(.p-chip) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.mapping-settings-dialog :deep(.p-button) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.mapping-settings-dialog :deep(.p-button i) {
  font-family: 'primeicons' !important;
}

.mapping-settings-dialog :deep(.p-inputtext) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.mapping-settings-dialog :deep(.p-dialog-header) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.mapping-settings-dialog :deep(.p-dialog-title) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  font-weight: 600 !important;
}

/* Стили для названий колонок БД */
.mapping-settings-dialog :deep(.field-label) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  font-weight: 600 !important;
}

.mapping-settings-dialog :deep(.field-description) {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  font-weight: 400 !important;
  font-size: 0.875rem !important;
}
</style>
