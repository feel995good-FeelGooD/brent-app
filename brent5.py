import pandas as pd
import streamlit as st

st.set_page_config(
    page_title='Дневник трейдера Brent (State Engine)',
    page_icon='🛢️',
    layout='wide',
)

st.title('🛢️ Дневник трейдера: Brent (Динамический движок)')
st.markdown(
    'Архитектура: работа с реальными данными архива и окном последних'
    ' экстремумов.'
)

file_path = 'brent_history2.csv'


# --- 1. РАБОТА С АРХИВОМ ---
def load_archive(path):
  df = pd.read_csv(path, sep=',', quotechar='"')
  # Очищаем названия колонок от лишних пробелов
  df.columns = df.columns.str.strip()

  # Приводим числовые колонки к float
  for col in ['Цена', 'Откр.', 'Макс.', 'Мин.']:
    if col in df.columns:
      df[col] = df[col].astype(str).str.replace(',', '.').astype(float)

  # Переводим дату в формат datetime для правильной хронологической сортировки
  df['temp_dt'] = pd.to_datetime(
      df['Дата'], format='%d.%m.%Y', errors='coerce'
  )
  if df['temp_dt'].isna().all():
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


# --- 3. ДИНАМИЧЕСКИЙ ДВИЖОК СОСТОЯНИЙ ( ПОСЛЕДНИЕ 10 БАРОВ ) ---
def run_state_engine(df):
  if len(df) < 2:
    return 'ВНЕ РЫНКА', 0.0, '', 0.0, 0.0

  prices = df['Цена'].tolist()
  highs = df['Макс.'].tolist()
  lows = df['Мин.'].tolist()
  dates = df['Дата'].tolist()

  # Скользящее окно: берем последние 10 дней для локальных экстремумов
  window_size = 10
  recent_lows = lows[-window_size:]
  recent_highs = highs[-window_size:]

  loc_min
