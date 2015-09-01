/* Javascript for MultiEngineXBlock. */
function MultiEngineXBlock(runtime, element) {
    /**:SomeClass.prototype.someMethod( reqArg[, optArg1[, optArg2 ] ] )

        The description for ``someMethod``.
    */
    function forEachInCollection(collection, action) {
		collection = collection || {};
		for (var i = 0; i < collection.length; i++)
			action(collection[i]);
	};

	//Функция формирует список из детей переданнго в функцию элементов
	function childList(value) {
		var childList = [];
		var value = value.children || value.childNodes;
		/*if(!val.length){
		  console.log('Attention!: '+ typeof(val) + ' has no children')
		  return;
		};*/
		for (var i = 0; i < value.length; i++) {
			if (value[i].nodeType == 1) {
				childList.push(value[i])
			};
		};
		return childList;
	};
	//Функция генерации ID
	function generationID() {
		return 'id' + Math.random().toString(16).substr(2, 8).toUpperCase();
	};
	//Функция формирования правиольного отвнета
	//Пример {name1:id1,name2:id2, name:{id3,id4}} передается в функцию
	function generationAnswerJSON(answer) {
		var answerJSON = {
			answer: {}
		};
		answerJSON.answer = answer;
		return JSON.stringify(answerJSON);
	};

	//TODO: Какой вид должен быть у результата выполнения функций
	function getValueFild(idField) {
		var parser = new DOMParser();
		var value = element.querySelector('#' + idField);
		value = parser.parseFromString(value.value || value.innerHTML, 'text/html');
		return value;
	};

	function setValueFild(idField, value) {
		element.querySelector('#' + idField).value = value;
	};

	function setBlockHtml(idBlock, contentHtml) {
		element.querySelector('#' + idBlock).innerHTML = contentHtml;
	};
    function success_func(result) {
        $('.attempts', element).text(result.attempts);
        $(element).find('.weight').html('Набрано баллов: <span class="points"></span>');
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
                    console.log('Scenario loading ... OK!');
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

    eval(scenarioJSON.javascriptStudent);
    javascriptStudent(element);


    //Save student state

    var saveStudentStateURL = runtime.handlerUrl(element,'save_student_state');
    function saveStudentState(saveStudentStateURL){
        
        };
    
    setBlockHtml('scenarioStyleStudent', scenarioJSON.cssStudent);

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