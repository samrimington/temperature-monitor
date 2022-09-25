import datetime
import os

import peewee as pw

db = pw.MySQLDatabase(
    'environment',
    host='localhost',
    port=3306,
    user=os.environ["DB_USER"],
    password=os.environ["DB_PWD"]
)


class BaseModel(pw.Model):
    class Meta:
        database = db


class Environment(BaseModel):
    t = pw.DateTimeField(default=datetime.datetime.now, primary_key=True)
    downstairs_indoor_humidity = pw.FloatField(null=True)
    downstairs_indoor_temperature = pw.FloatField(null=True)
    downstairs_outdoor_temperature = pw.FloatField(null=True)
    upstairs_indoor_humidity = pw.FloatField(null=True)
    upstairs_indoor_temperature = pw.FloatField(null=True)
