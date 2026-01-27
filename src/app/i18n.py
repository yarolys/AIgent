"""Internationalization support for agent communication."""

from typing import Any

# Russian translations for agent communication
RU_TRANSLATIONS = {
    # Agent thoughts and status
    "starting_task": "Начинаю задачу: {task}",
    "task_complete": "Задача выполнена: {summary}",
    "task_failed": "Задача не удалась: {reason}",
    "needs_user_input": "Требуется ввод пользователя: {reason}",
    "action_cancelled": "Действие отменено пользователем",
    "recovery_attempt": "Попытка восстановления: {description}",

    # Tool operations
    "tool_navigating": "Переход на: {url}",
    "tool_clicking": "Нажимаю на элемент: {selector}",
    "tool_typing": "Ввожу текст: '{text}'",
    "tool_pressing": "Нажимаю клавишу: {keys}",
    "tool_scrolling": "Прокручиваю: {direction}",
    "tool_searching_dom": "Ищу в DOM: '{query}'",
    "tool_waiting": "Ожидаю {ms}мс",
    "tool_screenshot": "Делаю скриншот",
    "tool_closing_popups": "Закрываю всплывающие окна",
    "tool_getting_url": "Получаю текущий URL",
    "tool_hovering": "Наведение на: {selector}",
    "tool_going_back": "Возврат на предыдущую страницу",

    # Tool results
    "result_success": "успешно",
    "result_failed": "не удалось",
    "result_found_elements": "найдено {count} элементов",
    "result_no_elements": "элементы не найдены",
    "result_navigated": "перешёл на {url}",
    "result_typed": "ввёл '{text}'",
    "result_clicked": "нажал",
    "result_pressed": "нажал {keys}",
    "result_scrolled": "прокрутил {direction}",
    "result_timeout": "таймаут",

    # Security
    "security_check_required": "⚠️  Требуется проверка безопасности",
    "security_action": "Действие",
    "security_reason": "Причина",
    "security_confirm_needed": "Требуется подтверждение",
    "confirm_prompt": "Продолжить с этим действием?",
    "confirm_yes_no": "Подтвердите (да/нет): ",
    "confirm_enter_yes_no": "Введите 'да' или 'нет'",

    # Sub-agents
    "dom_analyst": "Анализатор DOM",
    "dom_processing_query": "Обрабатываю запрос: {query}",
    "dom_no_candidates": "Нет кандидатов для анализа",
    "dom_high_confidence": "Найдено с высокой уверенностью: [{id}] {text}",
    "dom_low_confidence": "Низкая уверенность - консультируюсь с LLM",
    "dom_selected": "Выбран: [{id}] уверенность={score:.2f}",

    # Orchestrator communication
    "orch_observing": "Наблюдаю за страницей...",
    "orch_thinking": "Думаю над следующим шагом...",
    "orch_executing": "Выполняю: {tool}",
    "orch_step": "Шаг {step}",
    "orch_max_steps": "Достигнут лимит шагов ({max_steps})",

    # Final report
    "report_task_completed": "Задача выполнена",
    "report_task_failed": "Задача не выполнена",
    "report_waiting_user": "Ожидание пользователя",
    "report_execution_finished": "Выполнение завершено",
    "report_status": "Статус",
    "report_steps": "Шагов",
    "report_summary": "Итог",

    # Welcome message
    "welcome_title": "Добро пожаловать",
    "welcome_text": (
        "🤖 AIgent - Автономный браузерный агент\n\n"
        "Введите задачу и нажмите Enter. Введите 'выход' для завершения.\n"
        "Агент запросит подтверждение перед важными действиями."
    ),

    # Task start
    "new_task": "📋 Новая задача",

    # Errors
    "error": "Ошибка",
    "step_error": "Ошибка на шаге {step}: {error}",
    "llm_no_response": "LLM не ответил",
    "unknown_tool": "Неизвестный инструмент: {tool}",

    # Agent communication prefixes
    "agent_says": "🤖 Агент",
    "subagent_says": "↳ {name}",
    "orchestrator_says": "🎯 Оркестратор",
    "dom_analyst_says": "🔍 Анализатор",
    "llm_says": "🧠 LLM",
}

