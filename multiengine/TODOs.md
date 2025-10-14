Для полной совместимости с браузерами метода trim:

```
if(typeof(String.prototype.trim) === "undefined")
{
    String.prototype.trim = function() 
    {
        return String(this).replace(/^\s+|\s+$/g, '');
    };
}
```

1.  В @XBlock.json_handler добавить `JsonHandlerError` для ошибок логического состояния, валидных: 


```python
@XBlock.json_handler
def submit_answer(self, data, suffix=''):
    if self.past_due():
        raise JsonHandlerError(400, "Ответ нельзя отправить: время истекло.")
    
    if not self.has_attempts_left():
        raise JsonHandlerError(400, "Превышено количество попыток.")
    
    # Обработка ответа...
    return {"result": "success", "score": self.score}
```

2. Добавить обработчики `JsonHandlerError` в js:

```js
$.ajax({
    url: handlerUrl,
    type: "POST",
    data: JSON.stringify(data),
    success: function(response) {
        // успех
    },
    error: function(xhr) {
        const errorMsg = xhr.responseJSON?.error || "Неизвестная ошибка";
        alert("Ошибка: " + errorMsg);
    }
});
```
