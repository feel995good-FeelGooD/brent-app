import pandas as pd
import streamlit as st

st.set_page_config(
    page_title='Дневник трейдера Brent (State Engine)',
    page_icon='🛢️',
    layout='wide',
)

st.title('🛢️ Дневник трейдера: Brent (Динамический движок)')
st.markdown(
    'Архитектура с 4-мя переменными: минимум, максимум, вчера и сегодня. Без'
    ' призраков прошлых лет.'
)

file_path = 'brent_history2.csv'


# --- 1. РАБОТА С АРХИВОМ ---
def load_archive(path):
  df = pd.read_csv(path, sep=',', quotechar='"')
  df['Цена'] = df['Цена'].astype(str).str.replace(',', '.').astype(float)
  df['temp_dt'] = pd.to_datetime(df['Дата'], dayfirst=True, errors='coerce')
  # Сортируем строго от старых к новым для правильного последовательного расчета
  df = df.sort_values('temp_dt').drop(columns=['temp_dt']).reset_index(drop=True)
  return df


try:
  df_archive = load_archive(file_path)
except Exception as e:
  st.error(f'Ошибка загрузки архива: {e}')
  st.stop()

# --- 2. БОКОВАЯ ПАНЕЛЬ: ДОБАВЛЕНИЕ СВЕЖЕГО ДНЯ ---
st.sidebar.header('📝 Внести свежую дату')
new_date = st.sidebar.text_input('Дата (например, 03.11.2026)')
new_price = st.sidebar.number_input(
    'Цена закрытия', min_value=0.0, value=80.00, format='%.2f'
)

if st.sidebar.button('Записать день в дневник'):
  if new_date:
    df_disk = pd.read_csv(file_path, sep=',', quotechar='"')
    if new_date in df_disk['Дата'].astype(str).values:
      df_disk.loc[df_disk['Дата'] == new_date, 'Цена'] = new_price
      st.sidebar.success(f'Обновлено: {new_date} — {new_price}')
    else:
      new_row = pd.DataFrame({'Дата': [new_date], 'Цена': [new_price]})
      df_disk = pd.concat([new_row, df_disk], ignore_index=True)
      st.sidebar.success(f'Добавлено: {new_date} — {new_price}')

    # Сохраняем на диск
    df_disk.to_csv(file_path, index=False, sep=',')
    st.rerun()
  else:
    st.sidebar.warning('Укажите дату!')


# --- 3. ДИНАМИЧЕСКИЙ ДВИЖОК СОСТОЯНИЙ (STATE MACHINE) ---
def run_state_engine(df):
  """Прогоняет последовательно цены, удерживая в памяти только 4 переменные на каждом

  шаге:

  1. local_min (текущий минимум волны)
  2. local_max (текущий максимум волны)
  3. prev_price (вчерашняя цена)
  4. curr_price (сегодняшняя цена)
  """
  if len(df) < 2:
    return 'ВНЕ РЫНКА', 0.0, '', 0.0, 0.0

  prices = df['Цена'].tolist()
  dates = df['Дата'].tolist()

  # Инициализация первого состояния
  trend = 'LONG' if prices[1] >= prices[0] else 'SHORT'

  local_min = min(prices[0], prices[1])
  local_max = max(prices[0], prices[1])

  entry_price = prices[0]
  entry_date = dates[0]

  pullback_min = prices[0]
  pullback_max = prices[0]

  # Шагаем по истории последовательно, обновляя состояние локально
  for i in range(1, len(prices)):
    curr_price = prices[i]
    prev_price = prices[i - 1]
    curr_date = dates[i]

    if trend == 'LONG':
      # Новый максимум — подтягиваем локальную верхушку
      if curr_price > local_max:
        local_max = curr_price
        pullback_min = curr_price

      # Слом структуры: цена пробила локальный минимум волны
      if curr_price < local_min:
        trend = 'SHORT'
        entry_price = curr_price
        entry_date = curr_date
        local_max = prev_price
        pullback_max = curr_price
      else:
        # Фиксация дна для потенциального нового минимума
        if curr_price < pullback_min:
          pullback_min = curr_price
        if i > 1 and prices[i - 1] < prices[i - 2] and curr_price > prev_price:
          local_min = pullback_min
          pullback_min = curr_price

    elif trend == 'SHORT':
      # Новый минимум — обновляем низину
      if curr_price < local_min:
        local_min = curr_price
        pullback_max = curr_price

      # Слом структуры: цена пробила локальный максимум волны
      if curr_price > local_max:
        trend = 'LONG'
        entry_price = curr_price
        entry_date = curr_date
        local_min = prev_price
        pullback_min = curr_price
      else:
        # Фиксация вершины для потенциального нового максимума
        if curr_price > pullback_max:
          pullback_max = curr_price
        if i > 1 and prices[i - 1] > prices[i - 2] and curr_price < prev_price:
          local_max = pullback_max
          pullback_max = curr_price

  return trend, entry_price, entry_date, local_min, local_max


# Расчет состояния
trend, entry_p, entry_d, loc_min, loc_max = run_state_engine(df_archive)

# Подготовка данных для экрана (самые свежие дни сверху, как в блокноте)
df_display = df_archive.iloc[::-1].reset_index(drop=True)
today_p = df_display.iloc[0]['Цена']
yesterday_p = (
    df_display.iloc[1]['Цена'] if len(df_display) > 1 else today_p
)
diff_val = today_p - yesterday_p

# --- 4. ДИСКРЕТНЫЙ ИНТЕРФЕЙС: 4 ОСНОВНЫЕ ПЕРЕМЕННЫЕ ---
st.subheader('📊 4 Ключевые переменные текущего состояния')

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    label='1. Сегодняшняя цена',
    value=f'${today_p:.2f}',
    delta=f'{diff_val:+.2f}',
)
c2.metric(label='2. Вчерашняя цена', value=f'${yesterday_p:.2f}')
c3.metric(label='3. Локальный MIN волны', value=f'${loc_min:.2f}')
c4.metric(label='4. Локальный MAX волны', value=f'${loc_max:.2f}')

st.markdown('---')

# --- 5. ВЕРДИКТ И ПОЗИЦИЯ ---
st.subheader('🎯 Актуальная позиция')
col_left, col_right = st.columns([1, 2])

with col_left:
  if trend == 'LONG':
    st.success(
        f'### 🟢 LONG\n**Вход:** ${entry_p:.2f}\n\n**Дата входа:** {entry_d}'
    )
  else:
    st.error(
        f'### 🔴 SHORT\n**Вход:** ${entry_p:.2f}\n\n**Дата входа:** {entry_d}'
    )

with col_right:
  st.info(f"""
    **Логика уровня переворота:**
    * Находясь в **{trend}**, система следит за противоположным экстремумом.
    * Переворот произойдет только если новая цена пересечет уровень **${loc_min if trend == 'LONG' else loc_max:.2f}**.
    """)

# --- 6. ТАБЛИЦА-АРХИВ ДЛЯ ПРОСМОТРА ---
st.subheader('📜 Полный архив (для контроля и блокнота)')
df_display['Изменение'] = df_display['Цена'].diff(-1)


def color_diff(val):
  if pd.isna(val):
    return ''
  return 'color: green; font-weight: bold;' if val > 0 else 'color: red;'


st.dataframe(
    df_display.head(30)
    .style.format({'Цена': '{:.2f}', 'Изменение': '{:+.2f}'})
    .map(color_diff, subset=['Изменение']),
    use_container_width=True,
)
