import pandas as pd
import streamlit as st

# Настройка страницы браузера
st.set_page_config(
    page_title='Дневник трейдера Brent', page_icon='🛢️', layout='wide'
)

st.title('🛢️ Личный дневник трейдера: Brent (Price Action)')
st.markdown(
    'Контроль тренда, ручной ввод котировок и железная дисциплина по Ливермору.'
)

# Путь к файлу с историей в корне проекта
file_path = 'brent_history2.csv'


# Функция загрузки данных с защитой от ошибок
@st.cache_data
def load_data(path):
  df = pd.read_csv(path, sep=',', quotechar='"')
  df['Цена'] = df['Цена'].astype(str).str.replace(',', '.').astype(float)
  return df


try:
  df_raw = load_data(file_path)
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
    df_disk = pd.read_csv(file_path, sep=',', quotechar='"')

    if new_date in df_disk['Дата'].astype(str).values:
      df_disk.loc[df_disk['Дата'] == new_date, 'Цена'] = new_price
      st.sidebar.success(f'Обновлена цена за {new_date}: {new_price}')
    else:
      new_row = pd.DataFrame({'Дата': [new_date], 'Цена': [new_price]})
      df_disk = pd.concat([new_row, df_disk], ignore_index=True)
      st.sidebar.success(f'Успешно добавлено: {new_date} — {new_price}')

    df_disk['temp_dt'] = pd.to_datetime(
        df_disk['Дата'], dayfirst=True, errors='coerce'
    )
    df_disk = (
        df_disk.sort_values('temp_dt')
        .drop(columns=['temp_dt'])
        .reset_index(drop=True)
    )

    df_disk.to_csv(file_path, index=False, sep=',')
    st.cache_data.clear()
    st.rerun()
  else:
    st.sidebar.warning('Пожалуйста, укажите дату!')


# --- АКТУАЛЬНЫЙ РАСЧЕТ ПО СВЕЖЕМУ ОКНУ (БЕЗ ПРИЗРАКОВ 2022 ГОДА) ---
def calculate_strategy(df_data):
  df_temp = df_data.dropna(subset=['Дата', 'Цена']).copy()
  df_temp['temp_dt'] = pd.to_datetime(
      df_temp['Дата'], dayfirst=True, errors='coerce'
  )
  df_sorted = (
      df_temp.sort_values('temp_dt')
      .drop(columns=['temp_dt'])
      .reset_index(drop=True)
  )

  # Жестко ограничиваем расчет последними 75 днями,
  # чтобы экстремумы строились исключительно по актуальному рынку
  if len(df_sorted) > 75:
    df_sorted = df_sorted.tail(75).reset_index(drop=True)

  prices = df_sorted['Цена'].tolist()
  dates = df_sorted['Дата'].tolist()

  if len(prices) < 2:
    return 'ВНЕ РЫНКА', prices[-1] if prices else 0, dates[-1] if dates else ''

  trend = 'LONG' if prices[1] >= prices[0] else 'SHORT'

  current_max = max(prices[0], prices[1])
  current_min = min(prices[0], prices[1])

  entry_price = prices[0]
  entry_date = dates[0]

  pullback_min = prices[0]
  pullback_max = prices[0]

  for i in range(1, len(prices)):
    p = prices[i]
    d = dates[i]
    prev_p = prices[i - 1]

    if trend == 'LONG':
      if p > current_max:
        current_max = p
        pullback_min = p

      if p < current_min:
        trend = 'SHORT'
        entry_price = p
        entry_date = d
        current_max = prev_p
        pullback_max = p
      else:
        if p < pullback_min:
          pullback_min = p
        if i > 1 and prices[i - 1] < prices[i - 2] and p > prev_p:
          current_min = pullback_min
          pullback_min = p

    else:  # SHORT
      if p < current_min:
        current_min = p
        pullback_max = p

      if p > current_max:
        trend = 'LONG'
        entry_price = p
        entry_date = d
        current_min = prev_p
        pullback_min = p
      else:
        if p > pullback_max:
          pullback_max = p
        if i > 1 and prices[i - 1] > prices[i - 2] and p < prev_p:
          current_max = pullback_max
          pullback_max = p

  return trend, entry_price, entry_date


# Подготовка датафрейма для отображения (свежие даты сверху)
df_display_prep = df_raw.copy()
df_display_prep['temp_dt'] = pd.to_datetime(
    df_display_prep['Дата'], dayfirst=True, errors='coerce'
)
df_display_sorted = (
    df_display_prep.sort_values('temp_dt', ascending=False)
    .drop(columns=['temp_dt'])
    .reset_index(drop=True)
)

current_position, entry_p, entry_d = calculate_strategy(df_raw)

# --- БЛОК СТАТУСА СТРАТЕГИИ ---
st.subheader('⚙️ Текущий статус по системе')

latest_price = df_display_sorted.iloc[0]['Цена']
diff_val = (
    latest_price - df_display_sorted.iloc[1]['Цена']
    if len(df_display_sorted) > 1
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
    value=f'{len(df_display_sorted)} дней',
)

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

df_display = df_display_sorted.copy()
df_display['Изменение'] = df_display['Цена'].diff(-1)


def color_green_red(val):
  if pd.isna(val):
    return ''
  color = 'green' if val > 0 else 'red'
  return f'color: {color}; font-weight: bold;'


styled_df = (
    df_display.head(25)
    .style.format({'Цена': '{:.2f}', 'Изменение': '{:+.2f}'})
    .map(color_green_red, subset=['Изменение'])
)

st.dataframe(styled_df, use_container_width=True)
