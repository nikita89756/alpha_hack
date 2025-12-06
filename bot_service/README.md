# AI Copilot for Microbusiness

AI Copilot — мультиагентная RAG-платформа на FastAPI, которая помогает владельцам микробизнеса отвечать на вопросы на основе собственной базы знаний (Qdrant) и персональной памяти пользователя. Система включает основной диалоговый конвейер, контроллер памяти и отдельный пайплайн анализа договоров.

## Содержание
- [Возможности](#возможности)
- [Архитектура](#архитектура)
- [Структура репозитория](#структура-репозитория)
- [Технологический стек](#технологический-стек)
- [Требования и подготовка окружения](#требования-и-подготовка-окружения)
- [Пример .env](#пример-env)
- [Запуск API](#запуск-api)
- [HTTP API](#http-api)
- [Управление знаниями и памятью](#управление-знаниями-и-памятью)
- [Пайплайн анализа контрактов](#пайплайн-анализа-контрактов)
- [CLI и ноутбуки](#cli-и-ноутбуки)
- [Качество и отладка](#качество-и-отладка)
- [Расширение и кастомизация](#расширение-и-кастомизация)

## Возможности
- Мультиагентный LangGraph-конвейер (`ai_assistant/agent_system/service/pipeline.py`) с IntentRewrite, Retrieval, RAG-валидацией, fallback web-search и валидатором ответа.
- Управление долгосрочной памятью пользователя через `MemoryController` (Qdrant `long_term_memory`).
- Пайплайн анализа договоров (`contract_analysis/system.py`) с отдельными агентами intent/reviewer/drafter и автоматическим выбором стратегии контекста.
- REST API на FastAPI (`web/api.py`) с эндпоинтами `/answer`, `/memory/memorize`, `/contract/analyze`.
- Qdrant + DeepPavlov BERT-энкодер (`ai_assistant/agent_system/rag/controller.py`) для dense retrieval.
- CLI-утилиты и Jupyter-ноутбуки для ручного тестирования (`artifacts/`).
- Dockerfile и стандартизованные зависимости (`requirements.txt`, `pyproject.toml`).

## Архитектура
```
FastAPI (web/api.py)
├─ InterviewSession (ai_assistant/agent_system/app.py)
│  └─ AgentPipeline (service/pipeline.py)
│     ├─ IntentRewriteAgent
│     ├─ RetrievalAgent  ─┐
│     ├─ RagValidatorAgent│
│     ├─ WebSearcherAgent│  Qdrant (RetrieverController)
│     ├─ AnswerAgent     │    ├─ knowledge_base collection
│     └─ ValidationAgent ┘    └─ long_term_memory collection
├─ MemoryController (agent_system/memory/memory_controller.py)
└─ ContractAnalysisSystem (contract_analysis/system.py)
   ├─ ContractIntentAgent
   ├─ RagValidatorAgent + WebSearcher
   ├─ ContractReviewerAgent / ContractDraftAgent
   └─ DISCLAIMER и выдача структуры intent/context/result
```

## Валидация источников

Система использует многоуровневую валидацию источников для обеспечения достоверности информации:

### 1. RAG-валидация (RagValidatorAgent)
- Автоматическая проверка релевантности извлеченных фрагментов к запросу
- Оценка достоверности источников на основе их происхождения и метаданных
- Фильтрация устаревшей или неподтвержденной информации

### 2. Валидация ответа (ValidationAgent)
- Проверка соответствия ответа исходному запросу
- Верификация фактов, упомянутых в ответе
- Обнаружение и фильтрация галлюцинаций и противоречий

### 3. Валидация веб-источников (WebSearcherAgent)
- Проверка достоверности доменов
- Оценка авторитетности источников
- Отсеивание сомнительных или ненадежных ресурсов

### 4. Валидация в памяти (MemoryController)
- Проверка фактов перед сохранением в долгосрочную память
- Устранение противоречий с уже известной информацией
- Обеспечение консистентности данных

### 5. Валидация в пайплайне анализа контрактов
- Проверка юридической корректности извлеченных положений
- Верификация ссылок на нормативные акты
- Контроль целостности документа

## Структура репозитория
```
.
├── ai_assistant/
│   ├── agent_system/
│   │   ├── agents/                  # Intent, Answer, Validator, WebSearcher и т.д.
│   │   ├── memory/                  # MemoryController и промпты извлечения фактов
│   │   ├── rag/                     # RetrieverController + BertSentenceEncoder
│   │   ├── service/pipeline.py      # LangGraph-конвейер диалога
│   │   ├── utils/                   # AsyncLLMClient, logger, загрузка моделей
│   │   ├── app.py                   # Orchestrator сессии
│   │   └── config.py
├── contract_analysis/
│   ├── agents/                      # intent / reviewer / drafter
│   ├── config.py                    # настройки температур, лимитов и т.д.
│   ├── prompts.py                   # шаблоны подсказок и DISCLAIMER
│   └── system.py                    # отдельный LangGraph для договоров
├── web/
│   ├── api.py                       # FastAPI-приложение и endpoints
│   ├── config.py                    # параметры инференса
│   └── shemas.py                    # Pydantic-схемы
├── artifacts/
│   ├── chat_cli.py                  # CLI для проверки /answer
│   ├── doc_analysis.ipynb
│   ├── interactive_interview.ipynb
│   └── promt_stend.ipynb
├── Dockerfile
├── requirements.txt
├── pyproject.toml                    # ruff + mypy конфигурация
└── main.py                           # uvicorn entrypoint (python main.py)
```

## Технологический стек
- Python 3.12, FastAPI, Uvicorn
- LangGraph, langchain-core, langchain-community
- httpx + OpenRouter (модель `deepseek/deepseek-chat-v3.1` по умолчанию)
- Qdrant (cloud/on-prem) и DeepPavlov RuBERT для dense retrieval
- Jupyter/IPython для интерактивных сценариев
- Ruff + mypy для статического анализа

## Требования и подготовка окружения
1. Установите Python ≥3.12, Git и Docker (по необходимости).
2. Подготовьте Qdrant (cloud URL или локальный `docker run qdrant/qdrant`).
3. Получите OpenRouter API key (LLM).
4. Клонируйте репозиторий и установите зависимости:

   ```bash
   git clone https://github.com/<org>/<repo>.git
   cd <repo>
   python -m venv .venv
   .\\.venv\\Scripts\\activate          # Windows
   pip install --upgrade pip
   pip install -r requirements.txt   # или pip install -e .
   ```

5. Скопируйте `.env` и заполните ключевые переменные.

## Пример .env
```env
# LLM
LLM_API_KEY=<openrouter_key>
OPENROUTER_CHAT_BASE=https://openrouter.ai/api/v1/chat/completions

# FastAPI
HOST=0.0.0.0
PORT=8000

# Qdrant
QDRANT_URL=https://<cluster>.qdrant.cloud
QDRANT_API_KEY=<token>
QDRANT_KB_COLLECTION=knowledge_base
QDRANT_LTM_COLLECTION=long_term_memory
QDRANT_PREFER_GRPC=false

# Contract analysis tuning (опционально)
CONTRACT_ANALYSIS_KB_LIMIT=6
CONTRACT_ANALYSIS_SOURCE=DocAnalysis
CONTRACT_DRAFT_TEMPERATURE=0.65

TOKENIZERS_PARALLELISM=false
```

## Запуск API
### Локально (разработка)
```bash
uvicorn web.api:app --host 0.0.0.0 --port 8000 --reload
# либо
python main.py                      # читает HOST/PORT и запускает uvicorn
```

### Docker
```bash
docker build -t ai-copilot .
docker run --env-file .env -p 8000:8004 ai-copilot \
  uvicorn web.api:app --host 0.0.0.0 --port 8004
```
По умолчанию Dockerfile слушает 8004 — пробросьте порт на 8000/https как нужно.

## HTTP API
### `POST /answer`
Запускает основной агентный конвейер.

```json
{
  "query": "Как закрыть кассовый разрыв к следующей неделе?",
  "history": [{"role": "user", "content": "Продажи падают"}],
  "user_id": 123
}
```

Ответ:
```json
{
  "answer": "<финальный текст>",
  "next_action": "continue",
  "kb": [{"id": "kb_42", "title": "Cash-flow план", "knowledge": "..."}],
  "ltm": [{"id": "ltm_7", "title": "Текущий проект", "knowledge": "..."}]
}
```

### `POST /memory/memorize`
Передаёт историю диалога и сохраняет факты в Qdrant `long_term_memory`.

```json
{
  "user_id": "123",
  "dialogue": [
    {"role": "user", "content": "Я владелец кофейни в Казани"},
    {"role": "assistant", "content": "Запомнила"}
  ]
}
```

Возвращает количество сохранённых фрагментов и их содержимое.

### `POST /contract/analyze`
Оркестрирует пайплайн анализа договоров. Возвращает структуру intent/context/result/disclaimer:

```json
{
  "intent": {
    "action": "analyze",
    "document_type": "NDA",
    "key_requirements": ["ограничение на 12 месяцев"],
    "notes": "",
    "raw": {...}
  },
  "context": {
    "source": "kb",
    "strategy": "kb",
    "notes": "",
    "items": [{"id": "doc:12", "title": "Clause A", "knowledge": "..."}]
  },
  "result": "<review/draft>",
  "disclaimer": "<DISC>"
}
```

## Управление знаниями и памятью
- **RetrieverController** (`ai_assistant/agent_system/rag/controller.py`) использует DeepPavlov RuBERT для эмбеддингов. При первом запуске чекпоинт качается из HF и кэшируется в `ai_assistant/agent_system/model`.
- **Коллекции Qdrant**:
  - `knowledge_base`: структурированные знания с полями `id`, `title`, `knowledge`, `source`, `metadata`.
  - `long_term_memory`: персональные факты (`user_id`, `knowledge`, `score`).
- **MemoryController** (`agent_system/memory/memory_controller.py`) выделяет факты из диалога, валидирует с помощью LLM и upsert'ит через RetrieverController.
- Для наполнения KB используйте собственный ETL или ноутбук `artifacts/doc_analysis.ipynb`, затем `retriever.upsert_knowledge_base(...)`.

## Пайплайн анализа контрактов
- Конфигурация агентов описана в `contract_analysis/config.py` и может переопределяться переменными `CONTRACT_*`.
- Граф (`contract_analysis/system.py`):
  1. `ContractIntentAgent` понимает действие (`analyze` / `draft`), тип документа и требования.
  2. `_prepare_context` ищет DocAnalysis фрагменты через RetrieverController, затем RagValidator выбирает стратегию (`kb`, `web_search`, `llm_only`); при необходимости подключается `WebSearcherAgent`.
  3. `ContractReviewerAgent` либо `ContractDraftAgent` генерирует результат.
  4. В ответ добавляется `DISCLAIMER_TEXT` (`contract_analysis/prompts.py`).
- Настройки: `CONTRACT_ANALYSIS_KB_LIMIT`, `CONTRACT_ANALYSIS_SOURCE`, `CONTRACT_INTENT_MAX_TOKENS` и т.д.

## CLI и ноутбуки
- `python artifacts/chat_cli.py history|exit --message "<text>"` — локальный тест диалогового API. История хранится в `artifacts/chat_history.json`.
- Jupyter:
  - `interactive_interview.ipynb` — шаг за шагом демонстрация `/answer`.
  - `doc_analysis.ipynb` — эксперименты с контекстом contract analysis.
  - `promt_stend.ipynb` — стенд для отладки промптов агентов.
Перед запуском ноутбуков установите `ipykernel` и активируйте нужное ядро.

## Качество и отладка
- Запускайте тесты и линты из корня:

  ```bash
  python -m pytest                     # (если добавлены тесты)
  ruff check ai_assistant contract_analysis web
  ruff format ai_assistant contract_analysis web
  mypy ai_assistant contract_analysis
  ```

- Логи настраиваются через `ai_assistant/agent_system/utils/logger.py` и выводятся в stdout (INFO по умолчанию).
- Частые проблемы:
  - `LLM_API_KEY` не задан → FastAPI не поднимется (ошибка в lifespan).
  - Нет доступа к Qdrant → RetrieverController бросит HTTP 500 при старте.
  - Hugging Face rate limit → добавьте `HF_HOME` и предварительно скачайте модель.

## Расширение и кастомизация
- Новые агенты LangGraph: добавьте класс в `ai_assistant/agent_system/agents/` и включите его в `AgentPipeline`.
- Смена модели OpenRouter: переопределите `InferenceConfig` или переменные окружения `OPENROUTER_CHAT_BASE` / `LLM_API_KEY`.
- Альтернативный retriever: замените `load_deeppavlov_bert` в `web/api.py` на собственный энкодер (sentence transformers, rerankers и т.д.).
- Новые типы памяти: расширьте `MemoryController.extract_and_validate` или добавьте отдельный эндпоинт в `web/api.py`.

---

AI Copilot рассчитан на быстрые эксперименты и адаптацию под доменные базы знаний: добавляйте собственные коллекции Qdrant, подключайте CRM/ERP и кастомизируйте ноутбуки. Contributions welcome!
