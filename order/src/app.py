import os
import json
import requests
from flask import Flask, request, abort, redirect
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData

app = Flask(__name__)

config = {
    'DATABASE_URI': os.environ.get('DATABASE_URI', ''),
}

from sqlalchemy import create_engine
engine = create_engine(config['DATABASE_URI'], echo=True)

SESSIONS = {}

@app.route('/order')
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

@app.route("/order/config")
def configuration():
    # config['version'] = 'NEW'
    return json.dumps(config)

@app.route("/order/test", methods=["GET"])
def test():
    return {"userid": request.headers['X-UserId']}

@app.route("/order/<int:order_id>")
def user(order_id):

    meta = MetaData()
    orders = Table(
        'orders', meta,
        Column('id', Integer, primary_key = True),
        Column('order_id', Integer),
        Column('product', String),
        Column('request_id', String),
        Column('is_status_payed', String),
    )
    with engine.connect() as connection:
        s = orders.select().where(orders.c.order_id == order_id)
        result = connection.execute(s)
                                                  
    rows = [dict(r.items()) for r in result]
    return json.dumps(rows)


@app.route("/order/create", methods=["POST"])
def create():
    data = {}
    data['id_request'] = request.headers['X-Request-id']

    request_data = request.get_json()
    _orderid = request_data['order_id']
    _product = request_data['product']
    _cost = request_data['cost']

    rows = []
    with engine.connect() as connection:
        result = connection.execute("select id, order_id, is_status_payed from orders where request_id='{}'".format(data['id_request']))
        rows = [dict(r.items()) for r in result]
        if len(rows) == 0:
            connection.execute(
                "INSERT INTO orders (order_id, product, cost, request_id) VALUES({}, '{}', {}, '{}') ".format(_orderid, _product, _cost, data['id_request']))

            result = connection.execute("select id, order_id, is_status_payed from orders where request_id='{}'".format(data['id_request']))
            rows = [dict(r.items()) for r in result]

            data = {"order_id":_orderid, "product":"'"+_product+"'", "cost":_cost}
            data_json = json.dumps(data)
            headers = {'Content-type': 'application/json'}
            response = requests.post('http://arch.homework/coordinator/create', data=data_json, headers=headers)

            response_json = response.json();
            if response_json['status'] == 1:
                connection.execute(
                    "UPDATE orders SET is_status_payed='true' WHERE id={}".format(rows[0]['id']))
                return "Заказ оплачен"
            else:
                return "Заказ не оплачен"
        else:
            return "Заказ уже оплачен"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port='80', debug=True)
