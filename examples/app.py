from flask import Flask
import socket
import os

app = Flask(__name__)

@app.route('/')
def hello():
    hostname = socket.gethostname()
    node_name = os.getenv('NODE_NAME', 'unknown')
    capacity_type = os.getenv('CAPACITY_TYPE', 'unknown')
    
    return f"""
    <h1>Spot/On-Demand Demo</h1>
    <p>Pod: {hostname}</p>
    <p>Node: {node_name}</p>
    <p>Capacity Type: {capacity_type}</p>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
