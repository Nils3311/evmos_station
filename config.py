import os

class Config(object):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = ""

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', None)
    print(SQLALCHEMY_DATABASE_URI)

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://hflxztkczpdarl:478f03628bb154a20f7bbcda1ee0b984d30fb19a69d92eaa52aaa4df24e0ea74@ec2-54-76-249-45.eu-west-1.compute.amazonaws.com:5432/d6t04qgo4ujoj6'

