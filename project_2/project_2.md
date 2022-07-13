# <center>  PROJECT-2. Подгрузка новых данных. Уточнение анализа  (BY SQL)

**Задание 2.1**    
*Рассчитайте максимальный возраст (max_age) кандидата в таблице.*    

SELECT    
    MAX(age) AS max_age    
FROM hh.candidate   

<image src="/project_2/images/picture_0.jpg" alt="Текст с описанием картинки">

<center> ----------------------------------------------------------------------------

**Задание 2.2**  
*Теперь давайте рассчитаем минимальный возраст (min_age) кандидата в таблице.*   

SELECT   
    MIN(age) AS min_age   
FROM hh.candidate   

<image src="/project_2/images/picture_1.jpg" alt="Текст с описанием картинки">

*Какие выводы мы можем сделать? Если 14 лет в качестве минимального значения возраста хоть как-то может претендовать на адекватность, то 100 лет в качестве значения максимального возраста — это явно какая-то ошибка.*

<center> ----------------------------------------------------------------------------

**Задание 2.3**   
*Попробуем «почистить» данные. Напишите запрос, который позволит посчитать для каждого возраста (age) сколько (cnt) человек этого возраста у нас есть.*   
*Отсортируйте результат по возрасту в обратном порядке.*   

SELECT  
    DISTINCT age,  
    COUNT(id) cnt  
FROM hh.candidate  
GROUP BY age  
ORDER BY age DESC   

<image src="/project_2/images/picture_2.jpg" alt="Текст с описанием картинки">

<center> ----------------------------------------------------------------------------

**Задание 2.4**   
*По данным Росстата, средний возраст занятых в экономике России составляет 39.7 лет. Мы округлим это значение до 40.*   
*Найдите количество кандидатов, которые старше данного возраста. Не забудьте отфильтровать «ошибочный» возраст 100.*

SELECT   
    COUNT(id) cnt   
FROM hh.candidate   
WHERE age BETWEEN 41 AND 99 --фильтруем по 99 лет

<image src="/project_2/images/picture_3.jpg" alt="Текст с описанием картинки">

<center> ----------------------------------------------------------------------------

**Задание 3.1**   
*Для начала напишите запрос, который позволит узнать, сколько (cnt) у нас кандидатов из каждого города (city).*    
*Формат выборки: city, cnt.*   
*Группировку таблицы необходимо провести по столбцу title, результат отсортируйте по количеству в обратном порядке.*   

SELECT   
    city.title AS city,   
    COUNT(cand.id) AS cnt   
FROM hh.candidate AS cand   
    JOIN hh.city ON cand.city_id = city.id   
GROUP BY city   
ORDER BY cnt DESC   

<image src="/project_2/images/picture_4.jpg" alt="Текст с описанием картинки">

<center> ----------------------------------------------------------------------------

**Задание 3.2**  
*Москва бросается в глаза как, пожалуй, самый активный рынок труда. Напишите запрос, который позволит понять,*   
*каких кандидатов из Москвы устроит «проектная работа».*    
*Формат выборки: gender, age, desirable_occupation, city, employment_type.*  
*Отсортируйте результат по id кандидата.*  

SELECT   
    cand.gender,   
    cand.age,   
    cand.desirable_occupation,    
    city.title AS city,    
    cand.employment_type    
FROM hh.candidate AS cand    
     JOIN hh.city ON cand.city_id = city.id   
WHERE cand.employment_type LIKE '%проектная работа%'    
    AND city.title = 'Москва'   
ORDER BY cand.id   

<image src="/project_2/images/picture_5.jpg" alt="Текст с описанием картинки">

<center> ----------------------------------------------------------------------------

**Задание 3.3**  
*Данных оказалось многовато. Отфильтруйте только самые популярные IT-профессии — разработчик, аналитик, программист.*   
*Обратите внимание, что данные названия могут быть написаны как с большой, так и с маленькой буквы.*  
*Отсортируйте результат по id кандидата.*   

SELECT  
    cand.gender,  
    cand.age,  
    cand.desirable_occupation,   
    city.title AS city,    
    cand.employment_type  
FROM hh.candidate AS cand  
     JOIN hh.city ON cand.city_id = city.id  
