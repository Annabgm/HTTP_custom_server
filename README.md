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

* Запуск:  `python http_server.py -w 5 -r ./html_content`

## Результаты нагрузочного тестирования
`ab -n 50000 -c 100 -r http://localhost:8080`

Server Software:        OTUServer
Server Hostname:        localhost
Server Port:            8080

Document Path:          /
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   44.506 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      8400000 bytes
HTML transferred:       1700000 bytes
Requests per second:    1123.45 [#/sec] (mean)
Time per request:       89.012 [ms] (mean)
Time per request:       0.890 [ms] (mean, across all concurrent requests)
Transfer rate:          184.32 [Kbytes/sec] received  

Connection Times (ms)  
| | min | mean | [+/-sd] | median | max |
|------- | --- | --- | --- | --- | --- |             
| Connect: | 0 | 0 | 0.4 | 0 | 1 |
| Processing: | 17 | 85 | 13.0 | 80 | 163 |
| Waiting: | 3 | 84 | 13.0 | 80 | 163 |
| Total: | 17 | 85 | 13.0 | 80 | 163 |


Percentage of the requests served within a certain time (ms) 
| Quant. | time(ms) |
| ---- | -----|
| 50% | 80 |
| 66% | 82 |
| 75% | 85 |
| 80% | 87 |
| 90% | 97 |
| 95% | 115 |
| 98% | 132 |
| 99% | 151 |
| 100% | 163 (longest request) |