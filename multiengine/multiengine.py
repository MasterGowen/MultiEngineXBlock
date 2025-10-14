# -*- coding: utf-8 -*-
"""
XBlock для проверки json-объектов, сформированных по определенным правилам.
Поддерживает различные типы заданий через систему сценариев.
"""


import copy
import datetime
import pkg_resources
import pytz
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from django.template import Context, Template
from django.core.exceptions import PermissionDenied

from common.djangoapps.student.models import user_by_anonymous_id
from submissions import api as submissions_api
from submissions.models import StudentItem as SubmissionsStudent

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

logger = logging.getLogger(__name__)

ITEM_TYPE = "multiengine"
ATTR_KEY_ANONYMOUS_USER_ID = 'edx-platform.anonymous_user_id'
ATTR_KEY_USER_IS_STAFF = 'edx-platform.user_is_staff'
ATTR_KEY_USER_ROLE = 'edx-platform.user_role'


def reify(meth):
    """
    Декоратор, кэширующий значение, чтобы оно вычислялось только один раз.
    
    Args:
        meth (function): Метод для кэширования
        
    Returns:
        property: Свойство с кэшированным значением
    """
    def getter(inst):
        value = meth(inst)
        inst.__dict__[meth.__name__] = value
        return value
    return property(getter)

def utcnow():
    """
    Get current date and time in UTC
    """
    return datetime.datetime.now(tz=pytz.utc)


