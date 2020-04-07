#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@version: 1.0.0
@author: zheng guang
@contact: zg.zhu@daocloud.io
@time: 2019/7/4 4:56 PM
"""

from flask import Flask, request, Response
import requests
import arrow
import logging
import json
import os

LOG = logging.getLogger(__name__)
app = Flask(__name__)

WECAHT_API = os.getenv('WECAHT_API', "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={}")
KEY = os.getenv('ROBOT_KEY', '')
ALEAT_MANAGER_URL = os.getenv('ALEAT_MANAGER_URL', '')


def send_wechat_msg(key, message):
    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": message
        }
    }
    headers = {
        "Content-Type": "application/json;charset=UTF-8"
    }
    if not key and KEY:
        key = KEY

    LOG.debug("send wechat msg: %s", data)
    respose = requests.post(WECAHT_API.format(key), headers=headers, data=json.dumps(data))
    LOG.info("send message result: %s:%s", respose.status_code, respose.text)
    if respose.status_code == 200:
        return True
    else:
        return False


def try_get_value(data_dict, keys, default_value=""):
    for key in keys:
        if data_dict.get(key):
            return data_dict.get(key)
    return default_value


@app.route('/prometheus_webhook', methods=['POST'])
def prometheus_webhook():
    bearer_token = request.headers.get('Authorization', 'bearer_token ').split(" ")
    if len(bearer_token) != 2:
        get_result(error="bearer_token can not null")
    receiver = bearer_token[1]

    data = request.get_json()
    LOG.debug("receive msg: %s", data)
    msg = ""
    alert_status = data.get('status') 
    alert_len = len(data.get('alerts'))
    alert_name = data.get('commonLabels').get("alertname")
    alert_0 = data.get('alerts')[0]
    env = alert_0.get('labels').get('env')
    desc = alert_0.get('annotations').get('message')
    if desc == None :
        desc = alert_0.get('annotations').get('description')

    severity = alert_0.get('labels').get('severity')
    if alert_status == "resolved":
        msg = "[**[{}] {}**]()\n\n".format(alert_status,alert_name)
    else:
        msg = "[**[{}:{}] {}**]()\n\n".format(alert_status,alert_len,alert_name)

    msg = msg + "*Environment:* " + env +" \n\n*Description:* "+ desc + " \n\n*Severity:* `" + severity + "` \n\n*Alert details*: \n\n"

    container_msg = ""
    detail_msg = ""
    for alert in data.get('alerts'):
        container = alert.get('labels').get('container')
        detail = alert.get('annotations').get('detail')

        if container != None:
            if container_msg != "":
                container_msg = container_msg + "```*container:* "+container+ "```\n\n"
            else:
                container_msg = "```*container:* "+container+"```\n\n"

        if detail != None:
            if detail_msg != "":
                detail_msg = detail_msg+"```"+detail+"```\n\n"
            else:
                detail_msg = "```"+ detail +"```\n\n"

    result = send_wechat_msg(receiver, msg+container_msg+detail_msg)

    return get_result(error=result)


def get_result(text='', receiver='', error=""):
    if isinstance(error, bool):
        if error:
            error = ""
        else:
            error = "send alert failed"
    result = {
        "receiver": receiver,
        "text": text,
    }
    if error:
        return Response(json.dumps({"error": error}), mimetype='application/json', status=400)
    return Response(json.dumps(result), mimetype='application/json')


if __name__ == '__main__':
    logging.basicConfig(level=logging.getLevelName(os.getenv('LOG_LEVEL', 'DEBUG')),
                        format='%(asctime)s %(name)s %(levelname)-8s %(message)s')
    LOG.info("app started")
    app.run('0.0.0.0', '8080')
