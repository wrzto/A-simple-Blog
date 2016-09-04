#!/usr/bin/env python
#-*-coding:utf-8-*-

from app import app,db,Post,Category
from flask_script import Manager,Server,Shell

manage=Manager(app)

def make_shell_context():
	return dict(app=app,db=db,Post=Post,Category=Category)

manage.add_command('run',Server(use_debugger=True,host='127.0.0.1',port=5000))
manage.add_command('shell',Shell(make_context=make_shell_context))


if __name__=='__main__':
    manage.run()
