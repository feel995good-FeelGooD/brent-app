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
