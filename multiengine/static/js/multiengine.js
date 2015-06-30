/* Javascript for MultiEngineXBlock. */
function MultiEngineXBlock(runtime, element) {
    /**:SomeClass.prototype.someMethod( reqArg[, optArg1[, optArg2 ] ] )

        The description for ``someMethod``.
    */
    function success_func(result) {
        //console.log("Количество баллов: " + result.correct/result.weight*100 + " ОТВЕТОВ: " + result.attempts);
        $('.attempts', element).text(result.attempts);
        $('.points', element).text(result.correct / result.weight * 100);

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

    //Возврат сценариев
    scenarioURL = runtime.handlerUrl(element, 'send_scenario');


    function getScenario(scenarioURL) {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", scenarioURL, false);
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
    };

    var scenario = getScenario(scenarioURL);
    var scenarioJSON = JSON.parse(scenario);

    eval(scenarioJSON.javascriptStudent)

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