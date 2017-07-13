from flask import Flask
from flask_restful import Resource, Api
from threading import Thread

class WebAPI:

    def __init__(self, sprApi):
        self.api = sprApi
        self.server_thread = Thread(target=self.start_server, args=(self,))
        self.server_thread.start()

    def start_server(self):
        app = Flask(__name__)
        api = Api(app)
        api.add_resource(,'/')
        app.run(debug=True)

def SwitchResource(Resource):
    
    def get(self):

