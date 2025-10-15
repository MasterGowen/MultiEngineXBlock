# -*- coding: utf-8 -*-
"""
XBlock для проверки json-объектов, сформированных по определенным правилам.
Поддерживает различные типы заданий через систему сценариев.
"""

import copy
import datetime
import pytz
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from django.core.exceptions import PermissionDenied

from common.djangoapps.student.models import user_by_anonymous_id
from submissions import api as submissions_api

import xblock
from xblock.core import XBlock
from xblock.fields import Scope, Integer, String, JSONField, Boolean
from web_fragments.fragment import Fragment

from xblock.utils.resources import ResourceLoader
from xblock.exceptions import JsonHandlerError

resource_loader = ResourceLoader(__name__)

from xmodule.util.duedate import get_extended_due_date
from webob.response import Response
from django.utils.encoding import force_str

# Попытка импорта nh3 (если установлен)
try:
    from nh3 import clean as nh3_clean
    NH3_AVAILABLE = True
except ImportError:
    NH3_AVAILABLE = False
    def nh3_clean(html, **kwargs):
        return html  # fallback: no sanitization

logger = logging.getLogger(__name__)

ITEM_TYPE = "multiengine"
ATTR_KEY_ANONYMOUS_USER_ID = "edx-platform.anonymous_user_id"
ATTR_KEY_USER_IS_STAFF = "edx-platform.user_is_staff"
ATTR_KEY_USER_ROLE = "edx-platform.user_role"


def reify(meth):
    """Декоратор, кэширующий значение, чтобы оно вычислялось только один раз."""
    def getter(inst):
        value = meth(inst)
        inst.__dict__[meth.__name__] = value
        return value
    return property(getter)


def utcnow():
    """Get current date and time in UTC"""
    return datetime.datetime.now(tz=pytz.utc)


