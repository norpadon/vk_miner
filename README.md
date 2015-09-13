#VK Miner

Инструмент для извлечения и обработки данных из ВКонтакте

1.  [Что](#что-это)
2.  [Зачем](#зачем-это)
3.  [Как](#как-этим-пользоваться)
    1.  [Установить](#установка)
    2.  [Работать](#использование)
4.  [Что дальше](#что-дальше)
5. [FAQ](#faq)

#Что это

Это библиотека, позволяющая

* Загружать из ВКонтакте информацию о людях и сообществах
* Конвертировать ее в таблицы Pandas
* Обрабатывать полученные данные

Библиотека находится в стадии активной разработки, поэтому пока лишена многих полезных фич вроде тестов и нормальной документации.

#Зачем это

Just for lulz.

#Как этим пользоваться

##Установка

1.  Установите hdf5
    ```
    sudo apt-get install libhdf4-5 libhdf5-7-dev
    ```
2.  Установите все питонячьи зависимости
    ```
    pip3 install -r requirements.txt
    ```
3.  Выполните setup.py
    ```
    python3 setup.py install
    ```
    
##Использование

```python
from vk_miner.algorithms import *
from vk_miner.community import *
from vk_async import API

#Инициализируем API для запросов
api = API(user_login='<Ваш номер телефона или email>', user_password='<Ваш пароль>', app_ids=[<Список ваших приложений>])

#Загружаем людей, находящихся на расстоянии <=2 от автора приложения.
ds = load_friends_bfs(api, [170100773], 2)

#Сохраняем их
ds.save('my_friends.hdf5')

#Выкидываем всех друзей друзей
ds = ds.filter_users(lambda u: u.layer < 2)

#Соединяем таблицы для удобства
users = ds.users.join(ds.cities, on='city_id').\
            join(ds.universities, on='university_id').\
            drop(['city_id', 'university_id', 'latitude', 'longitude', 'last_seen'], axis=1)
           
#Настраиваем matplotlib
import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = (10.0, 10.0)
from matplotlib import rc
rc('font',**{'family': 'sans-serif'})
rc('text', usetex=True)
rc('text.latex',unicode=True)
rc('text.latex',preamble=r'\usepackage[utf8]{inputenc}')
rc('text.latex',preamble=r'\usepackage[russian]{babel}')
            
#Строим диаграмму популярности университетов
users.university.value_counts()[:20].plot(kind='bar')

#Рисуем граф друзей
import networkx
networkx.draw(ds.friends_graph())
```

Более подробную документацию пока можно найти только в исходном коде.

#Что дальше

Автор приносит свои извенения за качество этого продукта.
К сожалению, некоторые решения (в частности, загрузка пользователей) являются откровенными костылями и автору за них стыдно.
Если у вас есть время и желание их исправить, а может и добавить новую функциональность -- исправляйте, добавляйте и присылайте pull request.

#FAQ

* Почему данные хранятся в такой форме? Это же неудобно?
    * Потому что так -- компактно. Хранение данных в SQL-like талицах позволяет держать в памяти очень много пользователей
* Почему HDF5?
    * Потому что pandas очень хорошо и быстро с ним работает из коробки. Pickle, к примеру, падает при попытке сериализовать миллион пользователей.
* Почему нет X?
    * Потому что автор -- криворукий лентяй. Если вы в состоянии добавить X, добавьте и пришлите PR, будет здорово.
* Как связаться с автором?
    * norpadon@yandex.ru, vk.com/norpadon
    
![Котик](https://pp.vk.me/c624526/v624526773/417a6/fGsVuC7sXyc.jpg)