@XBlock.wants('settings')
@XBlock.needs("i18n", "user")
class MultiEngineXBlock(XBlock):
    """
    XBlock для многофункциональной проверки ответов студентов.
    
    Поддерживает различные сценарии проверки и оценивания.
    """
    
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
        help='0 - неограниченное количество попыток',
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
        scope=Scope.user_state,
        default={},
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

    # Константы путей
    MULTIENGINE_ROOT = Path(__file__).absolute().parent.parent / 'multiengine'
    SCENARIOS_ROOT = MULTIENGINE_ROOT / 'scenarios'

    def load_scenarios(self, keys: Optional[str] = None):
        """
        Загрузка сценариев из локального репозитория в список.
        
        Args:
            keys (Optional[str]): Если 'get', возвращает список ключей
            
        Returns:
            Union[Dict[str, Dict[str, str]], List[str]]: Словарь сценариев или список ключей
        """
        scenarios: Dict[str, Dict[str, str]] = {}
        scenario_keys = [
            'name::',
            'description::',
            'html::',
            'javascriptStudent::',
            'javascriptStudio::',
            'css::',
            'cssStudent::',
        ]
        
        if keys == 'get':
            return scenario_keys

        if self.SCENARIOS_ROOT.exists() and self.SCENARIOS_ROOT.is_dir():
            def _scenario_parser(scenario_file: str) -> Dict[str, str]:
                """Парсер содержимого файла сценария."""
                scenario_content: Dict[str, str] = {}
                current_key = ""
                
                with open(self.SCENARIOS_ROOT / scenario_file, 'r', encoding='utf-8') as scf:
                    for line in scf:
                        if any(ext in line for ext in scenario_keys):
                            current_key = line.strip().strip(':')
                        else:
                            if current_key in scenario_content:
                                scenario_content[current_key] += line
                            else:
                                scenario_content[current_key] = line.strip()
                return scenario_content

            for scenario_file in self.SCENARIOS_ROOT.iterdir():
                if scenario_file.suffix == ".sc":
                    scenarios[scenario_file.stem] = _scenario_parser(scenario_file.name)

        return scenarios

    def get_scenario_content(self, scenario: str) -> str:
        """
        Получение текста сценария.
        
        Args:
            scenario (str): Имя сценария
            
        Returns:
            str: Содержимое сценария или сообщение об ошибке
        """
        try:
            scenario_path = self.SCENARIOS_ROOT / f"{scenario}.sc"
            if scenario_path.exists():
                with open(scenario_path, 'r', encoding='utf-8') as jsfile:
                    scenario_content = jsfile.read()
            else:
                logger.warning(f'[MultiEngineXBlock]: Сценарий не найден: {scenario_path}')
                scenario_content = 'alert("Scenario file not found!");'
        except Exception as e:
            logger.error(f'[MultiEngineXBlock]: Ошибка чтения сценария {scenario}: {e}')
            scenario_content = 'alert("Scenario file not found!");'
        return scenario_content

    def resource_string(self, path):
        """
        Retrieve string contents for the file path
        """
        path = os.path.join('static', path)
        return resource_loader.load_unicode(path)

    def load_resources(self, js_urls: tuple, css_urls: tuple, fragment: Fragment) -> None:
        """
        Загрузка локальных статических ресурсов.
        
        Args:
            js_urls (tuple): Кортеж URL JavaScript файлов
            css_urls (tuple): Кортеж URL CSS файлов
            fragment (Fragment): Фрагмент для добавления ресурсов
        """
        for js_url in js_urls:
            if js_url.startswith('public/'):
                fragment.add_javascript_url(self.runtime.local_resource_url(self, js_url))
            elif js_url.startswith('static/'):
                fragment.add_javascript(load_resource(js_url))

        for css_url in css_urls:
            if css_url.startswith('public/'):
                fragment.add_css_url(self.runtime.local_resource_url(self, css_url))
            elif css_url.startswith('static/'):
                fragment.add_css(load_resource(css_url))

    @reify
    def block_id(self):
        """
        Return the usage_id of the block.
        """
        return str(self.scope_ids.usage_id)
    
    @reify
    def block_course_id(self):
        """
        Return the course_id of the block.

        Note: if this block is used in a Content Library, the returned ID will be the library's ID.
        """
        return str(self.context_key)

    def get_student_item_dict(self, student_id=None):
        """
        Returns dict required by the submissions app for creating and
        retrieving submissions for a particular student.
        """
        if student_id is None and (user_service := self.runtime.service(self, 'user')):
            student_id = user_service.get_current_user().opt_attrs.get(ATTR_KEY_ANONYMOUS_USER_ID)
            assert student_id != ("MOCK", "Forgot to call 'personalize' in test.")
        return {
            "student_id": student_id,
            "course_id": self.block_course_id,
            "item_id": self.block_id,
            "item_type": ITEM_TYPE,
        }


    def student_view(self, *args, **kwargs) -> Fragment:
        """
        Отображение MultiEngineXBlock студенту (LMS).
        
        Returns:
            Fragment: HTML фрагмент для отображения студенту
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

        # Make a copy of the context and put it into the context itself in the context field
        context['context'] = json.dumps(context)

        # Логика оценки
        try:
            score = submissions_api.get_score(self.get_student_item_dict())
        except Exception as e:
            logger.warning(f'[MultiEngineXBlock]: Ошибка получения оценки: {e}')
            score = None
            
        self.runtime.publish(
            self, 
            'grade', 
            {'value': float(self.points), 'max_value': float(self.weight)}
        )

        context.update({
            'max_attempts': self.max_attempts if self.max_attempts != 0 else None,
            'past_due': bool(self.past_due()),
            'points': self.points if self.answer != '{}' else None,
            'has_attempts_left': has_attempts_left(self),
            'is_course_staff': self.is_course_staff() or self.is_instructor(),
        })

        if self.max_attempts > 0 and has_attempts_left(self):
            context['is_last_attempt'] = (self.attempts == self.max_attempts - 1)

        fragment = Fragment()
        fragment.add_content(render_template('static/html/multiengine.html', context))
        self.load_resources(('static/js/multiengine.js',), ('static/css/multiengine.css',), fragment)

        self.include_theme_files(fragment)

        fragment.initialize_js('MultiEngineXBlock')
        # TODO: возможно добавлять контекст в js
        # fragment.initialize_js('MultiEngineXBlock', self.get_configuration())
        return fragment

    def studio_view(self, *args, **kwargs) -> Fragment:
        """
        Отображение MultiEngineXBlock разработчику (CMS).
        
        Returns:
            Fragment: HTML фрагмент для отображения в студии
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
    def workbench_scenarios() -> List[tuple]:
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
    def save_student_state(self, data: Dict[str, Any], suffix: str = '') -> Dict[str, str]:
        """
        Сохранение состояния студента.
        
        Args:
            data (Dict[str, Any]): Данные состояния студента
            suffix (str): Дополнительный суффикс
            
        Returns:
            Dict[str, str]: Результат операции
        """
        self.student_state_json = data
        return {'result': 'success'}

    @XBlock.handler
    def get_student_state(self, data, suffix: str = '') -> Response:
        """
        Получение состояния студента.
        
        Args:
            data: Данные запроса
            suffix (str): Дополнительный суффикс
            
        Returns:
            Response: HTTP ответ с состоянием студента
        """
        logger.warning(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! {self.student_state_json} \n\n\n")
        return Response(json_body=self.student_state_json)

    @XBlock.handler
    def send_scenario(self, request, suffix: str = '') -> Response:
        """
        Отправка сценария клиенту.
        
        Args:
            request: HTTP запрос
            suffix (str): Дополнительный суффикс
            
        Returns:
            Response: HTTP ответ со сценарием
        """
        scenarios = self.load_scenarios()
        scenario_name = force_str(self.scenario)
        context: Dict[str, str] = {}

        if scenario_name in scenarios:
            scenario_keys = self.load_scenarios('get')
            for key in scenario_keys:
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

        return Response(json_body=context, content_type='application/json')

    @XBlock.json_handler
    def studio_submit(self, data: Dict[str, Any], suffix: str = '') -> Dict[str, str]:
        """
        Обработка данных из студии.
        
        Args:
            data (Dict[str, Any]): Данные формы из студии
            suffix (str): Дополнительный суффикс
            
        Returns:
            Dict[str, str]: Результат операции
        """
        self.display_name = data.get('display_name', self.display_name)
        self.question = data.get('question', self.question)
        self.weight = int(data.get('weight', self.weight))
        self.correct_answer = data.get('correct_answer', self.correct_answer)
        self.sequence = data.get('sequence', self.sequence)
        self.scenario = data.get('scenario', self.scenario)
        self.max_attempts = int(data.get('max_attempts', self.max_attempts))
        self.student_view_template = data.get('student_view_template', self.student_view_template)
        return {'result': 'success'}

    @XBlock.json_handler
    def student_submit(self, data: str, suffix: str = '') -> Dict[str, Any]:
        """
        Обработка ответа студента.
        
        Args:
            data (str): JSON строка с ответом студента
            suffix (str): Дополнительный суффикс
            
        Returns:
            Dict[str, Any]: Результат проверки
        """
        try:
            student_json = json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f'[MultiEngineXBlock]: Ошибка парсинга ответа студента: {e}')
            return {'result': 'error', 'message': 'Invalid JSON format'}
            
        student_answer = student_json.get('answer', {})
        self.answer = data

        try:
            correct_json = json.loads(self.correct_answer) if self.correct_answer else {'answer': []}
        except json.JSONDecodeError:
            logger.warning('[MultiEngineXBlock]: Некорректный правильный ответ')
            correct_json = {'answer': []}

        correct_answer = correct_json.get('answer', [])
        settings = correct_json.get('settings', {'sequence': self.sequence})

        def multicheck(student_ans: Dict[str, Any], correct_ans: List[Any], check_settings: Dict[str, Any]) -> tuple:
            """
            Сравнение ответов студента с правильными ответами.
            
            Args:
                student_ans (Dict[str, Any]): Ответ студента
                correct_ans (List[Any]): Правильные ответы
                check_settings (Dict[str, Any]): Настройки проверки
                
            Returns:
                tuple: (баллы, коэффициент правильности)
            """
            # TODO: Реализовать логику сравнения ответов
            result = 0.0  # Заглушка - требуется реализация
            
            return int(round(result * self.weight)), result

        if has_attempts_left(self):
            try:
                correct, result = multicheck(student_answer, correct_answer, settings)
                self.points = correct
                self.attempts += 1

                self.runtime.publish(self, 'grade', {'value': correct, 'max_value': self.weight})
                return {
                    'result': 'success', 
                    'correct': correct, 
                    'weight': self.weight, 
                    'attempts': self.attempts
                }
            except Exception as e:
                logger.error(f'[MultiEngineXBlock]: Ошибка при проверке ответа: {e}')
                return {'result': 'error', 'message': 'Check failed'}
        else:
            return {'result': 'Max attempts exception!'}

    def past_due(self):
        """
        Проверка, прошла ли дата окончания задания.
        
        Метод учитывает возможный льготный период (grace period) при определении
        даты закрытия задания. Если льготный период определен, дата закрытия
        будет равна дате окончания + льготный период.
        
        Returns:
            bool: True если текущее время позже даты закрытия, иначе False
            
        Note:
            graceperiod и due определены в InheritanceMixin и используются
            автоматически в edX, но для unit тестов их нужно замокать.
        """
        due = get_extended_due_date(self)
        try:
            graceperiod = self.graceperiod
        except AttributeError:
            # graceperiod and due are defined in InheritanceMixin
            # It's used automatically in edX but the unit tests will need to mock it out
            graceperiod = None

        if graceperiod is not None and due:
            close_date = due + graceperiod
        else:
            close_date = due

        if close_date is not None:
            return utcnow() > close_date
        return False

    def is_course_staff(self):
        """
        Check if user is course staff.
        """
        if user_service := self.runtime.service(self, 'user'):
            return user_service.get_current_user().opt_attrs.get(ATTR_KEY_USER_IS_STAFF)
        return False

    
    def is_instructor(self):
        """
        Проверка статуса инструктора.
        
        Returns:
            bool: True если пользователь является инструктором
        """
        if user_service := self.runtime.service(self, 'user'):
            return user_service.get_current_user().opt_attrs.get(ATTR_KEY_USER_ROLE) == "instructor"
        return False