@XBlock.wants("settings")
@XBlock.needs("i18n", "user")
class MultiEngineXBlock(XBlock):
    """
    XBlock для многофункциональной проверки ответов студентов.
    Поддерживает различные сценарии проверки и оценивания.
    """

    icon_class = "problem"
    has_score = True

    # Настройки (settings)
    display_name = String(
        display_name="Название",
        help="Название задания, которое увидят студенты.",
        default="MultiEngine",
        scope=Scope.settings,
    )

    question = String(
        display_name="Вопрос",
        help="Текст задания.",
        default="Вы готовы?",
        scope=Scope.settings,
    )

    correct_answer = JSONField(
        display_name="Правильный ответ",
        help="Скрытое поле для правильного ответа в формате json.",
        default={},
        scope=Scope.settings,
    )

    weight = Integer(
        display_name="Максимальное количество баллов",
        help="Максимальное количество баллов которое может получить студент.",
        default=100,
        scope=Scope.settings,
    )

    # Удалено: grade_steps (не используется)

    scenario = String(
        display_name="Сценарий",
        help="Выберите один из сценариев отображения задания.",
        scope=Scope.settings,
        default=None,
    )

    max_attempts = Integer(
        display_name="Максимальное количество попыток",
        help="0 - неограниченное количество попыток",
        default=0,
        scope=Scope.settings,
    )

    # Состояние пользователя (user_state)
    points = Integer(
        display_name="Количество баллов студента", default=0, scope=Scope.user_state
    )

    answer = JSONField(
        display_name="Ответ пользователя",
        default={"answer": {}},
        scope=Scope.user_state,
    )

    attempts = Integer(
        display_name="Количество сделанных попыток", default=0, scope=Scope.user_state
    )

    student_state_json = JSONField(
        display_name="Сохраненное состояние",
        scope=Scope.user_state,
        default={},
    )

    student_view_template = String(
        display_name="Шаблон сценария", default="", scope=Scope.settings
    )

    sequence = Boolean(
        display_name="Учитывать последовательность выбранных вариантов?",
        help="Работает не для всех сценариев.",
        default=False,
        scope=Scope.settings,
    )

    # Константы путей
    MULTIENGINE_ROOT = Path(__file__).absolute().parent.parent / "multiengine"
    SCENARIOS_ROOT = MULTIENGINE_ROOT / "scenarios"

    def _parse_scenario_file(self, scenario_file: Path) -> Dict[str, str]:
        """Парсит содержимое одного файла сценария."""
        scenario_content: Dict[str, str] = {}
        current_key = ""
        scenario_keys = [
            "name::",
            "description::",
            "html::",
            "javascriptStudent::",
            "javascriptStudio::",
            "css::",
            "cssStudent::",
        ]

        try:
            with open(scenario_file, "r", encoding="utf-8") as scf:
                for line in scf:
                    if any(ext in line for ext in scenario_keys):
                        current_key = line.strip().strip(":")
                    else:
                        if current_key:
                            if current_key in scenario_content:
                                scenario_content[current_key] += line
                            else:
                                scenario_content[current_key] = line.rstrip('\n')
        except Exception as e:
            logger.error(f"[MultiEngineXBlock] Ошибка парсинга {scenario_file}: {e}")
            return {}

        return scenario_content

    def load_scenarios(self) -> Dict[str, Dict[str, str]]:
        """
        Загрузка и парсинг всех сценариев из директории.
        Returns:
            Dict[str, Dict[str, str]]: Словарь сценариев по имени файла
        """
        scenarios: Dict[str, Dict[str, str]] = {}

        if not (self.SCENARIOS_ROOT.exists() and self.SCENARIOS_ROOT.is_dir()):
            return scenarios

        for scenario_file in self.SCENARIOS_ROOT.iterdir():
            if scenario_file.suffix == ".sc":
                parsed = self._parse_scenario_file(scenario_file)
                if parsed:
                    scenarios[scenario_file.stem] = parsed

        return scenarios

    def resource_string(self, path):
        """Retrieve string contents for the file path"""
        path = os.path.join("static", path)
        return resource_loader.load_unicode(path)

    def load_resources(
        self, js_urls: tuple, css_urls: tuple, fragment: Fragment
    ) -> None:
        """Загрузка локальных статических ресурсов."""
        for js_url in js_urls:
            if js_url.startswith("public/"):
                fragment.add_javascript_url(
                    self.runtime.local_resource_url(self, js_url)
                )
            elif js_url.startswith("static/"):
                fragment.add_javascript(load_resource(js_url))

        for css_url in css_urls:
            if css_url.startswith("public/"):
                fragment.add_css_url(self.runtime.local_resource_url(self, css_url))
            elif css_url.startswith("static/"):
                fragment.add_css(load_resource(css_url))

    @reify
    def block_id(self):
        """Return the usage_id of the block."""
        return str(self.scope_ids.usage_id)

    @reify
    def block_course_id(self):
        """Return the course_id of the block."""
        return str(self.context_key)

    def get_student_item_dict(self, student_id=None):
        """Returns dict required by the submissions app."""
        if student_id is None and (user_service := self.runtime.service(self, "user")):
            student_id = user_service.get_current_user().opt_attrs.get(
                ATTR_KEY_ANONYMOUS_USER_ID
            )
            assert student_id != ("MOCK", "Forgot to call 'personalize' in test.")
        return {
            "student_id": student_id,
            "course_id": self.block_course_id,
            "item_id": self.block_id,
            "item_type": ITEM_TYPE,
        }

    def student_view(self, *args, **kwargs) -> Fragment:
        """Отображение студенту (LMS)."""
        scenarios = self.load_scenarios()

        context = {
            "display_name": self.display_name,
            "weight": self.weight,
            "question": self.question,
            "attempts": self.attempts,
            "student_state_json": self.student_state_json,
            "scenario": self.scenario,
            "scenarios": scenarios,
        }

        context["context"] = json.dumps(context)

        # Логика оценки
        try:
            score = submissions_api.get_score(self.get_student_item_dict())
        except Exception as e:
            logger.warning(f"[MultiEngineXBlock]: Ошибка получения оценки: {e}")
            score = None

        context.update(
            {
                "max_attempts": self.max_attempts if self.max_attempts != 0 else None,
                "past_due": bool(self.past_due()),
                "points": self.points if self.answer != "{}" else None,
                "has_attempts_left": self.has_attempts_left,
                "is_course_staff": self.is_course_staff() or self.is_instructor(),
            }
        )

        if self.max_attempts > 0 and self.has_attempts_left:
            context["is_last_attempt"] = self.attempts == self.max_attempts - 1

        fragment = Fragment()
        fragment.add_content(render_template("static/html/multiengine.html", context))
        self.load_resources(
            ("public/js/multiengine.js",), ("public/css/multiengine.css",), fragment
        )

        fragment.initialize_js("MultiEngineXBlock")
        return fragment

    def studio_view(self, *args, **kwargs) -> Fragment:
        """Отображение в студии (CMS)."""
        scenarios = self.load_scenarios()
        context = {
            "display_name": self.display_name,
            "weight": self.weight,
            "question": self.question,
            "scenario": self.scenario,
            "sequence": self.sequence,
            "max_attempts": self.max_attempts,
            "scenarios": scenarios,
            # УБРАНО: scenario_content (сырой .sc файл больше не вставляется в HTML)
        }

        fragment = Fragment()
        fragment.add_content(
            render_template("static/html/multiengine_edit.html", context)
        )
        self.load_resources(
            ("public/js/multiengine_edit.js",),
            ("public/css/multiengine.css",),
            fragment,
        )
        fragment.initialize_js("MultiEngineXBlockEdit")
        return fragment

    @staticmethod
    def workbench_scenarios() -> List[tuple]:
        """Примеры сценариев для workbench."""
        return [
            (
                "MultiEngineXBlock",
                """<vertical_demo>
                <multiengine/>
                <multiengine/>
                <multiengine/>
                </vertical_demo>
             """,
            ),
        ]

    @XBlock.json_handler
    def save_student_state(
        self, data: Dict[str, Any], suffix: str = ""
    ) -> Dict[str, str]:
        """Сохранение состояния студента."""
        self.student_state_json = data
        return {"result": "success"}

    @XBlock.handler
    def get_student_state(self, data, suffix: str = "") -> Response:
        """Получение состояния студента."""
        return Response(json_body=self.student_state_json)

    @XBlock.handler
    def send_scenario(self, request, suffix: str = "") -> Response:
        """Отправка сценария клиенту."""
        scenarios = self.load_scenarios()
        scenario_name = force_str(self.scenario) if self.scenario else ""
        context: Dict[str, str] = {}

        if scenario_name in scenarios:
            # Копируем все поля из спарсенного сценария
            context = {k: v for k, v in scenarios[scenario_name].items()}
        else:
            context = {
                "name": "",
                "html": "Scenario not found",
                "css": "",
                "javascriptStudent": "",
                "javascriptStudio": "",
                "description": "",
                "cssStudent": "",
            }

        return Response(json_body=context, content_type="application/json")

    @XBlock.json_handler
    def studio_submit(self, data: Dict[str, Any], suffix: str = "") -> Dict[str, str]:
        """Обработка данных из студии."""
        self.display_name = data.get("display_name", self.display_name)
        self.question = data.get("question", self.question)
        self.weight = int(data.get("weight", self.weight))

        # Валидация correct_answer
        raw_correct = data.get("correct_answer", "{}")
        try:
            json.loads(raw_correct)
            self.correct_answer = raw_correct
        except (json.JSONDecodeError, TypeError):
            logger.warning("[MultiEngineXBlock] Некорректный JSON в correct_answer")
            self.correct_answer = "{}"

        self.sequence = data.get("sequence", self.sequence)
        self.scenario = data.get("scenario", self.scenario)
        self.max_attempts = int(data.get("max_attempts", self.max_attempts))

        # Мягкая санитизация student_view_template
        raw_template = data.get("student_view_template", "")
        if NH3_AVAILABLE:
            # Разрешаем основные теги и атрибуты для интерактивных сценариев
            allowed_tags = {
                'div', 'span', 'p', 'table', 'thead', 'tbody', 'tr', 'td', 'th',
                'ul', 'ol', 'li', 'a', 'img', 'br', 'hr', 'b', 'i', 'u', 'strong', 'em'
            }
            allowed_attrs = {
                '*': ['class', 'id', 'style', 'title'],
                'a': ['href', 'target'],
                'img': ['src', 'alt', 'width', 'height']
            }
            self.student_view_template = nh3_clean(
                raw_template,
                tags=allowed_tags,
                attributes=allowed_attrs,
                strip_comments=True
            )
        else:
            # Без nh3 — минимальная очистка от опасных тегов
            self.student_view_template = raw_template.replace('<script', '<script')

        return {"result": "success"}

    @XBlock.json_handler
    def student_submit(self, data: Dict[str, Any], suffix: str = "") -> Dict[str, Any]:
        """Обработка ответа студента."""
        student_answer = data.get("answer", {})
        self.answer = data

        try:
            correct_json = (
                json.loads(self.correct_answer)
                if self.correct_answer
                else {"answer": []}
            )
        except json.JSONDecodeError:
            logger.warning("[MultiEngineXBlock]: Некорректный правильный ответ")
            correct_json = {"answer": []}

        correct_answer = correct_json.get("answer", [])
        settings = correct_json.get("settings", {"sequence": self.sequence})

        def multicheck(
            student_ans: Dict[str, Any],
            correct_ans: List[Any],
            check_settings: Dict[str, Any],
        ) -> tuple:
            """Сравнение ответов студента с правильными ответами."""
            # TODO: Реализовать логику сравнения ответов
            result = 0.0  # Заглушка
            return int(round(result * self.weight)), result

        if self.has_attempts_left:
            try:
                correct, result = multicheck(student_answer, correct_answer, settings)
                self.points = correct
                self.attempts += 1

                self.runtime.publish(
                    self, "grade", {"value": correct, "max_value": self.weight}
                )
                return {
                    "result": "success",
                    "correct": correct,
                    "weight": self.weight,
                    "attempts": self.attempts,
                }
            except Exception as e:
                logger.error(f"[MultiEngineXBlock]: Ошибка при проверке ответа: {e}")
                return {"result": "error", "message": "Check failed"}
        else:
            return {"result": "Max attempts exception!"}

    def past_due(self):
        """Проверка, прошла ли дата окончания задания."""
        due = get_extended_due_date(self)
        try:
            graceperiod = self.graceperiod
        except AttributeError:
            graceperiod = None

        if graceperiod is not None and due:
            close_date = due + graceperiod
        else:
            close_date = due

        if close_date is not None:
            return utcnow() > close_date
        return False

    def is_course_staff(self):
        """Check if user is course staff."""
        if user_service := self.runtime.service(self, "user"):
            return user_service.get_current_user().opt_attrs.get(ATTR_KEY_USER_IS_STAFF)
        return False

    def is_instructor(self):
        """Проверка статуса инструктора."""
        if user_service := self.runtime.service(self, "user"):
            return (
                user_service.get_current_user().opt_attrs.get(ATTR_KEY_USER_ROLE)
                == "instructor"
            )
        return False

    @property
    def has_attempts_left(self) -> bool:
        """Вернуть True, если студент может подать еще одну попытку."""
        return self.max_attempts == 0 or self.attempts < self.max_attempts


def _now() -> datetime.datetime:
    """Получение текущего времени в UTC."""
    return datetime.datetime.now(pytz.utc)


def render_template(
    template_path: str, context: Optional[Dict[str, Any]] = None
) -> str:
    """Рендер шаблона с контекстом."""
    if context is None:
        context = {}
    return resource_loader.render_django_template(template_path, context)


def load_resource(resource_path: str) -> str:
    """Загрузка ресурса по пути."""
    try:
        return resource_loader.load_unicode(resource_path)
    except EnvironmentError as e:
        logger.warning(f"[MultiEngineXBlock]: Не найден ресурс {resource_path}: {e}")
        return ""


def require(assertion: bool) -> None:
    """Проверка условия, выбрасывает PermissionDenied при невыполнении."""
    if not assertion:
        raise PermissionDenied()