import pandas as pd
import streamlit as st

st.set_page_config(
    page_title='Дневник трейдера Brent (State Engine)',
    page_icon='🛢️',
    layout='wide',
)

st.title('🛢️ Дневник трейдера: Brent (Динамический движок)')
st.markdown(
    'Архитектура: работа с реальными данными архива (Open, High, Low, Close).'
)

file_path = 'brent_history2.csv'


# --- 1. РАБОТА С АРХИВОМ ---
def load_archive(path):
  df = pd.read_csv(path, sep=',', quotechar='"')
  # Очищаем названия колонок от лишних пробелов
  df.columns = df.columns.str.strip()

  # Приводим числовые колонки к float (заменяем запятые на точки, если есть)
  for col in ['Цена', 'Откр.', 'Макс.', 'Мин.']:
    if col in df.columns:
      df[col] = df[col].astype(str).str.replace(',', '.').astype(float)

  # Переводим дату в формат datetime для правильной хронологической сортировки
  df['temp_dt'] = pd.to_datetime(
      df['Дата'], format='%d.%m.%Y', errors='coerce'
  )
  if df['temp_dt'].isna().all():
    # Если формат другой, пробуем общий парсер
    df['temp_dt'] = pd.to_datetime(df['Дата'], dayfirst=True, errors='coerce')

  # Сортируем СТРОГО от старых к новым (чтобы начало было в 2022, а конец в 2026)
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
new_open = st.sidebar.number_input(
    'Открытие', min_value=0.0, value=80.00, format='%.2f'
)
new_high = st.sidebar.number_input(
    'Максимум', min_value=0.0, value=81.00, format='%.2f'
)
new_low = st.sidebar.number_input(
    'Минимум', min_value=0.0, value=79.00, format='%.2f'
)

if st.sidebar.button('Записать день в дневник'):
  if new_date:
    df_disk = pd.read_csv(file_path, sep=',', quotechar='"')
    df_disk.columns = df_disk.columns.str.strip()

    if new_date in df_disk['Дата'].astype(str).values:
      df_disk.loc[df_disk['Дата'] == new_date, 'Цена'] = new_price
      df_disk.loc[df_disk['Дата'] == new_date, 'Макс.'] = new_high
      df_disk.loc[df_disk['Дата'] == new_date, 'Мин.'] = new_low
      st.sidebar.success(f'Обновлено: {new_date}')
    else:
      new_row = pd.DataFrame({
          'Дата': [new_date],
          'Цена': [new_price],
          'Откр.': [new_open],
          'Макс.': [new_high],
          'Мин.': [new_low],
      })
      df_disk = pd.concat([df_disk, new_row], ignore_index=True)

    df_disk.to_csv(file_path, index=False, sep=',')
    st.rerun()
  else:
    st.sidebar.warning('Укажите дату!')


# --- 3. ДИНАМИЧЕСКИЙ ДВИЖОК СОСТОЯНИЙ ---
def run_state_engine(df):
  if len(df) < 2:
    return 'ВНЕ РЫНКА', 0.0, '', 0.0, 0.0

  prices = df['Цена'].tolist()
  highs = df['Макс.'].tolist()
  lows = df['Мин.'].tolist()
  dates = df['Дата'].tolist()

  trend = 'LONG' if prices[1] >= prices[0] else 'SHORT'
  local_min = min(lows[0], lows[1])
  local_max = max(highs[0], highs[1])

  entry_price = prices[0]
  entry_date = dates[0]

  for i in range(1, len(prices)):
    curr_p = prices[i]
    curr_h = highs[i]
    curr_l = lows[i]
    curr_d = dates[i]

    if trend == 'LONG':
      if curr_h > local_max:
        local_max = curr_h
      if curr_l < local_min:
        # Слом структуры вниз -> переворот в SHORT
        trend = 'SHORT'
        entry_price = curr_p
        entry_date = curr_d
        local_max = curr_h  # Новый ориентир для шорта
    elif trend == 'SHORT':
      if curr_l < local_min:
        local_min = curr_l
      if curr_h > local_max:
        # Слом структуры вверх -> переворот в LONG
        trend = 'LONG'
        entry_price = curr_p
        entry_date = curr_d
        local_min = curr_l  # Новый ориентир для лонга

  return trend, entry_price, entry_date, local_min, local_max


trend, entry_p, entry_d, loc_min, loc_max = run_state_engine(df_archive)

# Дисплей: самые свежие сверху
df_display = df_archive.iloc[::-1].reset_index(drop=True)
today_p = df_display.iloc[0]['Цена']
yesterday_p = (
    df_display.iloc[1]['Цена'] if len(df_display) > 1 else today_p
)
diff_val = today_p - yesterday_p

# --- 4. ИНТЕРФЕЙС ---
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
  target_level = loc_min if trend == 'LONG' else loc_max
  st.info(f"""
    **Логика уровня переворота:**
    * Находясь в **{trend}**, система следит за ключевым экстремумом.
    * Переворот произойдет, если цена проколет уровень **${target_level:.2f}**.
    """)

st.subheader('📜 Полный архив (для контроля и блокнота)')
st.dataframe(df_display.head(30), use_container_width=True)