def has_attempts_left(instance: MultiEngineXBlock) -> bool:
    """
    Вернуть True, если студент может подать еще одну попытку.
    
    Примечание: В Open edX max_attempts==0 означает неограниченные попытки.
    
    Args:
        instance (MultiEngineXBlock): Экземпляр блока
        
    Returns:
        bool: True если можно ответить, False если достигнут лимит попыток
    """
    return instance.max_attempts == 0 or instance.attempts < instance.max_attempts


def _now() -> datetime.datetime:
    """
    Получение текущего времени в UTC.
    
    Returns:
        datetime.datetime: Текущее время
    """
    return datetime.datetime.now(pytz.utc)



def render_template(template_path: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Рендер шаблона с контекстом.
    
    Args:
        template_path (str): Путь к шаблону
        context (Optional[Dict[str, Any]]): Контекст для рендера
        
    Returns:
        str: Отрендеренный шаблон
    """
    if context is None:
        context = {}
    template_str = load_resource(template_path)
    if template_str:
        return Template(template_str).render(Context(context))
    return ''


def load_resource(resource_path: str) -> str:
    """
    Загрузка ресурса по пути.
    
    Args:
        resource_path (str): Путь к ресурсу
        
    Returns:
        str: Содержимое ресурса или пустая строка при ошибке
    """
    try:
        return resource_loader.load_unicode(resource_path)
    except EnvironmentError as e:
        logger.warning(f'[MultiEngineXBlock]: Не найден ресурс {resource_path}: {e}')
        return ''


def require(assertion: bool) -> None:
    """
    Проверка условия, выбрасывает PermissionDenied при невыполнении.
    
    Args:
        assertion (bool): Условие для проверки
        
    Raises:
        PermissionDenied: Если условие не выполнено
    """
    if not assertion:
        raise PermissionDenied()