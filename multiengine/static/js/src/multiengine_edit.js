function MultiEngineXBlockEdit(runtime, element) {
  $(element).find('.save-button').bind('click', function() {
    var handlerUrl = runtime.handlerUrl(element, 'studio_submit');
    var data = {
      display_name: $(element).find('input[name=display_name]').val(),
      question: $(element).find('input[name=question]').val(),
    };
            $.post(handlerUrl, JSON.stringify(data)).done(function(response) {
      window.location.reload(false);
    });
  });

  $(element).find('.cancel-button').bind('click', function() {
    runtime.notify('cancel', {});
  });

  var area = document.getElementById('question-area');
    if (area.addEventListener) {
        area.addEventListener('input', function() {
            document.getElementById('question').value = area.value;
        }, false);
    } else if (area.attachEvent) {
        area.attachEvent('onpropertychange', function() {
        document.getElementById('question').value = area.value;
        });
    }
}
