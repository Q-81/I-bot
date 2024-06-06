from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

import os

from transformers import pipeline
from transformers import AutoModelForTokenClassification
from transformers import AutoTokenizer

import pymorphy3

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///UsersSessionsTasks.db'

db = SQLAlchemy(app)
migrate = Migrate(app,  db)

print(os.getcwd())
clf = pipeline(
        task='token-classification',
        model=AutoModelForTokenClassification.from_pretrained('models/pt_save_pretrained'),
        tokenizer=AutoTokenizer.from_pretrained("DeepPavlov/rubert-base-cased"))

morph = pymorphy3.MorphAnalyzer()

from api import routes