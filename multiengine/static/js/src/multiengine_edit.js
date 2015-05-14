function MultiEngineXBlockEdit(runtime, element) {

  $(element).find('.save-button').bind('click', function() {
    var handlerUrl = runtime.handlerUrl(element, 'studio_submit'),
        data = {
            display_name: $(element).find('input[name=display_name]').val(),
            question: $(element).find('textarea[id=question-area]').val(),
            weight: $(element).find('input[name=weight]').val(),
            correct_answer: $(element).find('textarea[id=correct_answer]').val(),
            sequence: document.getElementById("sequence").checked,
            scenario:$(element).find('input[name=scenario]').val(),
            max_attempts:$(element).find('input[name=max_attempts]').val(),
            student_view_json:$(element).find('textarea[name=student_view_json]').val(),
            student_view_template:$(element).find('textarea[name=student_view_template]').val(),
                };

            $.post(handlerUrl, JSON.stringify(data)).done(function(response) {
      window.location.reload(false);
    });
  });

  $(element).find('.cancel-button').bind('click', function() {
    runtime.notify('cancel', {});
  });
}
