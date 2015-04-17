/* Javascript for MultiEngineXBlock. */
function MultiEngineXBlock(runtime, element) {
    function success_func(result) {
    		console.log("Correct: " + result.correct/result.weight*100 + "% " + "Answer opportunity : " + result.test)

        //$('.count', element).text(result.count);
    }
var handlerUrl = runtime.handlerUrl(element, 'student_submit');




  $(element).find('.Check').bind('click', function() {
    var data = $(element).find('textarea[id=answer]').val();
    
            $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify(data),
            success: success_func 
        });
  });

  //var handlerUrl = runtime.handlerUrl(element,'test_return');

}