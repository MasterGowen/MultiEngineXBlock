/* Javascript for MultiEngineXBlock. */
if (!MultiEngineXBlockState) var MultiEngineXBlockState = {};

function MultiEngineXBlock(runtime, element) {
    var elementDOM = element;
    var DEBUG = window.location.hostname.includes('local') || window.location.hostname === 'localhost';

    var mengine = {
        id: elementDOM.getAttribute("data-usage-id"),
        studentAnswerJSON: {},
        studentStateJSON: "",
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
            return "id" + Math.random().toString(16).substr(2, 8).toUpperCase();
        },
        getData: function (requestURL) {
            if (!requestURL) return "";
            var xhr = new XMLHttpRequest();
            xhr.open("GET", requestURL, false); // deprecated, but works
            xhr.send(null);
            return xhr.responseText;
        }
    };

    // Utility functions (backward compatibility)
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
        return "id" + Math.random().toString(16).substr(2, 8).toUpperCase();
    }

    function generationAnswerJSON(answer) {
        return JSON.stringify({ answer: answer });
    }

    function getValueFild(idField) {
        var el = elementDOM.querySelector("#" + idField);
        if (!el) {
            if (DEBUG) console.warn(`[MultiEngine] getValueFild: #${idField} not found`);
            return { body: document.createElement('div') };
        }
        var parser = new DOMParser();
        return parser.parseFromString(el.value || el.innerHTML, "text/html");
    }

    function setValueFild(idField, value) {
        var el = elementDOM.querySelector("#" + idField);
        if (el) el.value = value;
    }

    function setBlockHtml(idBlock, contentHtml) {
        var el = elementDOM.querySelector("#" + idBlock);
        if (el) el.innerHTML = contentHtml;
    }

    // Success handlers
    function success_func(result) {
        $(".attempts", element).text(result.attempts);
        $(element).find(".weight").html('Набрано баллов: <me-span class="points"></span>');
        $(".points", element).text(result.correct + " из " + result.weight);
        if (result.max_attempts && result.max_attempts <= result.attempts) {
            $(".Check", element).remove();
            $(".Save", element).remove();
        }
    }

    function success_save() {
        setTimeout(() => {
            var btn = element.querySelector(".Save");
            if (btn) btn.innerHTML = 'Сохранить<span class="sr"> ваш ответ</span>';
        }, 1000);
    }

    function success_check() {
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: mengine.genJSON("answer", mengine.genAnswerObj()),
            success: success_func
        });
    }

    // Load scenario and state
    var scenarioURL = runtime.handlerUrl(element, "send_scenario");
    var scenarioText = mengine.getData(scenarioURL);
    var scenarioJSON = {};
    try {
        scenarioJSON = JSON.parse(scenarioText);
    } catch (e) {
        console.error("[MultiEngine] Invalid scenario JSON", e);
        scenarioJSON = { cssStudent: "", javascriptStudent: "" };
    }

    setBlockHtml("scenarioStyleStudent", scenarioJSON.cssStudent || "");

    var studentStateURL = runtime.handlerUrl(element, "get_student_state");
    mengine.studentStateJSON = mengine.getData(studentStateURL);

    var handlerUrl = runtime.handlerUrl(element, "student_submit");
    var saveStateUrl = runtime.handlerUrl(element, "save_student_state");

    // Buttons
    $(element).find(".Save").on("click", function () {
        $(this).text("Сохранение...");
        $.ajax({ type: "POST", url: saveStateUrl, data: mengine.genJSON("state", mengine.genAnswerObj()), success: success_save });
    });

    $(element).find(".Check").on("click", function () {
        $.ajax({ type: "POST", url: saveStateUrl, data: mengine.genJSON("state", mengine.genAnswerObj()), success: success_check });
    });

    // Execute student scenario
    var jsCode = (scenarioJSON.javascriptStudent || "").trim();
    if (jsCode) {
        try {
            if (!jsCode.startsWith("(function") && !jsCode.startsWith("function")) {
                jsCode = `(function(element, mengine, runtime, $, logger) {\n${jsCode}\n});`;
            }
            const runner = new Function("element", "mengine", "runtime", "$", "logger", jsCode + "\n//# sourceURL=multiengine-scenario.js");
            runner(elementDOM, mengine, runtime, $, console);
            if (DEBUG) console.log("[MultiEngine] Student scenario executed");
        } catch (err) {
            console.error("[MultiEngine] Scenario error:", err);
        }
    }

    // Optional debug state
    if (typeof MultiEngineXBlockState === 'object') {
        MultiEngineXBlockState[mengine.id] = { element, mengine };
    }
}