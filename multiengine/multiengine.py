# -*- coding: utf-8 -*-
"""XBlock для проверки json-объектов, сформированных по определенным правилам.
Поддерживает различные типы заданий через систему сценариев."""

import datetime
import pkg_resources
import pytz
import json
import os
import re
from path import path
import git
import shutil

from django.template import Context, Template
from django.utils.encoding import smart_text
from django.conf import settings
from django.core.files.storage import default_storage


from xblock.core import XBlock
from xblock.fields import Scope, Integer, String, JSONField, Boolean
from xblock.fragment import Fragment

from xmodule.util.duedate import get_extended_due_date

from webob.response import Response
from webob.exc import HTTPNotFound

from settings import GIT_REPO_URL


class MultiEngineXBlock(XBlock):

    # settings
    display_name = String(
        display_name="Название",
        help="Название задания, которое увидят студенты.",
        default='MultiEngine',
        scope=Scope.settings
    )
    question = String(
        display_name="Вопрос",
        help="Текст задания.",
        default="Вы готовы?",
        scope=Scope.settings
    )

    correct_answer = JSONField(
        display_name="Правильный ответ",
        help="Скрытое поле для правильного ответа в формате json.",
        default={},
        scope=Scope.settings
    )

    weight = Integer(
        display_name="Максимальное количество баллов",
        help=("Максимальное количество баллов",
              "которое может получить студент."),
        default=100,
        scope=Scope.settings
    )

    grade_steps = Integer(
        display_name=u"Шаг оценивания",
        help=("Количество диапазонов оценивания"),
        default=0,
        scope=Scope.settings
    )
    scenario = String(
        display_name=u"Сценарий",
        help=("Выберите один из сценариев отображения задания."),
        scope=Scope.settings,
        default=None,
    )
    max_attempts = Integer(
        display_name=u"Максимальное количество попыток",
        help=(""),
        default=0,
        scope = Scope.settings
    )

    # user_state
    points = Integer(
        display_name="Количество баллов студента",
        default=None,
        scope=Scope.user_state
    )

    answer = JSONField(
        display_name="Ответ пользователя",
        default={"answer": {}},
        scope=Scope.user_state
    )

    attempts = Integer(
        display_name="Количество сделанных попыток",
        default=0,
        scope=Scope.user_state
    )

    student_view_json = String(
        display_name=u"Состояние сценария, видимое студенту",
        scope = Scope.settings
    )

    student_view_template = String(
        display_name=u"Шаблон сценария",
        default='',
        scope = Scope.settings
    )

    sequence = Boolean(
        display_name=u"Учитывать последовательность выбранных вариантов?",
        help=(u"Работает не для всех сценариев."),
        default=False,
        scope=Scope.settings
    )

    has_score = True

    MULTIENGINE_ROOT = path(__file__).abspath().dirname().dirname() + '/multiengine'
    SCENARIOS_ROOT = MULTIENGINE_ROOT + '/public/scenarios/'

    def is_repo(self):
            repo_exists = False
            if os.path.exists(self.SCENARIOS_ROOT) and os.path.isdir(self.SCENARIOS_ROOT):
                for file_item in os.listdir(self.SCENARIOS_ROOT):
                    if file_item and file_item == '.git':
                        repo_exists = True
                    elif not file_item:
                        pass
                    else:
                        pass
            return repo_exists
        
        
    def clean_repo_path(self, path=SCENARIOS_ROOT):
        shutil.rmtree(path, ignore_errors=True)
    
    def update_local_repo(self):
        LATEST = False
        scenarios_repo = git.Repo(self.SCENARIOS_ROOT)
        scenarios_repo_remote = git.Remote(
            scenarios_repo,
            'master')
        info = scenarios_repo_remote.fetch()[0]
        remote_commit = info.commit
        if scenarios_repo.commit().hexsha == remote_commit.hexsha:
            LATEST = True
    
        while remote_commit.hexsha != scenarios_repo.commit().hexsha:
            remote_commit = remote_commit.parents[0]
        return LATEST
    
    
    def clone_repo(self):
        scenarios_repo = git.Repo.clone_from(
            GIT_REPO_URL,
            self.SCENARIOS_ROOT
        )
        scenarios_repo = git.Repo(self.SCENARIOS_ROOT)
        LATEST = True
        return LATEST
    
    def load_scenarios(self):
        scenarios = {}
        if os.path.exists(self.SCENARIOS_ROOT) and os.path.isdir(self.SCENARIOS_ROOT):
            for file in os.listdir(self.SCENARIOS_ROOT):
                if file.endswith(".js"):
                    def _get_name(file):
                        read_file = open(self.SCENARIOS_ROOT + file)
                        name = read_file.readline()
                        name = re.sub('/*', '', name)
                        return name
                    scenarios[os.path.splitext(file)[0]] = _get_name(file)
            
        return scenarios

    def get_scenario_content(self, scenario):
        try:
            scenario_file = open(self.SCENARIOS_ROOT + scenario + '.js', 'r')

            with scenario_file as jsfile:
               scenario_content=jsfile.read()
        except:
            scenario_content = 'alert("Scenario file not found!");'
        return scenario_content

    send_button = ''

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def load_resources(self, js_urls, css_urls, fragment):
        '''
        '''
        for js_url in js_urls:

            if js_url.startswith('public/'):
                fragment.add_javascript_url(self.runtime.local_resource_url(self, js_url))
            elif js_url.startswith('static/'):
                fragment.add_javascript(_resource(js_url))
            else:
                pass

        for css_url in css_urls:

            if css_url.startswith('public/'):
                fragment.add_css_url(self.runtime.local_resource_url(self, css_url))
            elif css_url.startswith('static/'):
                fragment.add_css(_resource(css_url))
            else:
                pass

    # TO-DO: change this view to display your data your own way.
    def student_view(self, context=None):
        """
        The primary view of the MultiEngineXBlock, shown to students
        when viewing courses.
        """
        scenarios = self.load_scenarios()

        context = {
            "display_name": self.display_name,
            "weight": self.weight,
            "question": self.question,
            "correct_answer": self.correct_answer,
            "answer": self.answer,
            "attempts": self.attempts,
            "student_view_json": self.student_view_json,
            "student_view_template": self.student_view_template,
            "scenario": self.scenario,
            "scenarios": scenarios,
        }

        if self.max_attempts != 0:
            context["max_attempts"] = self.max_attempts

        if self.past_due():
            context["past_due"] = True

        if self.answer != '{}':
            context["points"] = self.points

        if answer_opportunity(self):
            context["answer_opportunity"] = True

        if self.is_course_staff() is True or self.is_instructor() is True:
            context['is_course_staff'] = True

        fragment = Fragment()
        fragment.add_content(
            render_template(
                'static/html/multiengine.html',
                context
            )
        )

        js_urls = (
            'static/js/multiengine.js',
        )

        css_urls = (
            'static/css/multiengine.css',
        )

        self.load_resources(js_urls, css_urls, fragment)

        fragment.initialize_js('MultiEngineXBlock')
        return fragment


    def studio_view(self, context):

        scenarios = self.load_scenarios()

        context = {
            "display_name": self.display_name,
            "weight": self.weight,
            "question": self.question,
            "correct_answer": self.correct_answer,
            "answer": self.answer,
            "sequence": self.sequence,
            "scenario": self.scenario,
            "max_attempts": self.max_attempts,
            "student_view_json": self.student_view_json,
            "student_view_template": self.student_view_template,

            "scenarios": scenarios,
        }

        if self.scenario:
            scenario_content = self.get_scenario_content(self.scenario)
            context["scenario_content"] = scenario_content

        fragment = Fragment()
        fragment.add_content(
            render_template(
                'static/html/multiengine_edit.html',
                context
            )
        )

        js_urls = (
            "static/js/multiengine_edit.js",
        )

        css_urls = (
            'static/css/multiengine.css',
        )

        self.load_resources(js_urls, css_urls, fragment)
        fragment.initialize_js('MultiEngineXBlockEdit')

        try:
            correct_answer = json.loads(self.correct_answer)
        except:
            correct_answer = json.loads('{}')

        correct_answer = json.dumps(correct_answer)

        context["correct_answer"] = correct_answer

        return fragment

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("MultiEngineXBlock",
             """<vertical_demo>
                <multiengine/>
                <multiengine/>
                <multiengine/>
                </vertical_demo>
             """),
        ]

    def download(self, path, filename):
        """
        Return a file from storage and return in a Response.
        """

        res = Response(content_type='text/javascript', app_iter=None)
        try:
            res.body = open(path + filename, 'r').read()
        except:
            res.body = 'alert("Scenario file not found!");'
        return res

    @XBlock.handler
    def update_scenarios_repo(self, request, suffix=''):
        """
        Обновление репозитория сценариев из внешнего git-репозитория
        """
        require(self.is_course_staff())
        if self.is_repo():
            try:
                self.update_local_repo()
            except:
                self.clean_repo_path()
                self.clone_repo()
        elif not self.is_repo():
            self.clone_repo()

        response = Response(body='{"result": "success"}', content_type='application/json' )
        return response

    @XBlock.handler
    def download_scenario(self, request, suffix=''):
        """
        Fetch student assignment from storage and return it.
        """
        if self.scenario:
            return self.download(self.SCENARIOS_ROOT, self.scenario + '.js')

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        self.display_name = data.get('display_name')
        self.question = data.get('question')
        self.weight = data.get('weight')
        self.correct_answer = data.get('correct_answer')
        self.sequence = data.get('sequence')
        self.scenario = data.get('scenario')
        self.max_attempts = data.get('max_attempts')
        self.student_view_json = data.get('student_view_json')
        self.student_view_template = data.get('student_view_template')
        return {'result': 'success'}

    @XBlock.json_handler
    def student_submit(self, data, suffix=''):

        student_json = json.loads(data)

        student_answer = student_json["answer"]
        self.answer = data

        correct_json = json.loads(self.correct_answer)
        correct_answer = correct_json["answer"]

        try:
            settings = correct_json["settings"]
        except:
            settings = {}

        settings['sequence'] = self.sequence

        def multicheck(student_answer, correct_answer, settings):
            """
            Сравнивает 2 словаря вида:
                {"name1": ["param1", "param2"], "name2": ["param3", "param4"]}
            с произвольным количеством ключей,

            возвращает долю совпавших значений
            """

            keywords = ('or', 'and', 'not')

            def max_length(lst):
                length = 0
                for element in lst:
                    if len(element) > length:
                        length = len(element)
                return length

            def _compare_answers_not_sequenced(student_answer, correct_answer, checked=0, correct=0):
                """
                Вычисляет долю выполненных заданий без учета
                последовательности элементов в области
                """
                for key in correct_answer:
                    for value in correct_answer[key]:
                        if value in keywords:
                            keyword = value
                            correct_values = correct_answer[key][keyword]
                            for correct_value in correct_values:
                                if len(set(correct_value) - set(student_answer[key])) == 0:
                                    with_keyword = True
                                    break
                            if with_keyword:
                                checked += len(student_answer[key])
                                correct += len(student_answer[key])
                            else:
                                checked += len(student_answer[key])

                        elif value in student_answer[key]:
                            checked += 1
                            correct += 1
                        else:
                            checked += 1
                return correct / float(checked)

            def _compare_answers_sequenced(student_answer, correct_answer, checked=0, correct=0):
                """
                Вычисляет долю выполненных заданий с учетом
                последовательности элементов в области
                """
                answer_condition = False

                for key in correct_answer:
                    student_answer_true = []

                    if not isinstance(correct_answer[key], dict):
                        for answer_item in student_answer[key]:
                            if answer_item in correct_answer[key]:
                                student_answer_true.append(answer_item)

                        try:
                            answer_condition = ''.join(student_answer_true) == ''.join(correct_answer[key])
                        except:
                            answer_condition = str(student_answer_true) == str(correct_answer[key])

                        if answer_condition:
                            correct += len(correct_answer[key])
                        checked += len(correct_answer[key])

                    else:
                        for keyword in keywords:
                            if keyword in correct_answer[key].keys():
                                correct_values = correct_answer[key][keyword]

                                for correct_value in correct_values:
                                    try:
                                        answer_condition = ''.join(student_answer[key]) == ''.join(correct_value)
                                    except:
                                        answer_condition = str(student_answer[key]) == str(correct_value)
                                    if answer_condition:
                                        break

                                checked += max_length(correct_values)

                                if answer_condition:
                                    correct += len(student_answer[key])

                return correct / float(checked)

            def _result_postproduction(result):  # , settings['postproduction_rule']=None):
                result = int(round(result * self.weight))
                self.points = result
                self.runtime.publish(self, 'grade', {
                    'value': self.points,
                    'max_value': self.weight,
                })
                return result

            if settings['sequence'] is True:
                result = _compare_answers_sequenced(student_answer, correct_answer)
            elif settings['sequence'] is False:
                result = _compare_answers_not_sequenced(student_answer, correct_answer)
            else:
                pass

            return _result_postproduction(result)

        if answer_opportunity(self):
            correct = multicheck(student_answer, correct_answer, settings)  # ={'sequence': True})
            self.attempts = self.attempts + 1
            return {'result': 'success',
                    'correct': correct,
                    'weight': self.weight,
                    'attempts': self.attempts,
                    'max_attempts': self.max_attempts,
                    }
        else:
            return('Max attempts exception!')

    def past_due(self):
            """
            Return whether due date has passed.
            """
            due = get_extended_due_date(self)
            if due is not None:
                if(_now() > due):
                    return False
            return True

    def is_course_staff(self):
        """
         Check if user is course staff.
        """
        return getattr(self.xmodule_runtime, 'user_is_staff', False)

    def is_instructor(self):
        """
        Check if user role is instructor.
        """
        return self.xmodule_runtime.get_user_role() == 'instructor'


def answer_opportunity(self):
    """
    Возможность ответа (если количество сделанное попыток меньше заданного)
    """
    if(self.max_attempts <= self.attempts and self.max_attempts != 0):
        return False
    else:
        return True


def _now():
    """
    Получение текущих даты и времени
    """
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def _resource(path):  # pragma: NO COVER
    """
    Handy helper for getting resources from our kit.
    """
    data = pkg_resources.resource_string(__name__, path)
    return data.decode("utf8")


def render_template(template_path, context=None):
    """
    Evaluate a template by resource path, applying the provided context.
    """
    if context is None:
        context = {}

    template_str = load_resource(template_path)
    template = Template(template_str)
    return template.render(Context(context))


def load_resource(resource_path):
    """
    Gets the content of a resource
    """
    try:
        resource_content = pkg_resources.resource_string(__name__, resource_path)
        return smart_text(resource_content)
    except EnvironmentError:
        pass

def require(assertion):
    """
    Raises PermissionDenied if assertion is not true.
    """
    if not assertion:
        raise PermissionDenied
