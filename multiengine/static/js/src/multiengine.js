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