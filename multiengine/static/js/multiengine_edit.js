function MultiEngineXBlockEdit(runtime, element) {
	// Перенос DOM структуры блока в отдельную переменную
	// HELP
	// Запросы доступные для работы с переменноой elementDOM
	// querySelector  --- elementNodeList
	// querySelectorAll --- NodeList
	// getElementByTegName --- HTMLCollection
	// getElementByClassName --- HTMLCollection

	var elementDOM = element[0];

	// Функция пробегания по элементам коллекции
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

	//Функции которые надо описать
	function generationTamplate() {};
	function conversionToRaw() {};
	function conversionInRaw() {};
	function actionsView(windowView, scenario) {};

	//jsDesign 
	//start
	// Функция которая должна отвечать за работу Вкладок RAW / View и следить за событием конвертирования (false or true)
	function toggleTabs() {};


	// Окно редактирование RAW Code
	var editor = CodeMirror.fromTextArea(elementDOM.querySelector('#student_view_template'), {
		mode: "text/html",
		tabMode: "indent",
		lineNumbers: true
	});
	//jsDesign
	//end

	//TODO: Кнопка обновления сценариев
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


	//TODO: Подгрузка сценапия
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

	
	setBlockHtml('scenarioTemplate', scenarioJSON.html);
	setBlockHtml('scenarioStyle', scenarioJSON.css);
	
	eval(scenarioJSON.javascriptStudio);
	



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