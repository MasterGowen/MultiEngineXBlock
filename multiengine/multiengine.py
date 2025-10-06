# -*- coding: utf-8 -*-
"""XBlock для проверки json-объектов, сформированных по определенным правилам.
Поддерживает различные типы заданий через систему сценариев."""

import datetime
import pkg_resources
import pytz
import json
import os
from pathlib import Path
import logging
import copy
import ast

from django.template import Context, Template
from django.core.exceptions import PermissionDenied

from common.djangoapps.student.models import user_by_anonymous_id
from submissions import api as submissions_api
from submissions.models import StudentItem as SubmissionsStudent

import xblock
from xblock.core import XBlock
from xblock.fields import Scope, Integer, String, JSONField, Boolean
from xblock.fragment import Fragment

from xmodule.util.duedate import get_extended_due_date

from webob.response import Response

# Django 4.2 использует smart_str вместо smart_text
from django.utils.encoding import smart_str

logger = logging.getLogger(__name__)


def reify(meth):
    """
    Декоратор, кэширующий значение, чтобы оно вычислялось только один раз.
    """
    def getter(inst):
        value = meth(inst)
        inst.__dict__[meth.__name__] = value
        return value
    return property(getter)


class MultiEngineXBlock(XBlock):
    icon_class = 'problem'
    has_score = True

    # Настройки (settings)
    display_name = String(
        display_name='Название',
        help='Название задания, которое увидят студенты.',
        default='MultiEngine',
        scope=Scope.settings
    )

    question = String(
        display_name='Вопрос',
        help='Текст задания.',
        default='Вы готовы?',
        scope=Scope.settings
    )

    correct_answer = JSONField(
        display_name='Правильный ответ',
        help='Скрытое поле для правильного ответа в формате json.',
        default={},
        scope=Scope.settings
    )

    weight = Integer(
        display_name='Максимальное количество баллов',
        help='Максимальное количество баллов которое может получить студент.',
        default=100,
        scope=Scope.settings
    )

    grade_steps = Integer(
        display_name='Шаг оценивания',
        help='Количество диапазонов оценивания',
        default=0,
        scope=Scope.settings
    )
    scenario = String(
        display_name='Сценарий',
        help='Выберите один из сценариев отображения задания.',
        scope=Scope.settings,
        default=None,
    )

    max_attempts = Integer(
        display_name='Максимальное количество попыток',
        help='',
        default=0,
        scope=Scope.settings
    )

    # Состояние пользователя (user_state)
    points = Integer(
        display_name='Количество баллов студента',
        default=0,
        scope=Scope.user_state
    )

    answer = JSONField(
        display_name='Ответ пользователя',
        default={'answer': {}},
        scope=Scope.user_state
    )

    attempts = Integer(
        display_name='Количество сделанных попыток',
        default=0,
        scope=Scope.user_state
    )

    student_state_json = JSONField(
        display_name='Сохраненное состояние',
        scope=Scope.user_state
    )

    student_view_template = String(
        display_name='Шаблон сценария',
        default='',
        scope=Scope.settings
    )

    sequence = Boolean(
        display_name='Учитывать последовательность выбранных вариантов?',
        help='Работает не для всех сценариев.',
        default=False,
        scope=Scope.settings
    )

    MULTIENGINE_ROOT = Path(__file__).absolute().parent.parent / 'multiengine'
    SCENARIOS_ROOT = Path('/edx/var/edxapp/multiengine/scenarios/')

    def load_scenarios(self, keys=None):
        """
        Загрузка сценариев из локального репозитория в список.
        """
        scenarios = {}
        _sc_keys = [
            'name::',
            'description::',
            'html::',
            'javascriptStudent::',
            'javascriptStudio::',
            'css::',
            'cssStudent::',
        ]
        if keys == 'get':
            return _sc_keys

        if self.SCENARIOS_ROOT.exists() and self.SCENARIOS_ROOT.is_dir():

            def _scenario_parser(scenario_file):
                _scenario_content = {}
                with open(self.SCENARIOS_ROOT / scenario_file, 'r', encoding='utf-8') as scf:
                    for line in scf:
                        if any(ext in line for ext in _sc_keys):
                            _current_key = line.strip().strip(':')
                        else:
                            if _current_key in _scenario_content:
                                _scenario_content[_current_key] += line
                            else:
                                _scenario_content[_current_key] = line.strip()
                return _scenario_content

            for scenario_file in self.SCENARIOS_ROOT.iterdir():
                if scenario_file.suffix == ".sc":
                    scenarios[scenario_file.stem] = _scenario_parser(scenario_file.name)

        return scenarios

    def get_scenario_content(self, scenario):
        """
        Получение текста сценария.
        """
        try:
            scenario_file = open(self.SCENARIOS_ROOT / f"{scenario}.cs", 'r', encoding='utf-8')
            with scenario_file as jsfile:
                scenario_content = jsfile.read()
        except Exception as e:
            logger.error(f'[MultiEngineXBlock]: Ошибка чтения сценария: {e}')
            scenario_content = 'alert("Scenario file not found!");'
        return scenario_content

    @staticmethod
    def resource_string(path):
        """
        Получение строковых ресурсов.
        """
        data = pkg_resources.resource_string(__name__, path)
        return data.decode('utf8')

    def load_resources(self, js_urls, css_urls, fragment):
        """
        Загрузка локальных статических ресурсов.
        """
        for js_url in js_urls:
            if js_url.startswith('public/'):
                fragment.add_javascript_url(self.runtime.local_resource_url(self, js_url))
            elif js_url.startswith('static/'):
                fragment.add_javascript(_resource(js_url))

        for css_url in css_urls:
            if css_url.startswith('public/'):
                fragment.add_css_url(self.runtime.local_resource_url(self, css_url))
            elif css_url.startswith('static/'):
                fragment.add_css(_resource(css_url))

    @property
    def course_id(self):
        return str(self.xmodule_runtime.course_id)  # pylint: disable=no-member

    def get_student_item_dict(self, anonymous_user_id=None):
        """Создание student_item_dict."""
        item_id = str(self.scope_ids.usage_id)
        course_id = self.course_id
        student_id = anonymous_user_id or self.xmodule_runtime.anonymous_student_id

        return {
            'student_id': student_id,
            'item_id': item_id,
            'course_id': course_id,
            'item_type': 'multiengine'
        }

    def student_view(self, *args, **kwargs):
        """
        Отображение MultiEngineXBlock студенту (LMS).
        """
        scenarios = self.load_scenarios()
        context = {
            'display_name': self.display_name,
            'weight': self.weight,
            'question': self.question,
            'attempts': self.attempts,
            'student_state_json': self.student_state_json,
            'scenario': self.scenario,
            'scenarios': scenarios,
        }

        # Логика оценки
        score = submissions_api.get_score(self.get_student_item_dict())
        self.runtime.publish(self, 'grade', {'value': float(self.points), 'max_value': float(self.weight)})

        # Добавление дополнительных параметров в контекст
        if self.max_attempts != 0:
            context['max_attempts'] = self.max_attempts
        if self.past_due():
            context['past_due'] = True
        if self.answer != '{}':
            context['points'] = self.points
        if answer_opportunity(self):
            context['answer_opportunity'] = True
        if self.is_course_staff() or self.is_instructor():
            context['is_course_staff'] = True

        fragment = Fragment()
        fragment.add_content(render_template('static/html/multiengine.html', context))
        self.load_resources(('static/js/multiengine.js',), ('static/css/multiengine.css',), fragment)
        fragment.initialize_js('MultiEngineXBlock')
        return fragment

    def studio_view(self, *args, **kwargs):
        """
        Отображение MultiEngineXBlock разработчику (CMS).
        """
        scenarios = self.load_scenarios()
        context = {
            'display_name': self.display_name,
            'weight': self.weight,
            'question': self.question,
            'scenario': self.scenario,
            'sequence': self.sequence,
            'max_attempts': self.max_attempts,
            'scenarios': scenarios,
        }

        if self.scenario:
            context['scenario_content'] = self.get_scenario_content(self.scenario)

        fragment = Fragment()
        fragment.add_content(render_template('static/html/multiengine_edit.html', context))
        self.load_resources(('static/js/multiengine_edit.js',), ('static/css/multiengine.css',), fragment)
        fragment.initialize_js('MultiEngineXBlockEdit')
        return fragment

    @staticmethod
    def workbench_scenarios():
        """Примеры сценариев для workbench."""
        return [
            ("MultiEngineXBlock",
             """<vertical_demo>
                <multiengine/>
                <multiengine/>
                <multiengine/>
                </vertical_demo>
             """),
        ]

    @XBlock.json_handler
    def save_student_state(self, data, suffix=''):
        """Сохранение состояния студента."""
        self.student_state_json = data
        return {'result': 'success'}

    @XBlock.handler
    def get_student_state(self, data, suffix=''):
        """Получение состояния студента."""
        return Response(body=self.student_state_json, content_type='application/json')

    @XBlock.handler
    def send_scenario(self, request, suffix=''):
        """Отправка сценария."""
        scenarios = self.load_scenarios()
        scenario_name = smart_str(self.scenario)
        context = {}

        if scenario_name in scenarios:
            for key in self.load_scenarios('get'):
                clean_key = key.strip(':')
                if clean_key in scenarios[scenario_name]:
                    context[clean_key] = scenarios[scenario_name][clean_key].strip()
        else:
            context = {
                'name': '',
                'html': 'Scenario not found',
                'css': '',
                'javascriptStudent': '',
                'javascriptStudio': '',
                'description': '',
                'cssStudent': '',
            }

        return Response(json.dumps(context), content_type='text/plain')

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """Обработка данных из студии."""
        self.display_name = data.get('display_name')
        self.question = data.get('question')
        self.weight = data.get('weight')
        self.correct_answer = data.get('correct_answer')
        self.sequence = data.get('sequence')
        self.scenario = data.get('scenario')
        self.max_attempts = data.get('max_attempts')
        self.student_view_template = data.get('student_view_template')
        return {'result': 'success'}

    @XBlock.json_handler
    def student_submit(self, data, suffix=''):
        """Обработка ответа студента."""
        student_json = json.loads(data)
        student_answer = student_json['answer']
        self.answer = data

        try:
            correct_json = json.loads(self.correct_answer)
        except json.JSONDecodeError:
            logger.warning('[MultiEngineXBlock]: Некорректный правильный ответ')
            correct_json = {'answer': []}

        correct_answer = correct_json.get('answer', [])
        settings = correct_json.get('settings', {'sequence': self.sequence})

        def multicheck(student_answer, correct_answer, settings):
            """Сравнение ответов."""
            keywords = ('or', 'and', 'not', 'or-and')

            def compare_not_sequenced():
                # Реализация сравнения без учета последовательности
                pass

            def compare_sequenced():
                # Реализация сравнения с учетом последовательности
                pass

            if settings.get('sequence', False):
                result = compare_sequenced()
            else:
                result = compare_not_sequenced()

            return int(round(result * self.weight)), result

        if answer_opportunity(self):
            correct, result = multicheck(student_answer, correct_answer, settings)
            self.points = correct
            self.attempts += 1

            self.runtime.publish(self, 'grade', {'value': correct, 'max_value': self.weight})
            return {'result': 'success', 'correct': correct, 'weight': self.weight, 'attempts': self.attempts}
        else:
            return {'result': 'Max attempts exception!'}

    def past_due(self):
        """Проверка истечения срока."""
        due = get_extended_due_date(self)
        return due is None or _now() <= due

    def is_course_staff(self):
        """Проверка статуса преподавателя."""
        return getattr(self.xmodule_runtime, 'user_is_staff', False)

    def is_instructor(self):
        """Проверка статуса инструктора."""
        return self.xmodule_runtime.get_user_role() == 'instructor'


def answer_opportunity(self):
    """Проверка возможности ответа."""
    return self.max_attempts == 0 or self.attempts < self.max_attempts


def _now():
    """Текущее время."""
    return datetime.datetime.now(pytz.utc)


def _resource(path):  # pragma: NO COVER
    """Получение ресурса."""
    return pkg_resources.resource_string(__name__, path).decode('utf8')


def render_template(template_path, context=None):
    """Рендер шаблона."""
    if context is None:
        context = {}
    template_str = load_resource(template_path)
    return Template(template_str).render(Context(context))


def load_resource(resource_path):
    """Загрузка ресурса."""
    try:
        return smart_str(pkg_resources.resource_string(__name__, resource_path))
    except EnvironmentError:
        logger.debug(f'[MultiEngineXBlock]: Не найден ресурс {resource_path}')


def require(assertion):
    """Проверка условия."""
    if not assertion:
        raise PermissionDenied
