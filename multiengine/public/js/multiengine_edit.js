function MultiEngineXBlockEdit(runtime, element) {

  var elementDOM = element[0];

  if ($(element).find('.scenario_alert').length === 0) {
    var downloadUrl = runtime.handlerUrl(element, 'download_scenario');
  };

  function getScenario(downloadUrl){
  var xhr = new XMLHttpRequest();
  xhr.open("GET", downloadUrl, false);
  xhr.send(null);
  
  xhr.onload = function(e) {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        console.error(xhr.statusText);
      } else {
        console.error(xhr.statusText);
      }
    }
  };
  xhr.onerror = function(e) {
    console.error(xhr.statusText);
  };
  
  return xhr.responseText;
  
}



  // var script = document.createElement('script');
  // script.onload = function() {
  //   alert("Script loaded and ready");
  // };
  // script.src = downloadUrl;
  // document.getElementsByTagName('head')[0].appendChild(script);


  function setValueFild(idField, value) {
    elementDOM.querySelector('#' + idField).value = value;
  };
  setValueFild('student_view_template', getScenario(downloadUrl));

  $(element).find('.update_scenarios_repo').bind('click', function() {
    var updateScenariosRepo = runtime.handlerUrl(element, 'update_scenarios_repo');
    $.post(updateScenariosRepo).done(function(response) {
      window.location.reload(false);
    });
  });


  //HTMLElement(element).getElementById('#lea').onclick = function(){console.log('EHHF!!')}; 
  // var editor = CodeMirror.fromTextArea(document.getElementById('student_view_template'), {
  //   mode: "text/html",
  //   tabMode: "indent",
  //   lineNumbers: true
  // });

  $(element).find('.save-button').bind('click', function() {
    var handlerUrl = runtime.handlerUrl(element, 'studio_submit'),
      data = {
        display_name: $(element).find('input[name=display_name]').val(),
        question: $(element).find('textarea[id=question-area]').val(),
        weight: $(element).find('input[name=weight]').val(),
        correct_answer: $(element).find('input[id=correct_answer]').val(),
        sequence: document.getElementById("sequence").checked,
        scenario: $(element).find('select[name=scenario]').val(),
        max_attempts: $(element).find('input[name=max_attempts]').val(),
        student_view_json: $(element).find('input[name=student_view_json]').val(),
        student_view_template: editor.getValue(),
      };

    $.post(handlerUrl, JSON.stringify(data)).done(function(response) {
      window.location.reload(false);
    });
  });
  $(element).find('.cancel-button').bind('click', function() {
    runtime.notify('cancel', {});
  });

}