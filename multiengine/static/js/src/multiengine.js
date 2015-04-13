/* Javascript for MultiEngineXBlock. */
function MultiEngineXBlock(runtime, element) {

    function success_func(result) {
    		//console.log("Correct: " + result.correct + " Answer: "+ JSON.stringify(result.answer) + " Correct answer: " + JSON.stringify(result.correct_answer))

        //$('.count', element).text(result.count);
    }
var handlerUrl = runtime.handlerUrl(element, 'student_submit');

  $(element).find('.save').bind('click', function() {
    var data = $(element).find('textarea[id=answer]').val();
    
            $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify(data),
            success: success_func 
        });
  });
}