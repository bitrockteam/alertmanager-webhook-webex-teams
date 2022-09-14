from flask import Flask, request
from os import environ
from io import BytesIO
from werkzeug.exceptions import HTTPException
from pythonjsonlogger import jsonlogger
import pycurl
import json
import re


webex_token = environ.get('WEBEX_TOKEN')
webex_room = environ.get("WEBEX_ROOM_" + environ.get('DEFAULT_WEBEX_ROOM').upper())
loglevel = environ.get('LOGLEVEL','INFO')
formatter = jsonlogger.JsonFormatter(
    '%(asctime) %(levelname) %(module) %(funcName) %(lineno) %(message)')
strip = environ.get("STRIP_LABELS").split(",")
if strip == None:
    strip = [
        "cloud", "endpoint", "prometheus", "service", "webex_receiver"
    ]


app = Flask(__name__)
@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

@app.route('/alertmanager', methods=['POST'])
def alertmanager():
    try:
        if request.is_json:
            post_data = json.loads(request.data)
            alert_data(post_data)
    except Exception as e:
        app.logger.error("Storing alerts failed in main: %s", e)
        app.logger.exception(e)
        return {"ERROR"}, 500

    return "NOK", 200

def alert_data(data):
    if "alerts" in data:
        app.logger.debug('%s alerts received', len(data['alerts']))
        for i in data["alerts"]:
            app.logger.debug('alert content: {0}'.format(i))
            try:
                for ln in strip:
                    if ln.strip() in i["labels"]:
                        del i["labels"][ln.strip()]
                alertname = "### alertname: "
                severity = "severity: "
                cluster = "## cluster: "
                start = "start: "
                end = "end: "
                labels = ""
                annotations = ""
                local_webex_room = None

                if i["endAt"] == '0001-01-01T00:00:00Z':
                    del i["endsAt"]
                if "webex_room" in i["labels"]:
                    local_webex_room = environ.get("WEBEX_ROOM_" + i["labels"]["webex_room"].upper())
                    del i["labels"]["webex_room"]
                if local_webex_room == None:
                    local_webex_room = webex_room
                if "alertname" in i["labels"]:
                    alertname = alertname + i["labels"]["alertname"]
                    del i["labels"]["alertname"]
                if "severity" in i["labels"]:
                    severity = severity + i["labels"]["severity"]
                    del i["labels"]["severity"]
                if "cluster" in i["labels"]:
                    cluster = cluster + i["labels"]["cluster"]
                    del i["labels"]["cluster"]
                if i["startsAt"]:
                    start = start + i["startsAt"]
                if i["endsAt"]:
                    end = end + i["endsAt"]
                for k in i["labels"].keys():
                    if re.search("^\s*https*://", i["labels"][k]):
                        labels = '{0}\n - {1}: [{1}]({2})'.format(labels, k, i['labels'][k])
                    else:
                        labels = '{0}\n - {1}: {2}'.format(labels, k, i['labels'][k])
                for k in i["annotations"].keys():
                    annotations = '{0}\n - {1}: {2}'.format(annotations, k, i['annotations'][k])
                alert = cluster + "\n" + alertname + "\n" + severity + "\n" + labels + "\n" + annotations + "\n" + start + "\n" + end
                app.logger.debug(alert)
                app.logger.debug("Sending to roomId: '"+local_webex_room+"'")
                webex = [("roomId", local_webex_room), ("markdown", str(alert))]
                headers = ['Authorization: Bearer ' + webex_token ]
                buffer = BytesIO()
                crl = pycurl.Curl()
                crl.setopt(pycurl.URL, 'https://webexapis.com/v1/messages')
                crl.setopt(pycurl.HTTPHEADER, headers)
                crl.setopt(pycurl.HTTPPOST, webex)
                crl.setopt(crl.WRITEDATA, buffer)
                crl.perform()
                app.logger.debug('Status: {0}'.format(crl.getinfo(crl.RESPONSE_CODE)))
                app.logger.debug('Response: {0}'.format(buffer.getvalue()))
                crl.close()
            except Exception as e:
                app.logger.error("Storing alerts failed in sub: %s", e)
                app.logger.exception(e)
                return {"ERROR"}, 500

    return "OK", 200

@app.errorhandler(HTTPException)
def handle_exception(e):
    response = e.get_response()
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response

if __name__ == '__main__':
  app.logger.setLevel(loglevel)
  app.logger.handlers[0].setFormatter(formatter)
  app.run(
    host = "0.0.0.0",
    port = 9091,
    debug = 0
  )
