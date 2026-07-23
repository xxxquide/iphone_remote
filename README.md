# iphone_remote

**Локальный пульт управления и автоматизации для 1 Mac (Apple Silicon M2, macOS 26+) и 2 iPhone (iPhone 15 Pro Max / iOS 26 и iPhone XS Max / iOS 18).**

Это НЕ клон коммерческой "фермы телефонов". Это персональный, локальный инструмент: живой просмотр экранов подключённых iPhone, ограниченное управление и легитимная автоматизация через официальные механизмы Apple (XCUITest/WebDriverAgent, Shortcuts/App Intents, AVFoundation screen capture). Всё крутится на твоём Mac, без облака на старте.

> Технический due-diligence, целевая архитектура, roadmap и стартовый прототип. Полный разбор — в папке [`docs/`](docs/).

## Что важно понять сразу (реализм платформы)

- На **не-джейлбрейкнутом** iOS **нет** публичного API, чтобы инжектить тапы в произвольные приложения. Единственный легальный путь UI-автоматизации реального устройства — **XCUITest / WebDriverAgent** (подход Appium): нужна подпись Developer-сертификатом, включённый Developer Mode, смонтированный Developer Disk Image, периодический ре-подпис.
- **iPhone Mirroring** (macOS Sequoia+/26) даёт официальный просмотр+управление ТВОИМ iPhone с Mac, но **не автоматизируется** и работает с одним устройством за раз.
- Массовая автоматизация соц-аккаунтов нарушает ToS платформ и ведёт к банам — см. [`docs/legal-and-tos.md`](docs/legal-and-tos.md). Проект спроектирован под легитимные сценарии (свои устройства, свои аккаунты, тестирование, личные автоматизации).

## Структура

- `docs/` — исследование, архитектура, roadmap, backlog, риски, вопросы.
- `poc/` — Python-прототип для Phase 0/1 (проверка гипотез: обнаружение устройств, скриншот, WDA smoke-test).
- `mac-agent/` — скелет нативного macOS-агента (Swift, будущие фазы).

## Быстрый старт (проверка гипотез, Phase 0)

```bash
cd poc
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python check_devices.py      # список подключённых iPhone
python screenshot.py         # снять скриншот через DVT
python wda_smoke.py          # проверить WDA-сессию (после сборки WDA)
```

См. [`docs/09-first-plan.md`](docs/09-first-plan.md).
