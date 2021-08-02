import os
import json
from flask import Flask, request, abort, redirect
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData

app = Flask(__name__)

config = {
    'DATABASE_URI': os.environ.get('DATABASE_URI', ''),
}

from sqlalchemy import create_engine
engine = create_engine(config['DATABASE_URI'], echo=True)

SESSIONS = {}

@app.route('/warehouse')
def me():
    if not 'X-UserId' in request.headers:
        return "Not authenticated"
    data = {}
    data['id'] = request.headers['X-UserId']
    data['login'] = request.headers['X-User']
    data['email'] = request.headers['X-Email']
    data['first_name'] = request.headers['X-First-Name']
    data['last_name'] = request.headers['X-Last-Name']
    data['id_request'] = request.headers['X-Request-id']
    return data

@app.route("/warehouse/config")
def configuration():
    # config['version'] = 'NEW'
    return json.dumps(config)

@app.route("/warehouse/test", methods=["GET"])
def test():
    return {"userid": request.headers['X-UserId']}

@app.route("/warehouse/getAll")
def getall():

    meta = MetaData()
    warehouses = Table(
        'warehouses', meta,
        Column('id', Integer, primary_key = True),
        Column('order_id', Integer),
    )
    with engine.connect() as connection:
        s = warehouses.select()
        result = connection.execute(s)

    rows = [dict(r.items()) for r in result]
    return json.dumps(rows)

@app.route("/warehouse/getTransactions")
def getTransactions():
    with engine.connect() as connection:
        result = connection.execute("select id, transaction_id, event from local_changes")
    rows = [dict(r.items()) for r in result]
    return json.dumps(rows)

@app.route("/warehouse/commit", methods=["POST"])
def commit():
    request_data = request.get_json()
    _transactionid = request_data['transaction_id']
    with engine.connect() as connection:
        result = connection.execute("select id, transaction_id, event from local_changes where transaction_id={}".format(_transactionid))
        rows = [dict(r.items()) for r in result]
        try:
            connection.execute(rows[0]["event"])
            connection.execute("DELETE FROM local_changes WHERE transaction_id={}".format(_transactionid))
            data = {"status": 1}
            return json.dumps(data)
        except Exception:
            data = {"status": 0}
            return json.dumps(data)


@app.route("/warehouse/rollback", methods=["POST"])
def rollback():
    request_data = request.get_json()
    _transactionid = request_data['transaction_id']
    with engine.connect() as connection:
        result = connection.execute("select id, transaction_id, event from local_changes where transaction_id={}".format(_transactionid))
        rows = [dict(r.items()) for r in result]
        try:
            connection.execute("DELETE FROM local_changes WHERE transaction_id={}".format(_transactionid))
            data = {"status": 1}
            return json.dumps(data)
        except Exception:
            data = {"status": 0}
            return json.dumps(data)

@app.route("/warehouse/create", methods=["POST"])
def create():
    request_data = request.get_json()
    _orderid = request_data['order_id']
    _transactionid = request_data['transaction_id']
    _product = request_data['product']

    event = "INSERT INTO warehouses(product, order_id) VALUES(''{}'',{})".format(_product, _orderid)
    with engine.connect() as connection:
        try:
            connection.execute("INSERT INTO local_changes (transaction_id, event) VALUES({}, '{}')".format(_transactionid, event))
            data = {"status": 1}
            return json.dumps(data)
        except Exception:
            data = {"status": 0}
            return json.dumps(data)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port='80', debug=True)
