# -*- coding: utf-8 -*-
"""TO-DO: Write a description of what this XBlock is."""

import datetime
import pkg_resources
import pytz
import json

from django.core.exceptions import PermissionDenied
from django.core.files import File
from django.core.files.storage import default_storage
from django.conf import settings
from django.template import Context, Template
from django.utils.encoding import smart_text


from xblock.core import XBlock
from xblock.fields import Scope, Integer, String, Float, JSONField,Boolean
from xblock.fragment import Fragment

from xmodule.util.duedate import get_extended_due_date

class MultiEngineXBlock(XBlock):

#content
    display_name = String(
        display_name="Имя XBlock",
        help="Тут будет имя XBlock",
        default='MultiEngine',
        scope=Scope.content
        )
    question = String(
        display_name="Вопрос",
        help="Тут вопрос",
        default='Are you ready?',
        scope=Scope.content
        )

    correct_answer = JSONField(
        display_name="Правильный ответ",
        help="Тут правильный ответ",
        default={},
        scope=Scope.content
        )

#settings
    weight = Integer(
        display_name="Максимальное количество баллов",
        help=("Тут будет максимальное количество баллов"),
        default=100,
        scope=Scope.settings
        )

    grade_steps = Integer(
        display_name=u"Шаг оценивания",
        help=("Тут будет текст"),
        default=0,
        scope=Scope.settings
        )
    scenario = String(
        scope=Scope.settings
        )
    max_attempts = Integer(
        display_name = u"Максимальное количество попыток",
        help = ("Тут будет текст"),
        default=0,
        scope = Scope.settings
        )

#user_state
    points = Integer(
        display_name="Количество баллов студента",
        help=("Тут будет количество баллов студента"),
        default=None,
        scope=Scope.user_state
        )

    answer = JSONField(
        display_name="Ответ пользователя",
        help="Тут ответ пользователя",
        default={},
        scope=Scope.user_state
        )
    attempts = Integer(
        display_name = "Количество сделанных попыток",
        help = "Тут будет текст",
        default=0,
        scope = Scope.user_state
        )

    student_view_json = String(
        display_name = u"student_view_json",
        help = ("Тут будет текст"),
        scope = Scope.content
        )

    student_view_template = String(
        display_name = u"student_view_template",
        help = ("Тут будет текст"),
        default='',
        scope = Scope.content
        )

    sequence = Boolean(
        default=False
        )

    """answer_opportunity = Boolean(
        default=True
        )"""

    has_score = True
    
    send_button = ''

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # TO-DO: change this view to display your data your own way.
    def student_view(self, context=None):
        """
        The primary view of the MultiEngineXBlock, shown to students
        when viewing courses.
        """

        #self.student_view_template = r'<script>var element_json =' + str(self.student_view_json) + r'</script>'

        context = {
            "display_name": self.display_name,
            "weight": self.weight,
            "question": self.question,
            "correct_answer": self.correct_answer,
            "answer": self.answer,
            "max_attempts": self.max_attempts,
            "attempts": self.attempts,
            "student_view_json": self.student_view_json,
            "student_view_template": self.student_view_template,
        }

        if self.past_due():
            context["past_due"] = True

        if self.answer != '{}':
            context["points"] = self.points

        if answer_opportunity(self):
            context["answer_opportunity"] = True

        fragment = Fragment()
        fragment.add_content(
            render_template(
                'static/html/multiengine.html',
                context
            )
        )
        fragment.add_css(_resource("static/css/multiengine.css"))
        fragment.add_javascript(_resource("static/js/src/multiengine.js"))
        fragment.initialize_js('MultiEngineXBlock')
        
        return fragment

    def studio_view(self, context):

        context = {
            "display_name": self.display_name,
            "weight": self.weight,
            "question": self.question,
            "correct_answer":self.correct_answer,
            "answer":self.answer,
            "sequence": self.sequence,
            "scenario": self.scenario,
            "max_attempts":self.max_attempts,
            "student_view_json": self.student_view_json,
            "student_view_template": self.student_view_template,
        }

        fragment = Fragment()
        fragment.add_content(
            render_template(
                'static/html/multiengine_edit.html',
                context
            )
        )
        fragment.add_css(_resource("static/css/multiengine.css"))
        fragment.add_javascript(_resource("static/js/src/multiengine_edit.js"))
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
            def _compare_answers_not_sequenced(student_answer, correct_answer, checked=0, correct=0):
                """
                Вычисляет долю выполненных заданий без учета
                последовательности элементов в области
                """
                for key in correct_answer:
                    for value in correct_answer[key]:
                        if value in student_answer[key]:
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
                for key in correct_answer:
                    student_answer_true = []
                    if len(correct_answer) > 1:
                        for answer_item in student_answer[key]:
                            if answer_item in correct_answer[key]:
                                student_answer_true.append(answer_item)
                                checked += 1
                                correct += 1
                            else:
                                checked += 1
                    elif len(correct_answer) == 1:
                        student_answer_true = student_answer[key]
                    else:
                        pass # TODO exception

                    if len(student_answer_true) == len(correct_answer[key]):
                        try:
                            answer_condition = ''.join(student_answer_true) == ''.join(correct_answer[key])
                        except:
                            answer_condition = str(student_answer_true) == str(correct_answer[key])

                        if answer_condition:
                            checked += len(correct_answer[key])
                            correct += len(correct_answer[key])
                        else:
                            checked += len(correct_answer[key])
                    else:
                        checked += len(correct_answer[key])

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
            correct = multicheck(student_answer, correct_answer, settings) #={'sequence': True})
            self.attempts = self.attempts + 1
            return {
            		'result': 'success',
            		'correct': correct,
            		'weight': self.weight,
            		'attempts':self.attempts,
            		'max_attempts':self.max_attempts,
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

def answer_opportunity(self):
    if( self.max_attempts <= self.attempts):
        return False
    else:
    	return True
        
def _now():
    """
    Получение текущих даты и премени 
    """
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

def _resource(path):  # pragma: NO COVER
    """
    Handy helper for getting resources from our kit.
    """
    data = pkg_resources.resource_string(__name__, path)
    return data.decode("utf8")

def render_template(template_path, context=None):  # pragma: NO COVER
    """
    Evaluate a template by resource path, applying the provided context.
    """
    if context is None:
        context = {}

    template_str = load_resource(template_path)
    template = Template(template_str)
    return template.render(Context(context))

def load_resource(resource_path):  # pragma: NO COVER
    """
    Gets the content of a resource
    """
    resource_content = pkg_resources.resource_string(__name__, resource_path)
    return smart_text(resource_content)