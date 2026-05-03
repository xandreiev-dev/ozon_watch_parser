# Ozon Watch Parser

Парсер умных часов с Ozon. Проект сделан модульно, но сохраняет ключевую новую логику Ozon: работа через уже открытый Chrome по CDP, прокрутка листинга и сбор карточек прямо из открытой страницы.

## Главное

- CDP включен по умолчанию: `http://localhost:9222`.
- Если Chrome с CDP уже открыт, парсер подключается к нему и не закрывает его после работы.
- Если CDP недоступен, парсер может сам открыть Chrome с `--remote-debugging-port=9222`.
- Данные пишутся потоково в брендовые XLSX-файлы.
- После прохода брендовые файлы агрегируются в общий `Ozon_watch_ru_YYYYMMDD.xlsx`.
- Поля включают основу Avito-парсера и дополнительные поля Ozon из листинга.

## Установка

```bash
pip install -r requirements.txt
playwright install chromium
```

## Рекомендуемый запуск через открытый Chrome

```bash
chrome.exe --remote-debugging-port=9222
python -m ozon_watch_parser.cli --once
```

Парсинг одного бренда:

```bash
python -m ozon_watch_parser.cli --once --brand apple
```

Запуск без CDP:

```bash
python -m ozon_watch_parser.cli --once --no-cdp
```

## Структура

```text
src/ozon_watch_parser/
  browser/      CDP-first подключение к Chrome
  config/       бренды, URL листингов, колонки
  domain/       нормализация часов
  export/       потоковый XLSX и агрегация
  ozon/         JS extractor и прокрутка листинга
  services/     сценарий парсинга брендов
  utils/        даты, URL, пошлина
```
