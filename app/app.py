#!/usr/bin/env python
#-*-coding:utf-8-*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8') #解决在linux下编码错误的问题

from flask import Flask,render_template,url_for,session,redirect,request,flash,abort,Markup
from werkzeug.security import check_password_hash
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib import sqla
from flask_wtf import Form
import os
import hashlib
import functools
from datetime import datetime
'''导入支持markdown文本内容的相关库'''
from markdown import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.extra import ExtraExtension
from micawber import bootstrap_basic, parse_html
from micawber.cache import Cache as OEmbedCache


'''配置内容'''
basedir=os.path.abspath(os.path.dirname(__file__))
#此处设置密码的hash值用于登陆，此处默认密码是'123'
#from werkzeug.security import generate_password_hash
#generate_password_hash('你的密码')
#将生成的值替换PASSWORD_HASH
PASSWORD_HASH = 'pbkdf2:sha1:1000$80Oc5MyH$74a5c46815e27f6282b744c6590b012cf9f23b56'
DEBUG=True
SECRET_KEY="(\x8c,\x9c\x1e\xe7y\x05\x98E4\x92\x12'd\xd2\xc4\xcd\x8e3@\xd5\xc15"
SQLALCHEMY_DATABASE_URI='sqlite:///'+os.path.join(basedir,'data.sqlite')
SQLALCHEMY_TRACK_MODIFICATIONS = True
# SQLALCHEMY_COMMIT_ON_TEARDOWN=True
SQLALCHEMY_ECHO=True
SITE_WIDTH = 800

'''配置注册'''
app=Flask(__name__)
app.config.from_object(__name__)
moment=Moment(app)
db=SQLAlchemy(app)
oembed_providers = bootstrap_basic(OEmbedCache())
admin=Admin(app, name='博客后台管理')

'''错误页面配置'''
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'),404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'),500


'''登陆验证'''
def login_required(fn):
    @functools.wraps(fn)
    def inner(*args,**kwargs):
        if session.get('logged_in'):
            return fn(*args,**kwargs)
        return redirect(url_for('login',next=request.path))
    return inner


'''登陆视图函数'''
@app.route('/login',methods=['POST','GET'])
def login():
    next_url=request.args.get('next') or request.form.get('next')
    if request.method == 'POST' and request.form.get('password'):
        if check_password_hash(app.config['PASSWORD_HASH'],request.form.get('password')):
            session['logged_in']=True
            session.permanent = True  # Use cookie to store session.
            flash('你已经成功登陆.','success')
            print(request.path)
            return redirect(next_url or url_for('index'))
        flash('密码错误，请重新输入.','danger')
    return render_template('login.html',next=next_url)

'''登出视图函数'''
@app.route('/logout',methods=['GET','POST'])
@login_required
def logout():
    if request.method == 'POST':
        session.clear()
        flash('你已经成功登出本站.','success')
        print(request.path)
        return redirect(url_for('index'))
    return render_template('logout.html')

