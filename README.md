# HTTP_custom_server

## Кастомный веб-сервер частично реализующий протокол HTTP, основан на классической thread pool архитектуре.


__Веб-сервер умеет:__

* Масштабироваться на несколько `worker'ов`.
Числов `worker'ов` задается аргументом командной строки `-w`.
* Отвечать 200, 403 или 404 на `GET`-запросы и `HEAD`-запросы.
* Отвечать 405 на прочие запросы.
* Возвращать файлы по произвольному пути в `DOCUMENT_ROOT`. 
Вызов `/file.html` возвращает содержимое `DOCUMENT_ROOT/file.html`.
`DOCUMENT_ROOT` задается аргументом командной строки `-r`
* Возвращать `index.html` как индекс директории.
Вызов `/directory/` возвращает `DOCUMENT_ROOT/directory/index.html`.
* Отвечать следующими заголовками для успешных `GET`-запросов: `Date, Server, Content-Length, Content-Type, Connection`.
* Корректный `Content-Type` для: `.html, .css, .js, .jpg, .jpeg, .png, .gif, .swf`.
* Понимает пробелы и `%XX` в именах файлов.

* `python http_server.py -w 5 -r ./html_content`

## Результаты нагрузочного тестирования
`ab -n 50000 -c 100 -r http://localhost:8080`

Server Software:        OTUServer  
Server Hostname:        localhost  
Server Port:            8080  

Document Path:          /  
Document Length:        77 bytes  

Concurrency Level:      100  
Time taken for tests:   1406.488 seconds  
Complete requests:      50000  
Failed requests:        0  
Non-2xx responses:      50000  
Total transferred:      8650000 bytes  
HTML transferred:       3850000 bytes  
Requests per second:    35.55 [#/sec] (mean)  
Time per request:       2812.977 [ms] (mean)  
Time per request:       28.130 [ms] (mean, across all concurrent requests)  
Transfer rate:          6.01 [Kbytes/sec] received  

Connection Times (ms)  
| | min | mean | [+/-sd] | median | max |
|------- | --- | --- | --- | --- | --- |             
| Connect: | 0 | 28 | 115.4 | 0 | 531 |
| Processing: | 5 | 2778 | 264.8 | 2560 | 3611 | 
| Waiting: | 2 | 1509 | 733.8 | 1526 | 3091 |
| Total: | 5 | 2806 | 265.4 | 3039 | 3611 |


Percentage of the requests served within a certain time (ms) 
| Quant. | time(ms) |
| ---- | -----|
| 50% | 3039 |
| 66% | 3048 |
| 75% | 3052 |
| 80% | 3054 |
| 90% | 3060 |
| 95% | 3066 |
| 98% | 3073 |
| 99% | 3079 |
| 100% | 3611 (longest request) |