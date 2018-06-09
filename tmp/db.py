import flask

app = flask.Flask(__name__)

class MyDB():
    def __init__(self):
        print('A db connection is created')
    
    def close(self):
        print('A db is closed')

def connection_to_database():
    return MyDB()

def get_db():
    db = getattr(flask.g, '_database', None)
    if db is None:
        db = connection_to_database()
        flask.g._database = db
        print(flask.g)
    return db

@app.teardown_request
def teardown_db(reponse):
    db = getattr(flask.g, '__database', None)
    if db is not None:
        db.close()