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


from xblock.core import XBlock
from xblock.fields import Scope, Integer, String, Float, JSONField,Boolean
from xblock.fragment import Fragment

from xmodule.util.duedate import get_extended_due_date

class MultiEngineXBlock(XBlock):
	"""
	TO-DO: document what your XBlock does.
	"""

	# Fields are defined on the class.  You can access them in your code as
	# self.<fieldname>.

	# TO-DO: delete count, and define your own fields.


	#https://github.com/mitodl/edx-sga/blob/master/edx_sga/sga.py

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
		default=0,
		scope=Scope.settings
		)

	grade_steps = Integer(
		display_name=u"Шаг оценивания",
		help=("Тута будет текст"),
		default=0,
		scope=Scope.settings
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

	answer_opportunity = Boolean(
		default = True
		)
	
	sequence = Boolean(
		default=False
		)
	has_score = True
	

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

		html = self.resource_string("static/html/multiengine.html")
		frag = Fragment(html.format(self=self))
		frag.add_css(self.resource_string("static/css/multiengine.css"))
		frag.add_javascript(self.resource_string("static/js/src/multiengine.js"))
		frag.initialize_js('MultiEngineXBlock')
		return frag

	def studio_view(self, context):
		html = self.resource_string("static/html/multiengine.html")
		frag = Fragment(html.format(self=self))
		css_str = pkg_resources.resource_string(__name__, "static/css/multiengine.css")
		frag.add_css(unicode(css_str))
		js_str = pkg_resources.resource_string(__name__, "static/js/src/multiengine.js")
		frag.add_javascript(unicode(js_str))
		frag.initialize_js('MultiEngineXBlock')

		html_str = pkg_resources.resource_string(__name__, "static/html/multiengine_edit.html")
		display_name = self.display_name or 'MultiEngine'
		question = self.question or 'Are you ready?'
		weight = self.weight or 100
		#correct_answer = self.correct_answer
		sequence=self.sequence

		correct_answer = json.loads(self.correct_answer)

		if sequence:
			sequence_view = 'checked="checked"'
		else:
			sequence_view = ''

		correct_answer = json.dumps(correct_answer)

		frag = Fragment(unicode(html_str).format(
			display_name=display_name,
			question=question,
			weight=weight,
			correct_answer=correct_answer,
			sequence=sequence_view
		))

		js_str = pkg_resources.resource_string(__name__, "static/js/src/multiengine_edit.js")
		frag.add_javascript(unicode(js_str))
		frag.initialize_js('MultiEngineXBlockEdit')
		return frag
	def student_state(self):

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
		return {'result': 'success'}

	@XBlock.json_handler
	def student_submit(self, data, suffix=''):
		#str_answer = data.get('answer')
		#self.answer = str(data.get('answer'))

		student_json = json.loads(data) 

		student_answer = student_json["answer"]
		self.answer = data

		correct_json = json.loads(self.correct_answer)
		correct_answer = correct_json["answer"]

		settings = correct_json["settings"]
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

		correct = multicheck(student_answer, correct_answer, settings) #={'sequence': True})
		
		answer_opportunity = str(self.past_due())

		return {'result': 'success', 'correct': correct, 'weight': self.weight, 'test': answer_opportunity}
	
	def past_due(self):
			due = get_extended_due_date(self)
			if due is not None:
				if(_now() > due):
					return False
			return True
		
def _now():
	"""
	Получение текущих даты и премени 
	"""
	return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