'''博文数据库模型设计'''
class Post(db.Model):
    __tablename__='posts'
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(80))
    content=db.Column(db.Text)
    timestamp=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    published=db.Column(db.Boolean,index=True,default=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category',backref=db.backref('posts', lazy='dynamic'))

    def __init__(self,title,content,category,published=False):
        self.title=title
        self.content=content
        self.category=category
        if published:
            self.published=True

    @property
    def html_content(self):
        hilite = CodeHiliteExtension(linenums=False, css_class='highlight')
        extras = ExtraExtension()
        markdown_content = markdown(self.content, extensions=[hilite, extras])
        oembed_content = parse_html(
            markdown_content,
            oembed_providers,
            urlize_all=True,
            maxwidth=app.config['SITE_WIDTH'])
        return Markup(oembed_content)
    
    def __repr__(self):
        return '<Post %r>' % self.title

class Category(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(50),unique=True)
    
    def __repr__(self):
        return '<Category %r>' % self.name


'''首页视图函数'''
@app.route('/')
def index():
    page=request.args.get('page',1,type=int)
    pagination=Post.query.filter_by(published=True).order_by(Post.timestamp.desc()).paginate(page,per_page=10,error_out=False)
    posts=pagination.items
    return render_template('index.html',posts=posts,pagination=pagination,is_draft=False)

'''草稿箱视图函数'''
@app.route('/draft')
@login_required
def draft():
    page=request.args.get('page',1,type=int)
    pagination=Post.query.filter_by(published=False).order_by(Post.timestamp.desc()).paginate(page,per_page=10,error_out=False)
    posts=pagination.items
    return render_template('index.html',posts=posts,pagination=pagination,is_draft=True)


'''博文创建视图'''
@app.route('/create',methods=['GET','POST'])
@login_required
def create():
    categories=Category.query.order_by(db.desc('id')).all()
    if request.method == 'POST':
        if request.form.get('title') and request.form.get('content'):
            category=Category.query.filter_by(id=request.form.get('category')).first()
            post=Post(title=request.form.get('title'),content=request.form.get('content'),category=category,published=request.form.get('published',None))
            try:
                db.session.add(post)
                db.session.commit()
            except:
                flash('博文添加错误,请重新编辑.','danger')
                return render_template('create.html',categories=categories)
            if request.form.get('published'):
                flash('博文添加成功，已发布.','success')
                return redirect(url_for('index'))
            flash('博文添加成功,已存入草稿箱.','success')
            return redirect(url_for('draft'))
    return render_template('create.html',categories=categories)

'''博文详细内容视图'''
@app.route('/detail')
def detail():
    if not request.args.get('post_id'):
        abort(404)
    post=Post.query.filter_by(id=request.args.get('post_id')).first()
    if not post:
        abort(404)
    return render_template('detail.html',post=post)

@app.route('/edit',methods=['GET','POST'])
@login_required
def edit():
    if not request.args.get('post_id'):
        abort(404)
    post=Post.query.filter_by(id=request.args.get('post_id')).first()
    categories=Category.query.order_by(db.desc('id')).all()
    if not post or not categories:
        abort(404)
    if request.method == 'POST':
        post.title=request.form.get('title')
        post.content=request.form.get('content')
        post.category=Category.query.filter_by(id=request.form.get('category')).first()
        if request.form.get('published',None):
            post.published=True
        else:
            post.published=False
        try:
            db.session.add(post)
            db.session.commit()
            flash('博文更新成功.','success')
            return redirect(url_for('detail',post_id=post.id))
        except:
            flash('博文更新失败.','danger')

    return render_template('edit.html',post=post,categories=categories)

'''限制游客访问后台'''
@app.before_request
def before_request():
    if '/admin' in request.path and not session.get('logged_in',None):
        return redirect(url_for('login',next=request.path))

'''博文分类视图'''
@app.route('/posts')
def posts():
    posts=Post.query.filter(Post.category_id==request.args.get('category_id'),Post.published==True).order_by(Post.timestamp.desc()).all()
    if posts:
        return render_template('posts.html',posts=posts)
    return redirect(url_for('index'))

'''添加CSRF Protection'''
@app.before_request
def csrf_protect():
    if request.method == "POST" and '/admin' not in request.path:
        token = session.pop('_csrf_token', None)
        if not token or token != request.form.get('_csrf_token'):
            abort(404)
            
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = hashlib.sha1(os.urandom(24)).hexdigest()
    return session['_csrf_token']
app.jinja_env.globals['csrf_token'] = generate_csrf_token    


'''后台管理'''
class PostAdmin(sqla.ModelView):
    form_base_class = Form
    column_display_pk = True
    can_create = False
    column_list = ('id','title','category','published')

class CategoryAdmin(sqla.ModelView):
    form_base_class = Form
    column_display_pk = True
    can_create = True
    #Category模型中不能定义__init__方法，否则无法在admin创建category对象
admin.add_view(PostAdmin(Post, db.session))
admin.add_view(CategoryAdmin(Category, db.session))




