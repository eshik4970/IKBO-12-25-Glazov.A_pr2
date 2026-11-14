# Граф зависимостей Cargo

Практическая работа № 2 по конфигурационному управлению, вариант 5.

Программа получает зависимости пакетов Rust из реестра crates.io и строит граф. Можно работать без интернета: в тестовом режиме зависимости читаются из JSON-файла. Для графа создаются файлы D2 и SVG, а по запросу выводится ASCII-дерево.

Проект написан на Python 3.10+. Сторонние Python-библиотеки и Cargo для получения списка зависимостей не используются.

## Структура проекта

```text
variant5_cargo/
├── src/
│   ├── main.py       # аргументы командной строки и запуск этапов
│   ├── graph.py      # получение зависимостей и обход графа
│   ├── semver.py     # проверка совместимости версий
│   └── render.py     # вывод D2, SVG и ASCII-дерева
├── tests/
│   └── test_graph.py
├── examples/
│   ├── repository.json
│   └── cycle.json
├── run.sh
├── run.bat
├── .gitignore
└── README.md
```

## Запуск

Дополнительные библиотеки устанавливать не нужно. Команды ниже выполняются из корня проекта.

Windows:

```bat
run.bat --test --repository examples/repository.json --package A --version test --ascii
```

Linux/macOS:

```sh
sh run.sh --test --repository examples/repository.json --package A --version test --ascii
```

Можно запускать и напрямую через `python src/main.py` (на некоторых системах команда Python называется `python3`).

### Параметры

| Параметр | Описание |
| --- | --- |
| `--package` | Название пакета |
| `--repository` | HTTPS-адрес реестра или путь к JSON-файлу |
| `--test` | Работа с тестовым JSON вместо реестра |
| `--version` | Версия пакета (`test` для примеров) |
| `--output` | Путь к SVG, по умолчанию `graph.svg` |
| `--ascii` | Дополнительно вывести дерево в консоль |
| `--filter` | Не учитывать пакеты, содержащие указанную подстроку |
| `--stage` | Номер этапа от 1 до 5, по умолчанию 5 |
| `--help` | Показать справку |

Параметры `--package`, `--repository` и `--version` обязательны. В тестовом JSON используются имена из заглавных латинских букв. Каждый пакет, указанный в зависимостях, должен присутствовать в файле как отдельный ключ, даже если у него нет зависимостей.

## Основные функции

**`main.py`**

- `arguments()` проверяет аргументы запуска.
- `print_configuration()` выводит настройки для первого этапа.
- `save_diagrams()` сохраняет D2 и SVG.
- `main()` выполняет выбранный этап.

**`graph.py`**

- `load_test_repo()` читает тестовый репозиторий из JSON.
- `fetch_json()` получает данные по HTTP.
- `load_registry()` загружает информацию о зависимостях из API реестра.
- `select_version()` подбирает подходящую версию зависимости.
- `build_graph()` строит граф обходом BFS с рекурсией по уровням.
- `loading_order()` определяет порядок зависимостей и обнаруживает циклы.

**`semver.py`**

Функции `parse_version()`, `matches()`, `compare()` и вспомогательные функции разбирают версии и проверяют ограничения совместимости.

**`render.py`**

- `make_d2()` формирует описание графа на языке D2.
- `make_svg()` строит изображение SVG.
- `make_tree()` выводит текстовое дерево.
- `layout()` вычисляет расположение узлов графа.

## Примеры по этапам

### Этап 1. Параметры запуска

```sh
python src/main.py --test --repository examples/repository.json --package A --version test --stage 1
```

Программа выводит введённые настройки. Для проверки ошибок можно указать несуществующий JSON-файл или пропустить обязательный аргумент.

### Этап 2. Прямые зависимости

Тестовый репозиторий:

```sh
python src/main.py --test --repository examples/repository.json --package A --version test --stage 2
```

Для пакета `A` выводятся зависимости `B` и `C`.

Пример запроса к реестру:

```sh
python src/main.py --repository https://crates.io --package serde --version 1.0.0 --stage 2
```

Для этой команды нужен доступ к интернету.

### Этап 3. Построение графа

```sh
python src/main.py --test --repository examples/repository.json --package A --version test --stage 3
python src/main.py --test --repository examples/repository.json --package A --version test --filter B --stage 3
python src/main.py --test --repository examples/cycle.json --package A --version test --stage 3
```

Граф строится обходом BFS. Рекурсия используется для перехода к следующему уровню обхода. Повторно посещённые узлы не обрабатываются, поэтому наличие цикла не приводит к бесконечному обходу.

### Этап 4. Порядок загрузки

```sh
python src/main.py --test --repository examples/repository.json --package A --version test --stage 4
python src/main.py --test --repository examples/cycle.json --package A --version test --stage 4
```

Для обычного графа зависимости выводятся раньше пакета, который их использует. Для циклического графа программа сообщает об ошибке: построить топологический порядок невозможно.

### Этап 5. Визуализация

```sh
python src/main.py --test --repository examples/repository.json --package A --version test --ascii --output examples/a.svg
python src/main.py --test --repository examples/repository.json --package E --version test --ascii --output examples/e.svg
python src/main.py --test --repository examples/repository.json --package F --version test --ascii --output examples/f.svg
```

Для каждого пакета создаются два файла: `.d2` с описанием графа и `.svg` с изображением. SVG можно открыть в браузере. Параметр `--ascii` выводит зависимости в консоль.

## Тесты

```sh
python -m unittest discover -s tests -v
```

Тесты проверяют обход графа, фильтрацию, циклы, порядок зависимостей, обработку версий и создание представлений графа.



