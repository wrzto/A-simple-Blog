# A-simple-Blog
利用flask搭建的一个简单的个人博客网站

python版本3.5(实测python2版本也可用)

目前版本只是实现了个人博客功能

1.后台使用了flask-admin

2.文本支持markdown,支持语法高亮

3.数据库用的sqlite3,orm用的是flask-sqlalchemy

4.前端用的bootstrap

启动方法

1.命令行切换至app目录下，安装相应扩展包，sudo pip install -r requirement.txt

2.数据库创建

  	1.python manage.py shell

  	2.db.create_all()

  	3.exit()

3.启动app，  python manage.py run

4.打开127.0.0.1:5000/admin访问后台，密码默认123

目前版本比较简单，只为满足自己记录笔记的需求，后续继续扩展，完成一个完善的博客系统.
