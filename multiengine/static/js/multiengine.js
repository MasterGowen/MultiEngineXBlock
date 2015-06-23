/* Javascript for MultiEngineXBlock. */
function MultiEngineXBlock(runtime, element) {
    
    function success_func(result) {
    		//console.log("Количество баллов: " + result.correct/result.weight*100 + " ОТВЕТОВ: " + result.attempts);
            $('.attempts', element).text(result.attempts);
            $('.points', element).text(result.correct/result.weight*100);

            if (result.max_attempts <= result.attempts) {
                $('.send_button', element).html('<p><strong>Попытки исчерпаны</strong></p>')
            };
    }

    var handlerUrl = runtime.handlerUrl(element, 'student_submit');


    //TODO: Поиск плашки с сообщением, что ни один сценарий не поддерживается
    if ($(element).find('.update_scenarios_repo').length === 0) {
        var downloadUrl = runtime.handlerUrl(element, 'update_scenarios_repo');
    };

    //TODO: Кнопка обновления сценариев
    $(element).find('.update_scenarios_repo').bind('click', function() {
        $(element).find("#overlay").css("display", "block");
        var updateScenariosRepo = runtime.handlerUrl(element, 'update_scenarios_repo');
        $.post(updateScenariosRepo).done(function(response) {
            window.location.reload(false);
        });
    });


    $(element).find('.Check').bind('click', function() {
    var data = $(element).find('textarea[name=answer]').val();
    
            $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify(data),
            success: success_func 
        });
  });

}