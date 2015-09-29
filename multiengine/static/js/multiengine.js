/* Javascript for MultiEngineXBlock. */

if(!MultiEngineXBlockState) var MultiEngineXBlockState = {};

function MultiEngineXBlock(runtime, element) {
    /**:SomeClass.prototype.someMethod( reqArg[, optArg1[, optArg2 ] ] )

        The description for ``someMethod``.
    */
    var elementDOM = element;

    // *******
    // MENGINE
    var mengine = {
        id: elementDOM.getAttribute('data-usage-id'),//.split(';')[5],
        // Объявление переменных
        studentAnswerJSON:{},
        studentStateJSON:'',
        // Функция обявляемая в сцкеарии и описывающая процесс формирования обекта правильных значенией
        genAnswerObj: function(){},
        genJSON: function(type, dict) {
            if (dict == undefined){
                dict = {};
            };
            var objectJSON = {};
            objectJSON[type.valueOf()] = dict;
            return JSON.stringify(JSON.stringify(objectJSON));
        },

        forEach: function(collection, action) {
            collection = collection || {};
            for (var i = 0; i < collection.length; i++)
                action(collection[i]);
        },
        // Функция геренации ID
        genID: function() {
            return 'id' + Math.random().toString(16).substr(2, 8).toUpperCase();
        },
        getData: function(requestURL) {
            if(requestURL){
                var xhr = new XMLHttpRequest();
                xhr.open("GET", requestURL, false);
                xhr.send(null);

                xhr.onload = function(e) {
                    if (xhr.readyState === 4) {
                        if (xhr.status === 200) {
                            console.log('Data loading ... OK!');
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
        }
    };
    // MENGINE
    // *******


    // **********************************
    // Функции для обратной совместимости

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
    //DEPRECATED
		return 'id' + Math.random().toString(16).substr(2, 8).toUpperCase();
	};
	//Функция формирования правиольного отвнета
	//Пример {name1:id1,name2:id2, name:{id3,id4}} передается в функцию
	function generationAnswerJSON(answer) {
        //DEPRECATED
		var answerJSON = {
			answer: {}
		};
		answerJSON.answer = answer;
		return JSON.stringify(answerJSON);
	};
	//TODO: Какой вид должен быть у результата выполнения функций
	function getValueFild(idField) {
		var parser = new DOMParser();
		var value = elementDOM.querySelector('#' + idField);
		value = parser.parseFromString(value.value || value.innerHTML, 'text/html');
		return value;
	};

	function setValueFild(idField, value) {
		elementDOM.querySelector('#' + idField).value = value;
	};

	function setBlockHtml(idBlock, contentHtml) {
		elementDOM.querySelector('#' + idBlock).innerHTML = contentHtml;
	};


    // Функции для обратной совместимости
    // **********************************
    function success_func(result) {
        //console.log("Количество баллов: " + result.correct/result.weight*100 + " ОТВЕТОВ: " + result.attempts);
        $('.attempts', element).text(result.attempts);
        $(element).find('.weight').html('Набрано баллов: <span class="points"></span>');
        $('.points', element).text(result.correct);

        if (result.max_attempts && result.max_attempts <= result.attempts) {
            $('.send_button', element).html('<p><strong>Попытки исчерпаны</strong></p>')
        };
    };


    function success_save(result){
    	var span = document.createElement('span');
    	span.innerHTML = 'Сохранено';
    	span.classList.add('saved');
        element.getElementsByClassName('action')[0].appendChild(span);
        setTimeout(function(){element.getElementsByClassName('saved')[0].parentNode.removeChild(element.getElementsByClassName('saved')[0])}, 1000);        
    };
    
    //TODO: Поиск плашки с сообщением, что ни один сценарий не поддерживается
    if ($(element).find('.update_scenarios_repo')) {
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
    var scenarioURL = runtime.handlerUrl(element, 'send_scenario');
    var scenario = mengine.getData(scenarioURL);
    var scenarioJSON = JSON.parse(scenario);

    //Получение и передача CSS в шаблон
    setBlockHtml('scenarioStyleStudent', scenarioJSON.cssStudent);

    //Получение суденческого решения
    var getStudentStateURL = runtime.handlerUrl(element,'get_student_state');
    var studentState = mengine.getData(getStudentStateURL);
    
    // Сохранение состояния студета в mengine
    mengine.studentStateJSON = studentState;
   

    

    //Save student state
    // Сохранение ответа студента
    var handlerUrl = runtime.handlerUrl(element, 'student_submit');

    var saveStudentStateURL = runtime.handlerUrl(element,'save_student_state');

    $(element).find('.Save').bind('click', function() {
        $.ajax({
            type: "POST",
            url: saveStudentStateURL,
            data: mengine.genJSON('state', mengine.genAnswerObj()),
            success: success_save
        });
    });

    $(element).find('.Check').bind('click', function() {
                $.ajax({
            type: "POST",
            url: handlerUrl,
            data: mengine.genJSON('answer', mengine.genAnswerObj()),
            success: success_func
        });

        $.ajax({
            type: "POST",
            url: saveStudentStateURL,
            data: mengine.genJSON('state', mengine.genAnswerObj()),
            success: success_save
        });

    });

    // Сценарий
    eval(scenarioJSON.javascriptStudent)

    MultiEngineXBlockState[mengine.id.valueOf()] = function(){
        console.log(mengine.studentStateJSON);
    };
}