import pandas as pd
import streamlit as st

def check_password():
    """Возвращает True, если введен правильный пароль."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"] # Удаляем пароль из сессии
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Первое открытие — показываем поле ввода
        st.text_input("Введите пароль для доступа:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Неверный пароль
        st.text_input("Введите пароль для доступа:", type="password", on_change=password_entered, key="password")
        st.error("😕 Неверный пароль")
        return False
    else:
        # Пароль верный, пускаем дальше
        return True

if not check_password():
    st.stop() # Останавливаем загрузку приложения, пока пароль не верен

# --- ДАЛЕЕ ИДЕТ ВЕСЬ ТВОЙ ОСНОВНОЙ КОД (таблицы, функция calculate_strategy и т.д.) ---

# Настройка страницы браузера
st.set_page_config(
    page_title='Дневник трейдера Brent', page_icon='🛢️', layout='wide'
)

st.title('🛢️ Личный дневник трейдера: Brent (Price Action)')
st.markdown(
    'Контроль тренда, ручной ввод котировок и железная дисциплина по Ливермору.'
)

# Путь к вашему файлу с историей
file_path ='brent_history2.csv'


# Функция загрузки данных с защитой от ошибок
@st.cache_data
def load_data(path):
  df = pd.read_csv(path, sep=',', quotechar='"')
  # Превращаем цену в числа с учетом запятых
  df['Цена'] = df['Цена'].astype(str).str.replace(',', '.').astype(float)
  df = df[['Дата', 'Цена']]
  return df


try:
  df = load_data(file_path)
except Exception as e:
  st.error(
      f'Не удалось загрузить файл истории. Проверьте путь: {file_path}\nОшибка:'
      f' {e}'
  )
  st.stop()

# --- БОКОВАЯ ПАНЕЛЬ ДЛЯ РУЧНОГО ВВОДА ---
st.sidebar.header('📝 Внести свежие данные')
st.sidebar.markdown(
    'Вбивайте цену закрытия за день, чтобы держать руку на пульсе.'
)

new_date = st.sidebar.text_input('Дата (например, 02.11.2026)')
new_price = st.sidebar.number_input(
    'Цена закрытия', min_value=0.0, value=80.00, format='%.2f'
)

if st.sidebar.button('Добавить в базу и обновить'):
  if new_date:
    # Создаем новую строчку и добавляем её в датафрейм
    new_row = pd.DataFrame({'Дата': [new_date], 'Цена': [new_price]})
    df = pd.concat([new_row, df], ignore_index=True)

    # Сохраняем обновленный файл обратно на диск
    df.to_csv(file_path, index=False, sep=',')
    st.sidebar.success(f'Успешно добавлено: {new_date} — {new_price}')
    # Сбрасываем кэш, чтобы таблица сразу обновилась
    st.cache_data.clear()
    st.rerun()
  else:
    st.sidebar.warning('Пожалуйста, укажите дату!')


# --- ЛОГИКА РАСЧЕТА СТРАТЕГИИ (ZIGZAG) ---
def calculate_strategy(df_data):
  # Сортируем от старых к новым для правильного расчета структуры
  df_sorted = (
      df_data.dropna(subset=['Дата', 'Цена'])
      .sort_values('Дата', key=lambda x: pd.to_datetime(x, dayfirst=True))
      .reset_index(drop=True)
  )

  prices = df_sorted['Цена'].tolist()
  dates = df_sorted['Дата'].tolist()

  if len(prices) < 3:
    return 'ВНЕ РЫНКА', 0, 'Нет данных'

  extrema_history = []
  trend = 0
  best_price = prices[0]
  reversal_threshold = 2.0 # Порог разворота

  for i in range(len(prices)):
    p = prices[i]
    d = dates[i]

    if trend == 0:
      if p > best_price:
        trend = 1
        best_price = p
      elif p < best_price:
        trend = -1
        best_price = p
    elif trend == 1:
      if p > best_price:
        best_price = p
      elif best_price - p >= reversal_threshold:
        extrema_history.append(('Максимум', best_price, d))
        trend = -1
        best_price = p
    elif trend == -1:
      if p < best_price:
        best_price = p
      elif p - best_price >= reversal_threshold:
        extrema_history.append(('Минимум', best_price, d))
        trend = 1
        best_price = p

  position = None
  entry_price = 0
  entry_date = ''

  for i in range(1, len(extrema_history)):
    tipo, price, date = extrema_history[i]

    # LONG
    if (
        'Минимум' in tipo
        and position is None
        and i >= 2
        and extrema_history[i - 2][0] == 'Минимум'
    ):
      if price > extrema_history[i - 2][1]:
        position = 'LONG'
        entry_price = price
        entry_date = date
    elif (
        'Максимум' in tipo
        and position == 'LONG'
        and i >= 2
        and extrema_history[i - 2][0] == 'Максимум'
    ):
      if price < extrema_history[i - 2][1]:
        position = None

    # SHORT
    if (
        'Максимум' in tipo
        and position is None
        and i >= 2
        and extrema_history[i - 2][0] == 'Максимум'
    ):
      if price < extrema_history[i - 2][1]:
        position = 'SHORT'
        entry_price = price
        entry_date = date
    elif (
        'Минимум' in tipo
        and position == 'SHORT'
        and i >= 2
        and extrema_history[i - 2][0] == 'Минимум'
    ):
      if price > extrema_history[i - 2][1]:
        position = None

  return position, entry_price, entry_date


current_position, entry_p, entry_d = calculate_strategy(df)

# --- БЛОК СТАТУСА СТРАТЕГИИ ---
st.subheader('⚙️ Текущий статус по системе')

latest_price = df.iloc[0]['Цена'] # Самая верхняя строка (последняя)
# Для поиска предыдущей цены посчитаем дельту
df_sorted_temp = df.sort_values(
    'Дата', key=lambda x: pd.to_datetime(x, dayfirst=True), ascending=False
).reset_index(drop=True)
diff_val = (
    latest_price - df_sorted_temp.iloc[1]['Цена']
    if len(df_sorted_temp) > 1
    else 0
)

col1, col2, col3 = st.columns(3)
col1.metric(
    label='Последняя цена закрытия',
    value=f'{latest_price:.2f}',
    delta=f'{diff_val:+.2f}',
)
col2.metric(
    label='Всего записей в базе',
    value=f'{len(df)} дней',
)

# Красивое отображение текущего статуса в третьей колонке
if current_position == 'LONG':
  col3.success(
      f'🟢 СТАТУС: ДЕРЖИМ LONG\n\nЦена входа: ${entry_p:.2f} ({entry_d})'
  )
elif current_position == 'SHORT':
  col3.error(
      f'🔴 СТАТУС: ДЕРЖИМ SHORT\n\nЦена входа: ${entry_p:.2f} ({entry_d})'
  )
else:
  col3.warning('🟡 СТАТУС: ВНЕ РЫНКА\n\nЖдем формирования структуры.')

# --- ОСНОВНОЙ БЛОК: ТАБЛИЦА И ИНДИКАТОРЫ ---
st.subheader('📊 Таблица котировок и динамика')

df_display = df.copy()
# Считаем разницу с предыдущим днем (вниз по таблице, так как даты идут от новых к старым)
df_display['Изменение'] = df_display['Цена'].diff(-1)


# Функция окраски цены на основе столбца «Изменение»
def highlight_price(row):
  change = row['Изменение']
  if pd.isna(change):
    color = ''
  elif change > 0:
    color = 'color: #2ecc71; font-weight: bold;' # Зеленый при росте
  elif change < 0:
    color = 'color: #e74c3c; font-weight: bold;' # Красный при падении
  else:
    color = ''

  # Возвращаем стиль только для колонки 'Цена', для остальных — пусто
  return [
      color if col == 'Цена' else '' for col in row.index
  ]


# Применяем стилизацию ко всей строке
styled_df = (
    df_display.head(25)
    .style.apply(highlight_price, axis=1)
    .format({'Цена': '{:.2f}', 'Изменение': '{:+.2f}'})
)

st.dataframe(styled_df, use_container_width=True)
