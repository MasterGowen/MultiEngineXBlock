function MultiEngineXBlockEdit(runtime, element) {
    var elementDOM = element[0];
    var DEBUG = window.location.hostname.includes('local') || window.location.hostname === 'localhost';

    var mengine = {
        id: elementDOM.getAttribute('data-usage-id'),
        studentAnswerJSON: {},
        studentStateJSON: '',
        genAnswerObj: function () {},
        genJSON: function (type, dict) {
            if (dict === undefined) dict = {};
            var objectJSON = {};
            objectJSON[type.valueOf()] = dict;
            return JSON.stringify(objectJSON); // FIXED: no double stringify
        },
        forEach: function (collection, action) {
            collection = collection || {};
            for (var i = 0; i < collection.length; i++) action(collection[i]);
        },
        genID: function () {
            return 'id' + Math.random().toString(16).substr(2, 8).toUpperCase();
        },
        getData: function (requestURL) {
            if (!requestURL) return "";
            var xhr = new XMLHttpRequest();
            xhr.open("GET", requestURL, false); // deprecated
            xhr.send(null);
            return xhr.responseText;
        }
    };

    // Utility functions
    function forEachInCollection(collection, action) {
        collection = collection || {};
        for (var i = 0; i < collection.length; i++) action(collection[i]);
    }

    function childList(value) {
        var list = [];
        var nodes = value.children || value.childNodes;
        for (var i = 0; i < nodes.length; i++) {
            if (nodes[i].nodeType === 1) list.push(nodes[i]);
        }
        return list;
    }

    function generationID() {
        return 'id' + Math.random().toString(16).substr(2, 8).toUpperCase();
    }

    function generationAnswerJSON(answer) {
        return JSON.stringify({ answer: answer });
    }

    function getValueFild(idField) {
        var el = elementDOM.querySelector('#' + idField);
        if (!el) {
            if (DEBUG) console.warn(`[MultiEngineEdit] getValueFild: #${idField} not found`);
            return { body: document.createElement('div') };
        }
        var parser = new DOMParser();
        return parser.parseFromString(el.value || el.innerHTML, 'text/html');
    }

    function setValueFild(idField, value) {
        var el = elementDOM.querySelector('#' + idField);
        if (el) el.value = value;
    }

    function setBlockHtml(idBlock, contentHtml) {
        var el = elementDOM.querySelector('#' + idBlock);
        if (el) el.innerHTML = contentHtml;
    }

    // Tabs
    var tabList = `
        <li class="action-tabs is-active-tabs" id="main-settings-tab">Основные</li>
        <li class="action-tabs" id="scenario-settings-tab">Сценарий</li>
        <li class="action-tabs" id="advanced-settings-tab">Расширенные</li>`;
    var tabContainer = document.querySelector(".editor-modes.action-list.action-modes");
    if (tabContainer) tabContainer.innerHTML = tabList;

    function setActiveTab(activeId) {
        ['main', 'scenario', 'advanced'].forEach(name => {
            var tab = document.getElementById(name + '-settings-tab');
            var panel = document.getElementById(name + '-settings');
            if (tab) tab.classList.toggle('is-active-tabs', name + '-settings-tab' === activeId);
            if (panel) panel.toggleAttribute('hidden', name + '-settings-tab' !== activeId);
        });
    }

    ['main', 'scenario', 'advanced'].forEach(name => {
        var tab = document.getElementById(name + '-settings-tab');
        if (tab) tab.onclick = () => setActiveTab(name + '-settings-tab');
    });

    // Load scenario
    var scenarioURL = runtime.handlerUrl(element, 'send_scenario');
    var scenarioText = mengine.getData(scenarioURL);
    var scenarioJSON = {};
    try {
        scenarioJSON = JSON.parse(scenarioText);
    } catch (e) {
        console.error("[MultiEngineEdit] Invalid scenario JSON", e);
        scenarioJSON = { html: "", css: "", javascriptStudio: "" };
    }

    setBlockHtml('scenarioTemplate', scenarioJSON.html || "");
    setBlockHtml('scenarioStyle', scenarioJSON.css || "");

    // Execute studio scenario
    var studioJs = (scenarioJSON.javascriptStudio || "").trim();
    if (studioJs) {
        try {
            if (!studioJs.startsWith("(function") && !studioJs.startsWith("function")) {
                studioJs = `(function(elementDOM, mengine, $, logger) {\n${studioJs}\n});`;
            }
            const runner = new Function("elementDOM", "mengine", "$", "logger", studioJs + "\n//# sourceURL=multiengine-studio-scenario.js");
            runner(elementDOM, mengine, $, console);
            if (DEBUG) console.log("[MultiEngineEdit] Studio scenario executed");
        } catch (err) {
            console.error("[MultiEngineEdit] Studio scenario error:", err);
        }
    }

    // Save handler
    $(element).find('.save-button').on('click', function () {
        if (typeof scenarioSave === 'function') {
            try { scenarioSave(); } catch (e) { console.error("scenarioSave failed:", e); }
        }

        var data = {
            display_name: $(element).find('input[name=display_name]').val(),
            question: $(element).find('textarea[id=question-area]').val(),
            weight: $(element).find('input[name=weight]').val(),
            correct_answer: $(element).find('input[id=correct_answer]').val(),
            sequence: document.getElementById("sequence")?.checked || false,
            scenario: $(element).find('select[name=scenario]').val(),
            max_attempts: $(element).find('input[name=max_attempts]').val(),
            student_view_json: $(element).find('input[name=student_view_json]').val(),
            student_view_template: $(element).find('#student_view_template').val(),
        };

        $.post(runtime.handlerUrl(element, 'studio_submit'), JSON.stringify(data))
            .done(() => window.location.reload(false))
            .fail(xhr => {
                console.error("[MultiEngineEdit] Save failed:", xhr);
                alert("Ошибка сохранения. Проверьте консоль.");
            });
    });

    $(element).find('.cancel-button').on('click', function () {
        runtime.notify('cancel', {});
    });
}
