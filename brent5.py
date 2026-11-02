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

# Путь к вашему файлу с историей
# Путь к файлу с историей в корне проекта
file_path = 'brent_history2.csv'




# Функция загрузки данных с защитой от ошибок
@st.cache_data
def load_data(path):
  df = pd.read_csv(path, sep=',', quotechar='"')
  # Превращаем цену в числа с учетом запятых
  df['Цена'] = df['Цена'].astype(str).str.replace(',', '.').astype(float)
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

new_date = st.sidebar.text_input('Дата (например, 03.11.2026)')
new_price = st.sidebar.number_input(
    'Цена закрытия', min_value=0.0, value=80.00, format='%.2f'
)

if st.sidebar.button('Добавить в базу и обновить'):
  if new_date:
    # 1. Читаем свежие данные с диска без кэша
    df_disk = pd.read_csv(file_path, sep=',', quotechar='"')

    # 2. Проверяем, есть ли уже такая дата, чтобы исключить дубли
    if new_date in df_disk['Дата'].astype(str).values:
      df_disk.loc[df_disk['Дата'] == new_date, 'Цена'] = new_price
      st.sidebar.success(f'Обновлена цена за {new_date}: {new_price}')
    else:
      new_row = pd.DataFrame({'Дата': [new_date], 'Цена': [new_price]})
      df_disk = pd.concat([new_row, df_disk], ignore_index=True)
      st.sidebar.success(f'Успешно добавлено: {new_date} — {new_price}')

    # 3. Безопасная сортировка всей базы от старых к новым перед сохранением
    df_disk['temp_date'] = pd.to_datetime(
        df_disk['Дата'], dayfirst=True, errors='coerce'
    )
    df_disk = (
        df_disk.sort_values('temp_date')
        .drop(columns=['temp_date'])
        .reset_index(drop=True)
    )

    # 4. Сохраняем обратно на диск
    df_disk.to_csv(file_path, index=False, sep=',')

    # 5. Сбрасываем кэш и перезапускаем интерфейс
    st.cache_data.clear()
    st.rerun()
  else:
    st.sidebar.warning('Пожалуйста, укажите дату!')


# --- ЛОГИКА РАСЧЕТА СТРАТЕГИИ (ZIGZAG) ---
def calculate_strategy(df_data):
  # Безопасная сортировка от старых к новым для правильного расчета структуры
  df_temp = df_data.dropna(subset=['Дата', 'Цена']).copy()
  df_temp['temp_date'] = pd.to_datetime(
      df_temp['Дата'], dayfirst=True, errors='coerce'
  )
  df_sorted = (
      df_temp.sort_values('temp_date')
      .drop(columns=['temp_date'])
      .reset_index(drop=True)
  )

  prices = df_sorted['Цена'].tolist()
  dates = df_sorted['Дата'].tolist()

  if len(prices) < 3:
    return 'ВНЕ РЫНКА', 0, 'Нет данных'

  extrema_history = []
  trend = 0
  best_price = prices[0]
  reversal_threshold = 2.0  # Порог разворота

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


# Подготовка датафрейма для отображения (свежие даты сверху)
df_display_prep = df.copy()
df_display_prep['temp_date'] = pd.to_datetime(
    df_display_prep['Дата'], dayfirst=True, errors='coerce'
)
df_display_sorted = (
    df_display_prep.sort_values('temp_date', ascending=False)
    .drop(columns=['temp_date'])
    .reset_index(drop=True)
)

current_position, entry_p, entry_d = calculate_strategy(df)

# --- БЛОК СТАТУСА СТРАТЕГИИ ---
st.subheader('⚙️ Текущий статус по системе')

latest_price = df_display_sorted.iloc[0][
    'Цена'
]  # Самая верхняя строка (последняя актуальная)
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

# Отображение статуса
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
