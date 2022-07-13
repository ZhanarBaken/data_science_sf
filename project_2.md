**Задание 2.1**    
*Рассчитайте максимальный возраст (max_age) кандидата в таблице.*    

select    
    max(age) max_age    
from hh.candidate    


**Задание 2.2**  
*Теперь давайте рассчитаем минимальный возраст (min_age) кандидата в таблице.*   

select   
    min(age) min_age   
from hh.candidate   

*Какие выводы мы можем сделать? Если 14 лет в качестве минимального значения возраста хоть как-то может претендовать на адекватность, то 100 лет в качестве значения максимального возраста — это явно какая-то ошибка.*


**Задание 2.3**   
*Попробуем «почистить» данные. Напишите запрос, который позволит посчитать для каждого возраста (age) сколько (cnt) человек этого возраста у нас есть.*   
*Отсортируйте результат по возрасту в обратном порядке.*   

select  
    distinct age age,  
    count(id) cnt  
from hh.candidate  
group by age  
order by age desc   


**Задание 2.4**   
*По данным Росстата, средний возраст занятых в экономике России составляет 39.7 лет. Мы округлим это значение до 40.*   
*Найдите количество кандидатов, которые старше данного возраста. Не забудьте отфильтровать «ошибочный» возраст 100.*

select   
    count(id) cnt   
from hh.candidate   
where age between 41 and 99   


**Задание 3.1**   
*Для начала напишите запрос, который позволит узнать, сколько (cnt) у нас кандидатов из каждого города (city).*    
*Формат выборки: city, cnt.*   
*Группировку таблицы необходимо провести по столбцу title, результат отсортируйте по количеству в обратном порядке.*   

select   
    city.title as city,   
    count(cand.id) as cnt   
from hh.candidate as cand   
    join hh.city as city  on cand.city_id = city.id   
group by city   
order by cnt desc   



**Задание 3.2**  
*Москва бросается в глаза как, пожалуй, самый активный рынок труда. Напишите запрос, который позволит понять,*   
*каких кандидатов из Москвы устроит «проектная работа».*    
*Формат выборки: gender, age, desirable_occupation, city, employment_type.*  
*Отсортируйте результат по id кандидата.*  

select   
    cand.gender,   
    cand.age,   
    cand.desirable_occupation,    
    city.title as city,    
    cand.employment_type    

from hh.candidate as cand    
     join hh.city as city  on cand.city_id = city.id   
where cand.employment_type like '%проектная работа%'    
    and city.title = 'Москва'   
order by cand.id   


**Задание 3.3**  
*Данных оказалось многовато. Отфильтруйте только самые популярные IT-профессии — разработчик, аналитик, программист.*   
*Обратите внимание, что данные названия могут быть написаны как с большой, так и с маленькой буквы.*  
*Отсортируйте результат по id кандидата.*   

select  
    cand.gender,  
    cand.age,  
    cand.desirable_occupation,   
    city.title as city,    
    cand.employment_type  
from hh.candidate as cand  
     join hh.city as city  on cand.city_id = city.id  
where cand.employment_type like '%проектная работа%'   
    and city.title = 'Москва'   
    and (lower(desirable_occupation) like  '%разработчик%'   
    or lower(desirable_occupation) like  '%аналитик%'   
    or lower(desirable_occupation) like  '%программист%')   
order by cand.id   


**Задание 3.4**   
*Для общей информации попробуйте выбрать номера и города кандидатов, у которых занимаемая должность совпадает с желаемой.*
*Формат выборки: id, city.*
*Отсортируйте результат по городу и id кандидата.*

select   
    cand.id as id,  
    city.title as city   
from hh.candidate as cand   
     join hh.city as city  on cand.city_id = city.id   
where current_occupation = desirable_occupation    
order by city, id   


**Задание 3.5**  
*Определите количество кандидатов пенсионного возраста.*   
*Пенсионный возраст для мужчин наступает в 65 лет, для женщин — в 60 лет.*  

select  
    count(id)  
from hh.candidate   
where (gender = 'M'and  age between 65 and 99)   
    or (gender = 'F' and age between 60 and 99)  


**Задание 4.1**   
*Для добывающей компании нам необходимо подобрать кандидатов из Новосибирска, Омска, Томска и Тюмени,*  
*которые готовы работать вахтовым методом.*   
*Формат выборки: gender, age, desirable_occupation, city, employment_type, timetable_type.*  
*Отсортируйте результат по городу и номеру кандидата.*   

select 
    cand.gender, 
    cand.age, 
    cand.desirable_occupation, 
    city.title as city,  
    cand.employment_type,  
    tt.title as timetable_type  
from hh.candidate as cand  
    join hh.city as city  on cand.city_id = city.id   
    join hh.CANDIDATE_TIMETABLE_TYPE as ctt on ctt.candidate_id = cand.id  
    join hh.TIMETABLE_TYPE as tt on tt.id = ctt.timetable_id   
where tt.title = 'вахтовый метод'  
    and (city.title in  ('Новосибирск' , 'Омск','Томск','Тюмень'))   
order by city, cand.id    


**Задание 4.2**   
*Для заказчиков из Санкт-Петербурга нам необходимо собрать список из 10 желаемых профессий кандидатов из того же города*   
*от 16 до 21 года  (в выборку включается 16 и 21, сортировка производится по возрасту) с указанием их возраста,*  
*а также добавить строку Total с общим количеством таких кандидатов.*  
*Напишите запрос, который позволит получить выборку вида:*  

(select  
    desirable_occupation,  
    age  
from hh.candidate   
    join hh.city on city_id = hh.city.id  
where hh.city.title = 'Санкт-Петербург'   
    and age between 16 and 21   
order by age  
limit 10)   
UNION ALL   
   
SELECT   
    'Total',   
    count(hh.candidate.id)   
FROM hh.candidate   
    join hh.city on city_id = hh.city.id   
where hh.city.title = 'Санкт-Петербург'    
    and age between 16 and 21   