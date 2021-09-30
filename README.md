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
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   319.757 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      8400000 bytes
HTML transferred:       1700000 bytes
Requests per second:    156.37 [#/sec] (mean)
Time per request:       639.513 [ms] (mean)
Time per request:       6.395 [ms] (mean, across all concurrent requests)
Transfer rate:          25.65 [Kbytes/sec] received  

Connection Times (ms)  
| | min | mean | [+/-sd] | median | max |
|------- | --- | --- | --- | --- | --- |             
| Connect: | 0 | 0 | 0.3 | 0 | 4 |
| Processing: | 15 | 635 | 65.4 | 645 | 801 |
| Waiting: | 10 | 634 | 65.3 | 643 | 798 |
| Total: | 16 | 635 | 65.4 | 645 | 801 |


Percentage of the requests served within a certain time (ms) 
| Quant. | time(ms) |
| ---- | -----|
| 50% | 645 |
| 66% | 664 |
| 75% | 676 |
| 80% | 684 |
| 90% | 703 |
| 95% | 717 |
| 98% | 732 |
| 99% | 742 |
| 100% | 801 (longest request) |