import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import ToastService from 'primevue/toastservice'
import Tooltip from 'primevue/tooltip'
import 'primeicons/primeicons.css'
import 'primeflex/primeflex.css'
import './styles/global.css'

const app = createApp(App)

app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      prefix: 'p',
      darkModeSelector: '.dark-mode',
      cssLayer: false
    }
  },
  locale: {
    // Русская локализация
    startsWith: 'Начинается с',
    contains: 'Содержит',
    notContains: 'Не содержит',
    endsWith: 'Заканчивается на',
    equals: 'Равно',
    notEquals: 'Не равно',
    noFilter: 'Без фильтра',
    lt: 'Меньше чем',
    lte: 'Меньше или равно',
    gt: 'Больше чем',
    gte: 'Больше или равно',
    is: 'Является',
    isNot: 'Не является',
    before: 'До',
    after: 'После',
    dateIs: 'Дата равна',
    dateIsNot: 'Дата не равна',
    dateBefore: 'Дата до',
    dateAfter: 'Дата после',
    clear: 'Очистить',
    apply: 'Применить',
    matchAll: 'Совпадение всех',
    matchAny: 'Совпадение любого',
    addRule: 'Добавить правило',
    removeRule: 'Удалить правило',
    accept: 'Да',
    reject: 'Нет',
    choose: 'Выбрать',
    upload: 'Загрузить',
    cancel: 'Отмена',
    completed: 'Завершено',
    pending: 'Ожидание',
    dayNames: ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'],
    dayNamesShort: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
    dayNamesMin: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
    monthNames: ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
    monthNamesShort: ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'],
    chooseYear: 'Выбрать год',
    chooseMonth: 'Выбрать месяц',
    chooseDate: 'Выбрать дату',
    prevDecade: 'Предыдущее десятилетие',
    nextDecade: 'Следующее десятилетие',
    prevYear: 'Предыдущий год',
    nextYear: 'Следующий год',
    prevMonth: 'Предыдущий месяц',
    nextMonth: 'Следующий месяц',
    prevHour: 'Предыдущий час',
    nextHour: 'Следующий час',
    prevMinute: 'Предыдущая минута',
    nextMinute: 'Следующая минута',
    prevSecond: 'Предыдущая секунда',
    nextSecond: 'Следующая секунда',
    am: 'до полудня',
    pm: 'после полудня',
    today: 'Сегодня',
    weekHeader: 'Нед',
    firstDayOfWeek: 1,
    dateFormat: 'dd.mm.yy',
    weak: 'Слабый',
    medium: 'Средний',
    strong: 'Сильный',
    passwordPrompt: 'Введите пароль',
    emptyFilterMessage: 'Результатов не найдено',
    searchMessage: 'Доступно {0} результатов',
    selectionMessage: 'Выбрано {0} элементов',
    emptySelectionMessage: 'Нет выбранных элементов',
    emptySearchMessage: 'Результатов не найдено',
    emptyMessage: 'Нет доступных опций'
  }
})

app.use(ToastService)
app.directive('tooltip', Tooltip)
app.use(router)
app.mount('#app')