# English fallback translations
EN_TRANSLATIONS = {
    "starting_task": "Starting task: {task}",
    "task_complete": "Task complete: {summary}",
    "task_failed": "Task failed: {reason}",
    "needs_user_input": "Needs user input: {reason}",
    "action_cancelled": "Action cancelled by user",
    "recovery_attempt": "Recovery attempt: {description}",

    "tool_navigating": "Navigating to: {url}",
    "tool_clicking": "Clicking: {selector}",
    "tool_typing": "Typing: '{text}'",
    "tool_pressing": "Pressing: {keys}",
    "tool_scrolling": "Scrolling: {direction}",
    "tool_searching_dom": "Searching DOM: '{query}'",
    "tool_waiting": "Waiting {ms}ms",
    "tool_screenshot": "Taking screenshot",
    "tool_closing_popups": "Closing popups",
    "tool_getting_url": "Getting current URL",
    "tool_hovering": "Hovering: {selector}",
    "tool_going_back": "Going back",

    "result_success": "success",
    "result_failed": "failed",
    "result_found_elements": "found {count} elements",
    "result_no_elements": "no elements found",
    "result_navigated": "navigated to {url}",
    "result_typed": "typed '{text}'",
    "result_clicked": "clicked",
    "result_pressed": "pressed {keys}",
    "result_scrolled": "scrolled {direction}",
    "result_timeout": "timeout",

    "security_check_required": "⚠️  Security Check Required",
    "security_action": "Action",
    "security_reason": "Reason",
    "security_confirm_needed": "Confirmation Needed",
    "confirm_prompt": "Proceed with this action?",
    "confirm_yes_no": "Confirm (yes/no): ",
    "confirm_enter_yes_no": "Please enter 'yes' or 'no'",

    "dom_analyst": "DOM Analyst",
    "dom_processing_query": "Processing query: {query}",
    "dom_no_candidates": "No candidates to analyze",
    "dom_high_confidence": "High confidence match: [{id}] {text}",
    "dom_low_confidence": "Low confidence - consulting LLM",
    "dom_selected": "Selected: [{id}] score={score:.2f}",

    "orch_observing": "Observing page...",
    "orch_thinking": "Thinking about next step...",
    "orch_executing": "Executing: {tool}",
    "orch_step": "Step {step}",
    "orch_max_steps": "Max steps ({max_steps}) reached",

    "report_task_completed": "Task Completed",
    "report_task_failed": "Task Failed",
    "report_waiting_user": "Waiting for User",
    "report_execution_finished": "Execution Finished",
    "report_status": "Status",
    "report_steps": "Steps",
    "report_summary": "Summary",

    "welcome_title": "Welcome",
    "welcome_text": (
        "🤖 AIgent - Autonomous Browser Agent\n\n"
        "Type your task and press Enter. Type 'quit' to exit.\n"
        "The agent will ask for confirmation before sensitive actions."
    ),

    "new_task": "📋 New Task",

    "error": "Error",
    "step_error": "Step {step} error: {error}",
    "llm_no_response": "LLM did not respond",
    "unknown_tool": "Unknown tool: {tool}",

    "agent_says": "🤖 Agent",
    "subagent_says": "↳ {name}",
    "orchestrator_says": "🎯 Orchestrator",
    "dom_analyst_says": "🔍 Analyst",
    "llm_says": "🧠 LLM",
}

# Current language
_current_lang = "ru"
_translations = {
    "ru": RU_TRANSLATIONS,
    "en": EN_TRANSLATIONS,
}


def set_language(lang: str) -> None:
    """Set the current language (ru/en)."""
    global _current_lang
    if lang in _translations:
        _current_lang = lang


def get_language() -> str:
    """Get the current language."""
    return _current_lang


def t(key: str, **kwargs: Any) -> str:
    """
    Translate a key to the current language.

    Args:
        key: Translation key
        **kwargs: Format arguments

    Returns:
        Translated string
    """
    translations = _translations.get(_current_lang, EN_TRANSLATIONS)
    template = translations.get(key, EN_TRANSLATIONS.get(key, key))

    try:
        return template.format(**kwargs) if kwargs else template
    except KeyError:
        return template