WHERE cand.employment_type  LIKE '%проектная работа%'   
    AND city.title = 'Москва'   
    AND /* сначала пишем AND и далее в скобках через OR перечисляем IT-профессии, 
    для того чтобы в выборку вошли только нужные данные*/
    (LOWER(desirable_occupation)    LIKE  '%разработчик%'  --через LOWER приводим текст в нижний регистр 
    OR LOWER(desirable_occupation)  LIKE  '%аналитик%'   
    OR LOWER(desirable_occupation)  LIKE  '%программист%')
ORDER BY cand.id   

<image src="/project_2/images/picture_6.jpg" alt="Текст с описанием картинки">

<center> ----------------------------------------------------------------------------

**Задание 3.4**   
*Для общей информации попробуйте выбрать номера и города кандидатов, у которых занимаемая должность совпадает с желаемой.*
*Формат выборки: id, city.*
*Отсортируйте результат по городу и id кандидата.*

SELECT   
    cand.id AS id,  
    city.title AS city   
FROM hh.candidate AS cand   
     JOIN hh.city  on cand.city_id = city.id   
WHERE current_occupation = desirable_occupation    
ORDER BY city, id   

<image src="/project_2/images/picture_7.jpg" alt="Текст с описанием картинки">

<center> ----------------------------------------------------------------------------

**Задание 3.5**  
*Определите количество кандидатов пенсионного возраста.*   
*Пенсионный возраст для мужчин наступает в 65 лет, для женщин — в 60 лет.*  

SELECT  
    COUNT(id)  
FROM hh.candidate   
WHERE (gender = 'M' AND  age BETWEEN 65 AND 99) --не забываем фильтровать выбор 100 лет 
    OR (gender = 'F' AND age BETWEEN 60 AND 99) --не забываем фильтровать выбор 100 лет 

<image src="/project_2/images/picture_8.jpg" alt="Текст с описанием картинки">

<center> ----------------------------------------------------------------------------

**Задание 4.1**   
*Для добывающей компании нам необходимо подобрать кандидатов из Новосибирска, Омска, Томска и Тюмени,*  
*которые готовы работать вахтовым методом.*   
*Формат выборки: gender, age, desirable_occupation, city, employment_type, timetable_type.*  
*Отсортируйте результат по городу и номеру кандидата.*   

SELECT   
    cand.gender,  
    cand.age,  
    cand.desirable_occupation,  
    city.title AS city,    
    cand.employment_type,   
    tt.title AS timetable_type     
FROM hh.candidate AS cand   
    JOIN hh.city ON cand.city_id = city.id   
    JOIN hh.candidate_timetable_type AS ctt ON ctt.candidate_id = cand.id  
    JOIN hh.timetable_type AS tt ON tt.id = ctt.timetable_id  /*для того чтобы добавить названия категорий графика работы
    сначала присоедиянем доп.таблицу, так как у кандидата может быть несколько типов рабочего графика.*/ 
WHERE tt.title = 'вахтовый метод'  
    AND (city.title in  ('Новосибирск' , 'Омск','Томск','Тюмень'))   
ORDER BY city, cand.id    

<image src="/project_2/images/picture_9.jpg" alt="Текст с описанием картинки">

<center> ----------------------------------------------------------------------------

**Задание 4.2**   
*Для заказчиков из Санкт-Петербурга нам необходимо собрать список из 10 желаемых профессий кандидатов из того же города*   
*от 16 до 21 года  (в выборку включается 16 и 21, сортировка производится по возрасту) с указанием их возраста,*  
*а также добавить строку Total с общим количеством таких кандидатов.*  
*Напишите запрос, который позволит получить выборку вида:*  

(SELECT  
    desirable_occupation,  age  
FROM hh.candidate   
    JOIN hh.city ON city_id = city.id  
WHERE city.title = 'Санкт-Петербург'   
    AND age BETWEEN 16 and 21   
ORDER BY age  
LIMIT 10)  --берем в скобки, для того, чтобы отсротировать и вывести первые 10 строк, только для этой выборки  
UNION ALL  --присоединяем строчку с 'Total', соблюдая типизацию признаков 
SELECT  'Total',  COUNT(candidate.id)   
FROM hh.candidate   
    JOIN hh.city ON city_id = city.id   
WHERE city.title = 'Санкт-Петербург'    
    AND age BETWEEN 16 AND 21   

<image src="/project_2/images/picture_10.jpg" alt="Текст с описанием картинки">

<center> ----------------------------------------------------------------------------    