# -*- coding: utf-8 -*-
"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources

from xblock.core import XBlock
from xblock.fields import Scope, Integer, String, Float, JSONField
from xblock.fragment import Fragment


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
        default='',
        scope=Scope.content
        )
    question = String(
        display_name="Вопрос",
        help="Тут вопрос",
        default='',
        scope=Scope.content
        )

    correct_answer = JSONField(
        display_name="Правильный ответ",
        help="Тут правильный ответ",
        default={},
        scope=Scope.content
        )

#settings
    max_points = Integer(
        display_name="Максимальное количество баллов",
        help=(u"Тута будет максимальное количество баллов"),
        default=0,
        scope=Scope.settings
        )

    grade_steps = Integer(
        display_name=u"Шаг оценивания",
        help=(u"Тута будет текст"),
        default=0,
        scope=Scope.settings
        )

#user_state
    points = Integer(
        display_name="Количество баллов студента",
        help=(u"Тута будет количество баллов студента"),
        default=None,
        scope=Scope.user_state
        )

    answer = JSONField(
        display_name="Ответ пользователя",
        help="Тут ответ пользователя",
        default={},
        scope=Scope.user_state
        )

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
                frag.initialize_js('audioplayer')

                html_str = pkg_resources.resource_string(__name__, "static/html/multiengine_edit.html")
                display_name = self.display_name or 'MultiEngine'
                question = self.question or 'Are you ready?'
                max_points = self.max_points or 100

                frag = Fragment(unicode(html_str).format(
                    display_name=display_name,
                    question=question,
                    max_points=max_points
                ))

                js_str = pkg_resources.resource_string(__name__, "static/js/src/multiengine.js")
                frag.add_javascript(unicode(js_str))
                frag.initialize_js('MultiEngineXBlock')
                return frag

    # TO-DO: change this handler to perform your own actions.  You may need more
    # than one handler, or you may not need any handlers at all.
    @XBlock.json_handler
    def increment_count(self, data, suffix=''):
        """
        An example handler, which increments the data.
        """
        # Just to show data coming in...
        assert data['hello'] == 'world'

        self.count += 1
        return {"count": self.count}

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
