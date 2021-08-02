import os
import json
import requests
from flask import Flask, request, abort, redirect, jsonify
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData

app = Flask(__name__)

config = {
    'DATABASE_URI': os.environ.get('DATABASE_URI', ''),
}

from sqlalchemy import create_engine
engine = create_engine(config['DATABASE_URI'], echo=True)

SESSIONS = {}

@app.route('/coordinator')
def me():
    if not 'X-UserId' in request.headers:
        return "Not authenticated"
    data = {}
    data['id'] = request.headers['X-UserId']
    data['login'] = request.headers['X-User']
    data['email'] = request.headers['X-Email']
    data['first_name'] = request.headers['X-First-Name']
    data['last_name'] = request.headers['X-Last-Name']
    return data

@app.route("/coordinator/config")
def configuration():
    # config['version'] = 'NEW'
    return json.dumps(config)

@app.route("/coordinator/test", methods=["GET"])
def test():
    return {"userid": request.headers['X-UserId']}

@app.route("/coordinator/create", methods=["POST"])
def create():
    request_data = request.get_json()
    _orderid = request_data['order_id']
    _product = request_data['product']
    _cost = request_data['cost']

    with engine.connect() as connection:
        connection.execute("INSERT INTO coordinators (order_id) VALUES({}) ".format(_orderid))
        result = connection.execute("select id, order_id, status from coordinators where order_id={}".format(_orderid))
        transactions = [dict(r.items()) for r in result]
        try:
            #Отправка запроса на сервис payment
            data = {"transaction_id":transactions[0]["id"], "order_id":_orderid, "cost": _cost}
            data_json = json.dumps(data)
            headers = {'Content-type': 'application/json'}
            responsePayment = requests.post('http://arch.homework/payment/create', data=data_json, headers=headers)
            paymentStatus = responsePayment.json()["status"]

            #Отправка запроса на сервис warehouse
            data = {"transaction_id":transactions[0]["id"], "order_id":_orderid, "product": _product}
            data_json = json.dumps(data)
            headers = {'Content-type': 'application/json'}
            responseWarehouse = requests.post('http://arch.homework/warehouse/create', data=data_json, headers=headers)
            warehouseStatus = responseWarehouse.json()["status"]

            # Отправка запроса на сервис delivery
            data = {"transaction_id":transactions[0]["id"], "order_id":_orderid, "product": _product}
            data_json = json.dumps(data)
            headers = {'Content-type': 'application/json'}
            responseDelivery = requests.post('http://arch.homework/delivery/create', data=data_json, headers=headers)
            deliveryStatus = responseDelivery.json()["status"]

            data = {"transaction_id":transactions[0]["id"]}
            data_json = json.dumps(data)
            if paymentStatus == 1 and warehouseStatus == 1 and deliveryStatus == 1:
                requests.post('http://arch.homework/payment/commit', data=data_json, headers=headers)
                requests.post('http://arch.homework/warehouse/commit', data=data_json, headers=headers)
                requests.post('http://arch.homework/delivery/commit', data=data_json, headers=headers)
                connection.execute("UPDATE coordinators SET status = 'commit' where order_id={}".format(_orderid))
                data = {"status":1}
                return json.dumps(data)
            else:
                requests.post('http://arch.homework/payment/rollback', data=data_json, headers=headers)
                requests.post('http://arch.homework/warehouse/rollback', data=data_json, headers=headers)
                requests.post('http://arch.homework/delivery/rollback', data=data_json, headers=headers)
                connection.execute("UPDATE coordinators SET status = 'rollback' where order_id={}".format(_orderid))
                data = {"status":0}
                return json.dumps(data)
        except Exception:
            data = {"status":0}
            return json.dumps(data)

@app.route("/coordinator/getAll", methods=["GET"])
def getAll():
    with engine.connect() as connection:
        result = connection.execute("select * from coordinators")

    rows = [dict(r.items()) for r in result]
    return json.dumps(rows)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port='80', debug=True)
